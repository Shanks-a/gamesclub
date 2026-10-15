import hashlib, json, uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import AccessToken, GamePartition, Product, ProductCategory, Favorite, Order, OrderStatusHistory, PaymentAttempt, IdempotencyRecord, UserProfile, WechatIdentity, Partner, PartnerApplication, Review, AfterSaleCase, Evidence, get_config_int, Conversation, Message
from .serializers import GameSerializer, CategorySerializer, ProductSerializer, FavoriteSerializer, OrderSerializer, ProductWriteSerializer, PartnerSerializer, PartnerApplicationSerializer, ReviewSerializer, AfterSaleCaseSerializer, RefundSerializer, ConversationSerializer, MessageSerializer
from .wechat import code2session, WechatLoginError

def err(message, code, http=400):
    return Response({'error': {'code': code, 'message': message}}, status=http)
def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def get_idem(user, request, action):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    action = action + ':' + request.path
    key = request.headers.get('Idempotency-Key')
    if not key or len(key) > 100: return None, err('需要长度不超过100的 Idempotency-Key', 'IDEMPOTENCY_KEY_REQUIRED')
    h = digest(request.data); old = IdempotencyRecord.objects.filter(user=user, key=key).first()
    if old:
        if old.request_hash != h or old.action != action: return None, err('幂等键已用于其他请求', 'IDEMPOTENCY_CONFLICT', 409)
        return old, Response(old.response_json, status=old.status_code)
    return (key, h, action), None
def save_idem(user, state, action, resource, response):
    key, h, action = state
    IdempotencyRecord.objects.create(user=user, key=key, request_hash=h, action=action, resource_id=str(resource), response_json=response.data, status_code=response.status_code)

@api_view(['POST'])
@permission_classes([AllowAny])
def dev_login(request):
    if not settings.DEBUG or not settings.ALLOW_DEV_LOGIN: return err('开发登录未开放', 'DEV_LOGIN_DISABLED', 403)
    User = get_user_model()
    # 本地联调支持指定已存在的测试账号（仅 DEBUG 环境），默认仍为 dev-player
    username = request.data.get('username') if isinstance(request.data, dict) else None
    if username:
        if not isinstance(username, str) or len(username) > 80: return err('用户名无效', 'INVALID_USERNAME', 400)
        try: user = User.objects.get(username=username, is_staff=False, is_superuser=False)
        except User.DoesNotExist: return err('测试账号不存在', 'NOT_FOUND', 404)
    else:
        user, _ = User.objects.get_or_create(username='dev-player')
    UserProfile.objects.get_or_create(user=user)
    raw, _ = AccessToken.issue(user)
    return Response({'access_token': raw, 'user': {'id':user.id, 'nickname':user.profile.nickname, 'avatar_url':user.profile.avatar_url}})

@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_login(request):
    code = request.data.get('code') if isinstance(request.data, dict) else None
    if not code or not isinstance(code, str) or len(code) > 256:
        return err('缺少登录凭证 code', 'WECHAT_CODE_REQUIRED', 400)
    try:
        sess = code2session(code)
    except WechatLoginError as e:
        return err(e.message, 'WECHAT_LOGIN_FAILED', 400)
    openid = sess['openid']; appid = settings.WECHAT_APPID
    User = get_user_model()
    with transaction.atomic():
        identity = WechatIdentity.objects.filter(appid=appid, openid=openid).select_related('user').first()
        if identity:
            user = identity.user
        else:
            # 首次登录创建账号。用户名用 openid 哈希，避免暴露原始 openid。
            username = 'wx_' + hashlib.sha256(openid.encode()).hexdigest()[:20]
            user = User.objects.create_user(username=username)
            UserProfile.objects.create(user=user, nickname='微信玩家')
            WechatIdentity.objects.create(user=user, appid=appid, openid=openid, unionid=sess.get('unionid', ''))
        raw, _ = AccessToken.issue(user)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return Response({'access_token': raw, 'user': {'id': user.id, 'nickname': profile.nickname, 'avatar_url': profile.avatar_url}})

@api_view(['GET','PATCH'])
def me(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    def full():
        # GET 与 PATCH 统一返回完整结构，避免前端用 PATCH 响应覆盖 me 后丢失陪玩字段。
        partner = Partner.objects.filter(user=request.user).first()
        return {'id':request.user.id, 'nickname':profile.nickname, 'avatar_url':profile.avatar_url,
                'is_partner': partner is not None, 'partner_active': partner.is_active if partner else False}
    if request.method == 'GET':
        return Response(full())
    # PATCH 更新昵称/头像。只接受白名单字段，昵称做基本长度与去空校验。
    data = request.data if isinstance(request.data, dict) else {}
    allowed = {'nickname', 'avatar_url'}
    unknown = set(data) - allowed
    if unknown: return err('不接受字段：' + ','.join(sorted(unknown)), 'INVALID_FIELDS')
    if 'nickname' in data:
        nickname = data['nickname']
        if not isinstance(nickname, str) or not nickname.strip(): return err('昵称不能为空', 'INVALID_NICKNAME')
        nickname = nickname.strip()
        if len(nickname) > 80: return err('昵称长度不能超过80个字符', 'INVALID_NICKNAME')
        profile.nickname = nickname
    if 'avatar_url' in data:
        avatar = data['avatar_url']
        if avatar is not None and (not isinstance(avatar, str) or not avatar.startswith(('/media/', 'http://', 'https://'))): return err('头像地址无效', 'INVALID_AVATAR')
        profile.avatar_url = avatar or ''
    profile.save(update_fields=[f for f in ('nickname','avatar_url') if f in data])
    return Response(full())

@api_view(['POST'])
def upload_avatar(request):
    from PIL import Image, UnidentifiedImageError
    import io as _io
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    import uuid as _uuid
    file = request.FILES.get('file')
    if not file or file.size > 5*1024*1024: return err('请选择不超过5MB的图片', 'INVALID_IMAGE')
    try:
        picture = Image.open(file)
        if picture.format not in ('JPEG','PNG','WEBP') or picture.width*picture.height > 20_000_000: raise ValueError()
        picture.load(); picture = picture.convert('RGB'); output = _io.BytesIO(); picture.save(output, format='JPEG', quality=90)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return err('仅支持有效的 JPEG、PNG、WebP 图片', 'INVALID_IMAGE')
    path = default_storage.save('avatars/' + _uuid.uuid4().hex + '.jpg', ContentFile(output.getvalue()))
    url = default_storage.url(path)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.avatar_url = url; profile.save(update_fields=['avatar_url'])
    return Response({'url': url, 'avatar_url': url}, status=201)

@api_view(['POST'])
def logout(request):
    if isinstance(request.auth, AccessToken): request.auth.delete()
    return Response({'ok':True})

@api_view(['GET'])
@permission_classes([AllowAny])
def games(request):
    return Response(GameSerializer(GamePartition.objects.filter(is_enabled=True).order_by('sort_order','id'), many=True).data)

@api_view(['GET'])
@permission_classes([AllowAny])
def products(request):
    qs = Product.objects.filter(is_published=True, game__is_enabled=True, category__is_enabled=True).select_related('game','category')
    game = request.query_params.get('game'); query = request.query_params.get('q')
    if game and game not in ('全部','推荐'): qs = qs.filter(game__name=game)
    category_id = request.query_params.get('category_id')
    if category_id: qs = qs.filter(category_id=category_id)
    if query: qs = qs.filter(Q(title__icontains=query) | Q(game__name__icontains=query))
    sort = request.query_params.get('sort'); qs = qs.order_by('price_cents' if sort == 'asc' else '-price_cents' if sort == 'desc' else 'id')
    return Response(ProductSerializer(qs, many=True).data)

@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, pk):
    try: p = Product.objects.select_related('game').get(pk=pk)
    except Product.DoesNotExist: return err('商品不存在', 'NOT_FOUND', 404)
    return Response(ProductSerializer(p).data)

@api_view(['GET'])
@permission_classes([AllowAny])
def game_categories(request, pk):
    qs = ProductCategory.objects.filter(game_id=pk, game__is_enabled=True, is_enabled=True)
    return Response(CategorySerializer(qs, many=True).data)

@api_view(['GET'])
@permission_classes([AllowAny])
def game_partners(request, pk):
    """某游戏分区内接单中的陪玩列表（公开，供下单时指定陪陪）。"""
    active = Partner.objects.filter(game_id=pk, is_active=True, game__is_enabled=True).select_related('user__profile', 'game')
    from django.db.models import Count, Q
    active = active.annotate(completed_orders=Count('orders', filter=Q(orders__status=Order.Status.COMPLETED)))
    data = [{'id': p.id, 'nickname': p.user.profile.nickname if hasattr(p.user, 'profile') else p.user.username,
             'avatar_url': p.user.profile.avatar_url if hasattr(p.user, 'profile') else '',
             'intro': p.intro, 'completed_orders': p.completed_orders, 'game': GameSerializer(p.game).data} for p in active]
    return Response(data)

@api_view(['GET','POST'])
def favorites(request):
    if request.method == 'GET': return Response(FavoriteSerializer(Favorite.objects.filter(user=request.user).select_related('product__game'), many=True).data)
    try: p = Product.objects.get(pk=request.data.get('product_id'))
    except Product.DoesNotExist: return err('商品不存在', 'NOT_FOUND', 404)
    Favorite.objects.get_or_create(user=request.user, product=p); return Response({'ok':True})

@api_view(['DELETE'])
def favorite_detail(request, product_id):
    Favorite.objects.filter(user=request.user, product_id=product_id).delete(); return Response(status=204)

@api_view(['GET','POST'])
def orders(request):
    if request.method == 'GET':
        qs = Order.objects.filter(user=request.user).select_related('product', 'partner', 'partner__user__profile').prefetch_related('review').order_by('-created_at')
        return Response(OrderSerializer(qs, many=True).data)
    quantity = request.data.get('quantity'); expected = request.data.get('expected_product_version')
    if type(quantity) is not int: return err('数量必须为整数', 'INVALID_QUANTITY')
    if set(request.data) - {'product_id','quantity','expected_product_version','appointment_date','appointment_slot','platform','role_name','role_id','message','remark','preferred_partner_id'}: return err('不接受自定义金额或其他字段', 'INVALID_FIELDS')
    if type(request.data.get('product_id')) is not int: return err('商品编号必须为整数', 'INVALID_PRODUCT')
    # 游戏平台与角色信息（提交订单页填写；platform 可选，须为 mobile/pc）
    platform = request.data.get('platform')
    if platform is not None and platform not in Order.Platform.values: return err('游戏平台无效', 'INVALID_PLATFORM')
    role_name = (request.data.get('role_name') or '').strip() if isinstance(request.data, dict) else ''
    role_id = (request.data.get('role_id') or '').strip() if isinstance(request.data, dict) else ''
    message = (request.data.get('message') or '').strip() if isinstance(request.data, dict) else ''
    remark = (request.data.get('remark') or '').strip() if isinstance(request.data, dict) else ''
    if len(role_name) > 80 or len(role_id) > 80: return err('角色名称/ID 不能超过80字', 'INVALID_ROLE')
    if len(message) > 255 or len(remark) > 255: return err('留言/备注不能超过255字', 'INVALID_MESSAGE')
    preferred_partner_id = request.data.get('preferred_partner_id')
    if preferred_partner_id is not None and type(preferred_partner_id) is not int: return err('指定陪玩编号无效', 'INVALID_PARTNER')
    # 预约时段校验（可选，但日期与时段需成对出现）
    appt_date = request.data.get('appointment_date'); appt_slot = request.data.get('appointment_slot')
    if bool(appt_date) != bool(appt_slot): return err('预约日期与时段需同时提供', 'INVALID_APPOINTMENT')
    if appt_slot and appt_slot not in Order.Slot.values: return err('预约时段无效', 'INVALID_APPOINTMENT')
    if appt_date:
        try:
            from datetime import date as _date
            appt_date = _date.fromisoformat(str(appt_date))
        except ValueError:
            return err('预约日期格式为 YYYY-MM-DD', 'INVALID_APPOINTMENT')
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'CREATE_ORDER')
        if replay is not None: return replay
        try: p = Product.objects.select_for_update().get(pk=request.data.get('product_id'))
        except Product.DoesNotExist: return err('商品不存在', 'NOT_FOUND', 404)
        game = GamePartition.objects.select_for_update().get(pk=p.game_id)
        category = ProductCategory.objects.select_for_update().filter(pk=p.category_id).first()
        if not p.is_published or not game.is_enabled or not category or not category.is_enabled or category.game_id != game.id: return err('商品已下架', 'PRODUCT_UNAVAILABLE', 409)
        if expected != p.version: return err('商品已更新，请重新确认价格', 'PRODUCT_VERSION_CONFLICT', 409)
        if quantity < p.min_quantity or quantity > p.max_quantity: return err('购买数量超出范围', 'INVALID_QUANTITY')
        # 校验客户指定的陪玩：须属于商品游戏分区且接单中
        preferred = None
        if preferred_partner_id is not None:
            preferred = Partner.objects.filter(pk=preferred_partner_id, is_active=True, game_id=p.game_id).first()
            if not preferred: return err('指定陪玩不存在、已暂停接单或与商品游戏不符', 'INVALID_PREFERRED_PARTNER', 409)
        order = Order.objects.create(order_no='GC'+uuid.uuid4().hex[:30], user=request.user, product=p, game_name_snapshot=game.name, product_title_snapshot=p.title, cover_url_snapshot=p.cover_url, unit_price_cents=p.price_cents, total_amount_cents=p.price_cents*quantity, quantity=quantity, appointment_date=appt_date, appointment_slot=appt_slot, platform=platform, role_name=role_name, role_id=role_id, message=message, remark=remark, preferred_partner=preferred, commission_bp=get_config_int('commission_bp', 2000))
        OrderStatusHistory.objects.create(order=order, to_status=order.status, action='CREATE', actor=request.user)
        response = Response(OrderSerializer(order).data, status=201); save_idem(request.user, state, 'CREATE_ORDER', order.id, response); return response

@api_view(['GET'])
def order_detail(request, pk):
    try: order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
    return Response(OrderSerializer(order).data)

@api_view(['POST'])
def cancel_order(request, pk):
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'CANCEL')
        if replay is not None: return replay
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        if order.status != Order.Status.PENDING_PAYMENT: return err('当前状态不能取消', 'ORDER_STATE_CONFLICT', 409)
        old = order.status; order.status = Order.Status.CANCELLED; order.version += 1; order.save(update_fields=['status','version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action='CANCEL', actor=request.user)
        response = Response(OrderSerializer(order).data)
        save_idem(request.user, state, 'CANCEL', order.id, response)
        return response

@api_view(['POST'])
def mock_pay(request, pk):
    if not settings.DEBUG or not settings.ALLOW_MOCK_PAYMENT: return err('模拟付款未开放', 'MOCK_DISABLED', 403)
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'MOCK_PAY')
        if replay is not None: return replay
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        if order.status != Order.Status.PENDING_PAYMENT or order.payment_status != Order.PaymentStatus.UNPAID: return err('当前状态不能付款', 'ORDER_STATE_CONFLICT', 409)
        PaymentAttempt.objects.create(order=order, idempotency_key=digest([request.user.pk,state[0]]), amount_cents=order.total_amount_cents, status=PaymentAttempt.Status.SUCCEEDED, completed_at=timezone.now())
        old = order.status
        order.payment_status=Order.PaymentStatus.PAID
        # 接单流程改为客服介入：无论是否指定陪玩，付款后均进入「待派单」，
        # 由客服确认（陪玩是否有单/是否可接）后再人工派单。
        # 指定的陪玩仅作为「意向陪玩」供客服派单时参考，不再自动派单。
        order.status = Order.Status.PENDING_ARRANGEMENT
        action = 'MOCK_PAY'
        order.version += 1; order.save(update_fields=['payment_status','status','version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action=action, actor=request.user)
        response=Response(OrderSerializer(order).data); save_idem(request.user,state,'MOCK_PAY',order.id,response); return response

def admin_ok(request): return request.user.is_staff or request.user.is_superuser
@api_view(['POST'])
def management_products(request):
    if not admin_ok(request): return err('无管理权限','FORBIDDEN',403)
    serializer=ProductWriteSerializer(data=request.data); serializer.is_valid(raise_exception=True); return Response(ProductSerializer(serializer.save()).data,status=201)

@api_view(['GET','POST'])
def management_categories(request):
    if not admin_ok(request): return err('无管理权限','FORBIDDEN',403)
    if request.method == 'GET':
        return Response(CategorySerializer(ProductCategory.objects.select_related('game').all(), many=True).data)
    serializer = CategorySerializer(data=request.data); serializer.is_valid(raise_exception=True)
    return Response(CategorySerializer(serializer.save()).data, status=201)

@api_view(['PATCH'])
def management_category_detail(request, pk):
    if not admin_ok(request): return err('无管理权限','FORBIDDEN',403)
    try: category = ProductCategory.objects.get(pk=pk)
    except ProductCategory.DoesNotExist: return err('商品类型不存在','NOT_FOUND',404)
    serializer = CategorySerializer(category, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
    return Response(CategorySerializer(serializer.save(version=category.version+1)).data)
@api_view(['PATCH'])
def management_product_detail(request,pk):
    if not admin_ok(request): return err('无管理权限','FORBIDDEN',403)
    try: product=Product.objects.get(pk=pk)
    except Product.DoesNotExist: return err('商品不存在','NOT_FOUND',404)
    if request.data.get('version') != product.version: return err('版本冲突','VERSION_CONFLICT',409)
    serializer=ProductWriteSerializer(product,data=request.data,partial=True); serializer.is_valid(raise_exception=True); product=serializer.save(version=product.version+1); return Response(ProductSerializer(product).data)
@api_view(['POST'])
def publish_product(request,pk): return _publish(request,pk,True)
@api_view(['POST'])
def unpublish_product(request,pk): return _publish(request,pk,False)
def _publish(request,pk,value):
    if not admin_ok(request): return err('无管理权限','FORBIDDEN',403)
    try: product=Product.objects.get(pk=pk)
    except Product.DoesNotExist: return err('商品不存在','NOT_FOUND',404)
    product.is_published=value; product.version+=1; product.save(update_fields=['is_published','version','updated_at']); return Response(ProductSerializer(product).data)

# ============ P4 订单与派单 ============

@api_view(['GET','POST'])
def partner_application(request):
    if request.method == 'GET':
        return Response(PartnerApplicationSerializer(PartnerApplication.objects.filter(user=request.user).select_related('game','user__profile').order_by('-created_at'), many=True).data)
    # POST 提交入驻申请
    game_id = request.data.get('game') if isinstance(request.data, dict) else None
    reason = (request.data.get('reason') or '') if isinstance(request.data, dict) else ''
    if type(game_id) is not int: return err('请选择游戏分区', 'INVALID_GAME')
    if not isinstance(reason, str) or len(reason) > 1000: return err('申请说明不能超过1000字', 'INVALID_REASON')
    try: game = GamePartition.objects.get(pk=game_id, is_enabled=True)
    except GamePartition.DoesNotExist: return err('游戏分区不存在或已停用', 'NOT_FOUND', 404)
    app, created = PartnerApplication.objects.get_or_create(user=request.user, game=game, defaults={'reason': reason})
    if not created:
        if app.status == PartnerApplication.Status.PENDING: return err('你已提交过该分区的申请，请等待审核', 'APPLICATION_EXISTS', 409)
        # 已被处理过的申请允许重新提交
        app.reason = reason; app.status = PartnerApplication.Status.PENDING; app.reviewed_by = None; app.reviewed_at = None; app.save(update_fields=['reason','status','reviewed_by','reviewed_at'])
    return Response(PartnerApplicationSerializer(app).data, status=201 if created else 200)

@api_view(['POST'])
def confirm_order(request, pk):
    """客户验收：PENDING_CONFIRMATION -> COMPLETED"""
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'CONFIRM')
        if replay is not None: return replay
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        if order.status != Order.Status.PENDING_CONFIRMATION: return err('当前状态不能验收', 'ORDER_STATE_CONFLICT', 409)
        old = order.status; order.status = Order.Status.COMPLETED; order.completed_at = timezone.now()
        order.aftersale_deadline = order.completed_at + timedelta(hours=get_config_int('aftersale_window_hours', 48))
        order.version += 1
        order.save(update_fields=['status','completed_at','aftersale_deadline','version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action='CONFIRM', actor=request.user)
        response = Response(OrderSerializer(order).data); save_idem(request.user, state, 'CONFIRM', order.id, response); return response

@api_view(['GET','POST'])
def review(request, pk):
    """订单评价：仅已完成订单可评，一单一次。"""
    if request.method == 'GET':
        try: order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        try: r = order.review
        except Review.DoesNotExist: return err('尚未评价', 'NOT_FOUND', 404)
        return Response(ReviewSerializer(r).data)
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'REVIEW')
        if replay is not None: return replay
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        if order.status != Order.Status.COMPLETED: return err('订单完成后才能评价', 'ORDER_STATE_CONFLICT', 409)
        if Review.objects.filter(order=order).exists(): return err('该订单已评价', 'REVIEW_EXISTS', 409)
        rating = request.data.get('rating') if isinstance(request.data, dict) else None
        content = (request.data.get('content') or '') if isinstance(request.data, dict) else ''
        if type(rating) is not int or rating < 1 or rating > 5: return err('评分须为 1-5 的整数', 'INVALID_RATING')
        if not isinstance(content, str) or len(content) > 2000: return err('评价内容不能超过2000字', 'INVALID_CONTENT')
        r = Review.objects.create(order=order, user=request.user, rating=rating, content=content)
        order.version += 1; order.save(update_fields=['version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=order.status, to_status=order.status, action='REVIEW', actor=request.user)
        response = Response(ReviewSerializer(r).data, status=201); save_idem(request.user, state, 'REVIEW', order.id, response); return response

def _partner_of(request):
    """取当前用户的陪玩档案；无档案或接单关闭时返回 None。"""
    try: p = Partner.objects.get(user=request.user)
    except Partner.DoesNotExist: return None
    return p

@api_view(['GET'])
def partner_orders(request):
    partner = _partner_of(request)
    if not partner: return err('你不是陪玩或尚未建立档案', 'NOT_PARTNER', 403)
    qs = Order.objects.filter(partner=partner).select_related('product', 'user__profile').prefetch_related('review').order_by('-created_at')
    return Response(OrderSerializer(qs, many=True).data)

def _partner_order_action(request, pk, action, from_status, to_status):
    """陪玩对订单的状态流转通用处理。"""
    partner = _partner_of(request)
    if not partner: return err('你不是陪玩或尚未建立档案', 'NOT_PARTNER', 403)
    if not partner.is_active: return err('你的接单权限已被关闭', 'PARTNER_DISABLED', 403)
    with transaction.atomic():
        state, replay = get_idem(request.user, request, action)
        if replay is not None: return replay
        try: order = Order.objects.select_for_update().get(pk=pk, partner=partner)
        except Order.DoesNotExist: return err('订单不存在或未派给你', 'NOT_FOUND', 404)
        if order.status != from_status: return err('当前状态不能执行该操作', 'ORDER_STATE_CONFLICT', 409)
        old = order.status; order.status = to_status; order.version += 1
        update_fields = ['status','version','updated_at']
        if action == 'REJECT':
            order.partner = None; update_fields.append('partner')
        order.save(update_fields=update_fields)
        # 陪玩接单成功后，为客户与陪玩建立订单会话（幂等，一单一会话）
        if action == 'ACCEPT':
            Conversation.objects.get_or_create(order=order, defaults={'user': order.user, 'partner': partner})
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action=action, actor=request.user)
        response = Response(OrderSerializer(order).data); save_idem(request.user, state, action, order.id, response); return response

@api_view(['POST'])
def partner_accept(request, pk): return _partner_order_action(request, pk, 'ACCEPT', Order.Status.PENDING_ACCEPTANCE, Order.Status.ACCEPTED)
@api_view(['POST'])
def partner_reject(request, pk): return _partner_order_action(request, pk, 'REJECT', Order.Status.PENDING_ACCEPTANCE, Order.Status.PENDING_ARRANGEMENT)
@api_view(['POST'])
def partner_start(request, pk): return _partner_order_action(request, pk, 'START', Order.Status.ACCEPTED, Order.Status.IN_SERVICE)
@api_view(['POST'])
def partner_complete(request, pk): return _partner_order_action(request, pk, 'COMPLETE', Order.Status.IN_SERVICE, Order.Status.PENDING_CONFIRMATION)

# ============ P5 售后与退款 ============

def _aftersale_window_open(order):
    """判断订单是否在售后窗口内。服务中/待验收始终可申请；完成后须在截止时间内。"""
    if order.status in (Order.Status.IN_SERVICE, Order.Status.PENDING_CONFIRMATION):
        return True
    if order.status == Order.Status.COMPLETED:
        return order.aftersale_deadline is not None and timezone.now() <= order.aftersale_deadline
    return False

@api_view(['GET','POST'])
def aftersale(request, pk):
    """申请/查询售后案件。"""
    if request.method == 'GET':
        try: order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        cases = AfterSaleCase.objects.filter(order=order).prefetch_related('evidences','refunds').order_by('-created_at')
        return Response(AfterSaleCaseSerializer(cases, many=True).data)
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'AFTERSALE')
        if replay is not None: return replay
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        if order.payment_status != Order.PaymentStatus.PAID: return err('订单未付款，无需售后', 'ORDER_STATE_CONFLICT', 409)
        if not _aftersale_window_open(order): return err('已过售后申请时限', 'AFTERSALE_WINDOW_CLOSED', 409)
        if AfterSaleCase.objects.filter(order=order, status=AfterSaleCase.Status.OPEN).exists(): return err('该订单已有处理中的售后申请', 'AFTERSALE_EXISTS', 409)
        amount = request.data.get('amount_cents') if isinstance(request.data, dict) else None
        reason = (request.data.get('reason') or '') if isinstance(request.data, dict) else ''
        if type(amount) is not int or amount <= 0: return err('退款金额必须为正整数（分）', 'INVALID_AMOUNT')
        if not isinstance(reason, str) or len(reason) > 2000: return err('申请说明不能超过2000字', 'INVALID_REASON')
        refundable = order.total_amount_cents - order.refunded_amount_cents - order.reserved_refund_cents
        if amount > refundable: return err('退款金额超过可退金额', 'REFUND_AMOUNT_EXCEEDED', 409)
        case = AfterSaleCase.objects.create(order=order, user=request.user, case_no='AS'+uuid.uuid4().hex[:30], amount_cents=amount, reason=reason)
        # 挂接上传的凭证
        evidence_ids = request.data.get('evidence_ids') or []
        if evidence_ids:
            Evidence.objects.filter(id__in=evidence_ids, uploader=request.user, case=None).update(case=case)
        order.version += 1; order.save(update_fields=['version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=order.status, to_status=order.status, action='AFTERSALE_APPLY', actor=request.user)
        response = Response(AfterSaleCaseSerializer(case).data, status=201); save_idem(request.user, state, 'AFTERSALE', order.id, response); return response

@api_view(['POST'])
def upload_evidence(request):
    """上传售后图片凭证（私有存储，先不挂案件，申请时挂接）。"""
    from PIL import Image, UnidentifiedImageError
    import io as _io
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    import uuid as _uuid
    file = request.FILES.get('file')
    if not file or file.size > 5*1024*1024: return err('请选择不超过5MB的图片', 'INVALID_IMAGE')
    try:
        picture = Image.open(file)
        if picture.format not in ('JPEG','PNG','WEBP') or picture.width*picture.height > 20_000_000: raise ValueError()
        picture.load(); picture = picture.convert('RGB'); output = _io.BytesIO(); picture.save(output, format='JPEG', quality=90)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return err('仅支持有效的 JPEG、PNG、WebP 图片', 'INVALID_IMAGE')
    path = default_storage.save('evidence/' + _uuid.uuid4().hex + '.jpg', ContentFile(output.getvalue()))
    ev = Evidence.objects.create(uploader=request.user, file_path=path, mime_type='image/jpeg', size_bytes=output.tell())
    return Response({'id': ev.id, 'url': default_storage.url(path)}, status=201)

# ============ P0 消息与会话 ============

def _conversations_qs(user):
    """当前用户参与的会话，统一预取，避免 N+1。"""
    return Conversation.objects.filter(Q(user=user) | Q(partner__user=user)).select_related(
        'order', 'user__profile', 'partner__user__profile'
    ).prefetch_related('messages').order_by('-id')

def _accessible_conversation(user, pk):
    """取当前用户可访问的会话；非参与者返回 None。"""
    try:
        return _conversations_qs(user).get(pk=pk)
    except Conversation.DoesNotExist:
        return None

@api_view(['GET'])
def conversations(request):
    """会话列表：客户与陪玩通用，按最后消息时间倒序，带未读数。"""
    partner = _partner_of(request)
    qs = _conversations_qs(request.user)
    data = []
    for conv in qs:
        messages = list(conv.messages.all())
        # 当前用户在会话中的身份：是陪玩则我方 sender=PARTNER，否则为 USER
        is_partner = partner is not None and conv.partner_id == partner.id
        my_sender = Message.Sender.PARTNER if is_partner else Message.Sender.USER
        unread = sum(1 for m in messages if m.sender != my_sender and m.read_at is None)
        item = ConversationSerializer(conv).data
        item['unread_count'] = unread
        data.append(item)
    return Response(data)

@api_view(['GET'])
def conversation_messages(request, pk):
    conv = _accessible_conversation(request.user, pk)
    if conv is None: return err('会话不存在', 'NOT_FOUND', 404)
    # 拉取时把对方发来的消息标记为已读（当前用户视角）
    partner = _partner_of(request)
    my_sender = Message.Sender.PARTNER if partner and conv.partner_id == partner.id else Message.Sender.USER
    Message.objects.filter(conversation=conv, read_at__isnull=True).exclude(sender=my_sender).update(read_at=timezone.now())
    return Response(MessageSerializer(conv.messages.all(), many=True).data)

@api_view(['POST'])
def conversation_send(request, pk):
    conv = _accessible_conversation(request.user, pk)
    if conv is None: return err('会话不存在', 'NOT_FOUND', 404)
    content = request.data.get('content') if isinstance(request.data, dict) else None
    if not isinstance(content, str) or not content.strip(): return err('消息内容不能为空', 'INVALID_CONTENT')
    if len(content) > 2000: return err('消息内容不能超过2000字', 'INVALID_CONTENT')
    partner = _partner_of(request)
    sender = Message.Sender.PARTNER if partner and conv.partner_id == partner.id else Message.Sender.USER
    with transaction.atomic():
        state, replay = get_idem(request.user, request, 'SEND_MESSAGE')
        if replay is not None: return replay
        msg = Message.objects.create(conversation=conv, sender=sender, content=content.strip())
        response = Response(MessageSerializer(msg).data, status=201)
        save_idem(request.user, state, 'SEND_MESSAGE', msg.id, response)
        return response
