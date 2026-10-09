"""Session-authenticated operations console; public catalog remains array-compatible."""
import io
import uuid
from django.contrib.auth import authenticate, login, logout
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_protect
from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from .models import GamePartition, ProductCategory, Product, HomeEntry, AuditLog, Order, OrderStatusHistory, Partner, PartnerApplication
from .serializers import ProductSerializer, OrderSerializer, PartnerSerializer, PartnerApplicationSerializer

class LoginThrottle(AnonRateThrottle):
    rate = '10/min'

def endpoint(methods, public=False):
    def wrap(fn):
        fn = permission_classes([AllowAny if public else IsAdminUser])(fn)
        fn = authentication_classes([SessionAuthentication])(fn)
        return api_view(methods)(fn)
    return wrap

@endpoint(['GET'], public=True)
@ensure_csrf_cookie
def session_info(request):
    token = get_token(request)
    return Response({'csrf_token':token, 'authenticated':bool(request.user.is_authenticated and request.user.is_staff), 'username':request.user.get_username()})

@endpoint(['POST'], public=True)
@throttle_classes([LoginThrottle])
@csrf_protect
def session_login(request):
    user = authenticate(request, username=request.data.get('username'), password=request.data.get('password'))
    if not user or not user.is_staff: return Response({'error':{'message':'账号、密码或管理员权限不正确'}}, status=403)
    login(request, user)
    return Response({'username':user.username, 'csrf_token':get_token(request)})

@endpoint(['POST'])
def session_logout(request):
    logout(request)
    return Response({'ok':True})

class GameWrite(serializers.ModelSerializer):
    class Meta:
        model = GamePartition
        fields = '__all__'
        read_only_fields = ['version']

class CategoryWrite(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ['version','updated_at']
    def validate(self, attrs):
        if self.instance and 'game' in attrs and attrs['game'].pk != self.instance.game_id and self.instance.products.exists():
            raise serializers.ValidationError('已有商品的类型不能更换游戏')
        return attrs

HOME_KINDS = ('banner', 'special', 'popular')

class ProductWrite(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all(), required=True, allow_null=False)
    # 可选：商品要投放的首页位置（banner/special/popular）。传入则按给定集合同步首页配置；不传则不动首页。
    homeplacements = serializers.ListField(child=serializers.ChoiceField(choices=HOME_KINDS), required=False, write_only=True)
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['version','updated_at']
    def validate(self, attrs):
        obj = Product()
        if self.instance:
            for field in Product._meta.fields: setattr(obj, field.attname, getattr(self.instance, field.attname))
        for key, value in attrs.items(): setattr(obj, key, value)
        from django.core.exceptions import ValidationError
        try: obj.clean()
        except ValidationError as exc: raise serializers.ValidationError(exc.message_dict)
        return attrs

class HomeWrite(serializers.ModelSerializer):
    class Meta:
        model = HomeEntry
        fields = '__all__'
        read_only_fields = ['version','updated_at']
    def validate(self, attrs):
        value = lambda k: attrs.get(k, getattr(self.instance, k, None))
        if (value('kind') in ('special','popular') or value('target') == 'product') and not value('product'):
            raise serializers.ValidationError('请指定商品')
        if value('target') == 'game' and not value('game'): raise serializers.ValidationError('请指定游戏')
        return attrs

REGISTRY = {'games':(GamePartition,GameWrite), 'categories':(ProductCategory,CategoryWrite), 'products':(Product,ProductWrite), 'home':(HomeEntry,HomeWrite)}

def sync_product_home(product, placements):
    """按给定位置集合同步商品的首页投放。

    placements: HOME_KINDS 的子集。会：
    - 移除该商品现有、但不在 placements 中的 HomeEntry（仅 product 关联的）；
    - 为 placements 中缺失的位置创建 HomeEntry（target='product'，标题/封面复用商品）。
    """
    wanted = set(placements or [])
    existing = HomeEntry.objects.filter(product=product)
    existing_kinds = {e.kind for e in existing}
    # 移除不再投放的位置
    for e in existing:
        if e.kind not in wanted:
            e.delete()
    # 新增缺失的位置
    for kind in wanted:
        if kind in existing_kinds:
            continue
        HomeEntry.objects.create(
            kind=kind, title=product.title, image_url=product.cover_url or '',
            product=product, target='product', sort_order=0, is_enabled=True,
        )

def page(request, qs, serialize):
    try: number=max(1,int(request.query_params.get('page',1))); size=min(100,max(1,int(request.query_params.get('page_size',20))))
    except ValueError: raise serializers.ValidationError('分页参数必须为整数')
    return Response({'count':qs.count(),'page':number,'page_size':size,'results':[serialize(o) for o in qs[(number-1)*size:number*size]]})

@endpoint(['GET','POST','PATCH','DELETE'])
def catalog(request, resource, pk=None):
    if resource not in REGISTRY: return Response(status=404)
    model, serializer = REGISTRY[resource]
    if request.method == 'GET':
        qs=model.objects.all().order_by('id')
        # 商品额外附带首页投放位置，供前端编辑回显
        placements_map = {}
        if resource == 'products':
            placements_map = {}
            for product_id, kind in HomeEntry.objects.filter(product__isnull=False).values_list('product_id', 'kind'):
                placements_map.setdefault(product_id, []).append(kind)
        if pk:
            obj=qs.filter(pk=pk).first()
            if not obj: return Response(status=404)
            data = dict(serializer(obj).data)
            if resource == 'products':
                data['homeplacements'] = placements_map.get(obj.pk, [])
            return Response(data)
        q=request.query_params.get('q','')
        if q: qs=qs.filter(**{('title' if resource in ('products','home') else 'name')+'__icontains':q})
        for field in ('game','category'):
            if request.query_params.get(field) and field in {f.name for f in model._meta.fields}:
                try: qs=qs.filter(**{field+'_id':int(request.query_params[field])})
                except ValueError: raise serializers.ValidationError('筛选编号必须为整数')
        flag='is_published' if resource=='products' else 'is_enabled'
        if request.query_params.get('enabled') in ('true','false'): qs=qs.filter(**{flag:request.query_params['enabled']=='true'})
        def serialize_product(o):
            data = dict(serializer(o).data)
            if resource == 'products':
                data['homeplacements'] = placements_map.get(o.pk, [])
            return data
        return page(request,qs,serialize_product)
    if (request.method=='POST' and pk) or (request.method in ('PATCH','DELETE') and not pk): return Response(status=405)
    try:
        with transaction.atomic():
            obj=model.objects.select_for_update().filter(pk=pk).first() if pk else None
            if pk and not obj: return Response(status=404)
            if obj and request.data.get('version') != obj.version: return Response({'error':{'message':'数据已更新，请重新加载后操作','code':'VERSION_CONFLICT'}},status=409)
            before=dict(serializer(obj).data) if obj else {}
            if request.method == 'DELETE':
                obj.delete()
                AuditLog.objects.create(actor=request.user,action='delete',resource=resource,resource_id=str(pk),before=before,after={})
                return Response({'id':pk,'deleted':True})
            form=serializer(obj,data=request.data,partial=bool(obj)); form.is_valid(raise_exception=True)
            saved=form.save(version=obj.version+1 if obj else 1)
            # 商品保存后，若带 homeplacements 则同步首页投放
            if resource == 'products' and 'homeplacements' in form.validated_data:
                sync_product_home(saved, form.validated_data['homeplacements'])
            result=dict(serializer(saved).data)
            if resource == 'products':
                result['homeplacements'] = list(HomeEntry.objects.filter(product=saved).values_list('kind', flat=True))
            AuditLog.objects.create(actor=request.user,action='update' if obj else 'create',resource=resource,resource_id=str(saved.pk),before=before,after=result)
            return Response(result,status=200 if obj else 201)
    except (ProtectedError, IntegrityError):
        return Response({'error':{'message':'该记录已有业务关联，不能直接删除；请先移除首页配置等引用，或将记录停用／下架','code':'DELETE_CONFLICT'}},status=409)

@endpoint(['GET'])
def overview(request):
    return Response({'products':Product.objects.count(),'published':Product.objects.filter(is_published=True).count(),'orders':Order.objects.count(),'states':list(Order.objects.values('status').annotate(count=Count('id'))),'simulation':True})

@endpoint(['GET'])
def orders(request, pk=None):
    qs=Order.objects.select_related('user').order_by('-id')
    if pk:
        obj=qs.filter(pk=pk).first()
        if not obj:return Response(status=404)
        return Response({**OrderSerializer(obj).data,'user':obj.user.username,'user_id':obj.user_id,'history':list(obj.status_history.values('from_status','to_status','action','actor_id','created_at')),'payments':list(obj.payments.values('id','amount_cents','status','created_at','completed_at'))})
    if request.query_params.get('q'):qs=qs.filter(order_no__icontains=request.query_params['q'])
    if request.query_params.get('user'):qs=qs.filter(user__username__icontains=request.query_params['user'])
    if request.query_params.get('status'):qs=qs.filter(status=request.query_params['status'])
    for name,lookup in [('from','created_at__date__gte'),('to','created_at__date__lte')]:
        if request.query_params.get(name):
            value=parse_date(request.query_params[name])
            if not value:raise serializers.ValidationError('日期格式为 YYYY-MM-DD')
            qs=qs.filter(**{lookup:value})
    return page(request,qs,lambda o:{**OrderSerializer(o).data,'user':o.user.username})

@endpoint(['GET'])
def audit(request):
    return page(request,AuditLog.objects.select_related('actor').order_by('-id'),lambda o:{'id':o.pk,'actor':o.actor.username,'action':o.action,'resource':o.resource,'resource_id':o.resource_id,'before':o.before,'after':o.after,'created_at':o.created_at})

@endpoint(['POST'])
def upload(request):
    from PIL import Image, UnidentifiedImageError
    file=request.FILES.get('file')
    if not file or file.size > 5*1024*1024:raise serializers.ValidationError('请选择不超过5MB的图片')
    try:
        picture=Image.open(file)
        if picture.format not in ('JPEG','PNG','WEBP') or picture.width*picture.height>20_000_000:raise ValueError()
        picture.load(); picture=picture.convert('RGB'); output=io.BytesIO(); picture.save(output,format='JPEG',quality=90)
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):raise serializers.ValidationError('仅支持有效的 JPEG、PNG、WebP 图片')
    path=default_storage.save('covers/'+uuid.uuid4().hex+'.jpg',ContentFile(output.getvalue()))
    AuditLog.objects.create(actor=request.user,action='upload',resource='media',resource_id=path,after={'url':default_storage.url(path)})
    return Response({'url':default_storage.url(path)},status=201)

@endpoint(['GET'], public=True)
def public_home(request):
    entries=[]
    for obj in HomeEntry.objects.filter(is_enabled=True).select_related('product__game','product__category','game').order_by('sort_order','id'):
        product=ProductSerializer(obj.product).data if obj.product_id else None
        if product and not product['is_available']:continue
        if obj.game_id and not obj.game.is_enabled:continue
        entries.append({**HomeWrite(obj).data,'product_detail':product,'game_name':obj.game.name if obj.game_id else ''})
    return Response(entries)

# ============ P4 陪玩审核 / 档案 / 派单 ============

@endpoint(['GET'])
def partner_applications(request, pk=None):
    if pk:
        obj = PartnerApplication.objects.select_related('user__profile','game','reviewed_by').filter(pk=pk).first()
        return Response(PartnerApplicationSerializer(obj).data) if obj else Response(status=404)
    qs = PartnerApplication.objects.select_related('user__profile','game','reviewed_by').order_by('-created_at')
    if request.query_params.get('status'): qs = qs.filter(status=request.query_params['status'])
    return page(request, qs, lambda o: PartnerApplicationSerializer(o).data)

@endpoint(['POST'])
def partner_application_approve(request, pk):
    from django.utils import timezone as tz
    with transaction.atomic():
        try: app = PartnerApplication.objects.select_for_update().get(pk=pk)
        except PartnerApplication.DoesNotExist: return Response(status=404)
        if app.status != PartnerApplication.Status.PENDING:
            return Response({'error':{'message':'该申请已处理','code':'APPLICATION_PROCESSED'}},status=409)
        # 建立（或复用）陪玩档案，绑申请中的游戏分区
        partner, created = Partner.objects.get_or_create(user=app.user, defaults={'game': app.game})
        if not created and partner.game_id != app.game_id:
            return Response({'error':{'message':f'该用户已绑定分区「{partner.game.name}」，与本申请分区不一致','code':'PARTNER_GAME_MISMATCH'}},status=409)
        app.status = PartnerApplication.Status.APPROVED; app.reviewed_by = request.user; app.reviewed_at = tz.now()
        app.save(update_fields=['status','reviewed_by','reviewed_at'])
        AuditLog.objects.create(actor=request.user, action='approve_partner', resource='partner_application', resource_id=str(pk), after={'user_id':app.user_id,'game_id':app.game_id})
        return Response({'ok':True,'partner_id':partner.id,'created':created})

@endpoint(['POST'])
def partner_application_reject(request, pk):
    from django.utils import timezone as tz
    with transaction.atomic():
        try: app = PartnerApplication.objects.select_for_update().get(pk=pk)
        except PartnerApplication.DoesNotExist: return Response(status=404)
        if app.status != PartnerApplication.Status.PENDING:
            return Response({'error':{'message':'该申请已处理','code':'APPLICATION_PROCESSED'}},status=409)
        app.status = PartnerApplication.Status.REJECTED; app.reviewed_by = request.user; app.reviewed_at = tz.now()
        app.save(update_fields=['status','reviewed_by','reviewed_at'])
        AuditLog.objects.create(actor=request.user, action='reject_partner', resource='partner_application', resource_id=str(pk), after={'user_id':app.user_id,'game_id':app.game_id})
        return Response({'ok':True})

@endpoint(['GET'])
def partners(request, pk=None):
    if pk:
        obj = Partner.objects.select_related('user__profile','game').filter(pk=pk).first()
        return Response(PartnerSerializer(obj).data) if obj else Response(status=404)
    qs = Partner.objects.select_related('user__profile','game').order_by('-id')
    if request.query_params.get('q'): qs = qs.filter(user__username__icontains=request.query_params['q'])
    if request.query_params.get('game'):
        try: qs = qs.filter(game_id=int(request.query_params['game']))
        except ValueError: raise serializers.ValidationError('筛选编号必须为整数')
    if request.query_params.get('active') in ('true','false'): qs = qs.filter(is_active=request.query_params['active']=='true')
    return page(request, qs, lambda o: PartnerSerializer(o).data)

@endpoint(['PATCH'])
def partner_detail(request, pk):
    with transaction.atomic():
        try: partner = Partner.objects.select_for_update().get(pk=pk)
        except Partner.DoesNotExist: return Response(status=404)
        if request.data.get('version') != partner.version:
            return Response({'error':{'message':'数据已更新，请重新加载后操作','code':'VERSION_CONFLICT'}},status=409)
        allowed = {'is_active','intro','game'}
        unknown = set(request.data) - allowed - {'version'}
        if unknown: return Response({'error':{'message':'不接受字段：'+','.join(sorted(unknown)),'code':'INVALID_FIELDS'}},status=400)
        if 'game' in request.data and request.data['game'] is not None and type(request.data['game']) is not int:
            return Response({'error':{'message':'游戏分区编号必须为整数','code':'INVALID_GAME'}},status=400)
        if 'is_active' in request.data and type(request.data['is_active']) is not bool:
            return Response({'error':{'message':'接单开关必须为布尔值','code':'INVALID_ACTIVE'}},status=400)
        before = dict(PartnerSerializer(partner).data)
        if 'game' in request.data and request.data['game'] is not None: partner.game_id = request.data['game']
        if 'intro' in request.data: partner.intro = request.data['intro']
        if 'is_active' in request.data: partner.is_active = request.data['is_active']
        partner.version += 1; partner.save()
        result = dict(PartnerSerializer(partner).data)
        AuditLog.objects.create(actor=request.user, action='update', resource='partner', resource_id=str(pk), before=before, after=result)
    return Response(result)

@endpoint(['DELETE'])
def partner_delete(request, pk):
    """删除陪玩档案。有未完成派单（非取消/完成）时拒绝，保护业务一致性。"""
    with transaction.atomic():
        try: partner = Partner.objects.select_for_update().get(pk=pk)
        except Partner.DoesNotExist: return Response(status=404)
        if request.data.get('version') != partner.version:
            return Response({'error':{'message':'数据已更新，请重新加载后操作','code':'VERSION_CONFLICT'}},status=409)
        # 存在未完成的派单则拒绝删除
        active = Order.objects.filter(partner=partner).exclude(status__in=[Order.Status.CANCELLED, Order.Status.COMPLETED]).exists()
        if active:
            return Response({'error':{'message':'该陪玩存在未完成订单，无法删除','code':'PARTNER_HAS_ACTIVE_ORDERS'}},status=409)
        # 驳回相关待审核申请，避免出现悬挂档案引用
        PartnerApplication.objects.filter(user=partner.user, status=PartnerApplication.Status.PENDING).update(status=PartnerApplication.Status.REJECTED)
        before = dict(PartnerSerializer(partner).data)
        partner.delete()
        AuditLog.objects.create(actor=request.user, action='delete', resource='partner', resource_id=str(pk), before=before)
    return Response({'ok':True})

@endpoint(['POST'])
def order_assign(request, pk):
    """派单：PENDING_ARRANGEMENT -> PENDING_ACCEPTANCE，指定陪玩，含时段冲突检查。"""
    partner_id = request.data.get('partner_id') if isinstance(request.data, dict) else None
    if type(partner_id) is not int: return Response({'error':{'message':'请指定陪玩','code':'INVALID_PARTNER'}},status=400)
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(pk=pk).first()
        if not order: return Response(status=404)
        if order.status != Order.Status.PENDING_ARRANGEMENT:
            return Response({'error':{'message':'订单当前状态不能派单','code':'ORDER_STATE_CONFLICT'}},status=409)
        partner = Partner.objects.select_for_update().filter(pk=partner_id).first()
        if not partner: return Response({'error':{'message':'陪玩不存在','code':'NOT_FOUND'}},status=404)
        if not partner.is_active: return Response({'error':{'message':'该陪玩已关闭接单','code':'PARTNER_DISABLED'}},status=409)
        # 冲突检查：同一陪玩同一天同时段已有未完成订单
        if order.appointment_date and order.appointment_slot:
            conflict = Order.objects.filter(
                partner=partner, appointment_date=order.appointment_date, appointment_slot=order.appointment_slot
            ).exclude(status__in=[Order.Status.CANCELLED, Order.Status.COMPLETED]).exclude(pk=order.pk).exists()
            if conflict:
                return Response({'error':{'message':'该陪玩在该时段已有未完成订单，请换人','code':'PARTNER_CONFLICT'}},status=409)
        old = order.status; order.partner = partner; order.status = Order.Status.PENDING_ACCEPTANCE; order.version += 1
        order.save(update_fields=['partner','status','version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action='ASSIGN', actor=request.user)
        AuditLog.objects.create(actor=request.user, action='assign_order', resource='order', resource_id=str(pk), after={'partner_id':partner_id})
        return Response(OrderSerializer(order).data)

# ============ P4 订单管理端 CRUD ============

@endpoint(['GET'])
def customers(request):
    """列出客户（非管理员账号），供管理端建单/编辑时选择。"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    qs = User.objects.filter(is_staff=False, is_superuser=False).select_related('profile').order_by('-date_joined')
    q = request.query_params.get('q', '')
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(profile__nickname__icontains=q))
    def fmt(u):
        try: nickname = u.profile.nickname
        except Exception: nickname = ''
        return {'id': u.pk, 'username': u.username, 'nickname': nickname or u.username}
    return page(request, qs, fmt)

def _order_from_payload(data, partial=False):
    """校验并规范化建单/编辑的字段，返回 (error_response, cleaned_dict)。"""
    fields = {'user_id','product_id','quantity','appointment_date','appointment_slot','status','payment_status','partner_id'}
    unknown = set(data) - fields
    if unknown: return Response({'error':{'message':'不接受字段：'+','.join(sorted(unknown)),'code':'INVALID_FIELDS'}},status=400), None
    out = {}
    if 'user_id' in data:
        if type(data['user_id']) is not int: return Response({'error':{'message':'请选择客户','code':'INVALID_USER'}},status=400), None
        out['user_id'] = data['user_id']
    if 'product_id' in data:
        if type(data['product_id']) is not int: return Response({'error':{'message':'请选择商品','code':'INVALID_PRODUCT'}},status=400), None
        out['product_id'] = data['product_id']
    if 'quantity' in data:
        if type(data['quantity']) is not int or data['quantity'] < 1: return Response({'error':{'message':'数量必须为正整数','code':'INVALID_QUANTITY'}},status=400), None
        out['quantity'] = data['quantity']
    if 'status' in data:
        if data['status'] not in Order.Status.values: return Response({'error':{'message':'订单状态无效','code':'INVALID_STATUS'}},status=400), None
        out['status'] = data['status']
    if 'payment_status' in data:
        if data['payment_status'] not in Order.PaymentStatus.values: return Response({'error':{'message':'付款状态无效','code':'INVALID_PAYMENT_STATUS'}},status=400), None
        out['payment_status'] = data['payment_status']
    if 'partner_id' in data:
        if data['partner_id'] is not None and type(data['partner_id']) is not int: return Response({'error':{'message':'陪玩编号无效','code':'INVALID_PARTNER'}},status=400), None
        out['partner_id'] = data['partner_id']
    appt_date = data.get('appointment_date'); appt_slot = data.get('appointment_slot')
    if 'appointment_date' in data or 'appointment_slot' in data:
        if bool(appt_date) != bool(appt_slot): return Response({'error':{'message':'预约日期与时段需同时提供','code':'INVALID_APPOINTMENT'}},status=400), None
        if appt_slot and appt_slot not in Order.Slot.values: return Response({'error':{'message':'预约时段无效','code':'INVALID_APPOINTMENT'}},status=400), None
        if appt_date:
            d = parse_date(str(appt_date))
            if not d: return Response({'error':{'message':'预约日期格式为 YYYY-MM-DD','code':'INVALID_APPOINTMENT'}},status=400), None
            out['appointment_date'] = d
        else:
            out['appointment_date'] = None
        out['appointment_slot'] = appt_slot or None
    return None, out

@endpoint(['POST'])
def order_create(request):
    """管理员手动建单：选客户 + 商品 + 数量 + 预约时段（可选状态/付款/陪玩）。"""
    data = request.data if isinstance(request.data, dict) else {}
    err_resp, cleaned = _order_from_payload(data)
    if err_resp: return err_resp
    if 'user_id' not in cleaned: return Response({'error':{'message':'请选择客户','code':'INVALID_USER'}},status=400)
    if 'product_id' not in cleaned: return Response({'error':{'message':'请选择商品','code':'INVALID_PRODUCT'}},status=400)
    quantity = cleaned.get('quantity', 1)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    with transaction.atomic():
        try: customer = User.objects.get(pk=cleaned['user_id'], is_staff=False, is_superuser=False)
        except User.DoesNotExist: return Response({'error':{'message':'客户不存在','code':'NOT_FOUND'}},status=404)
        try: p = Product.objects.select_for_update().get(pk=cleaned['product_id'])
        except Product.DoesNotExist: return Response({'error':{'message':'商品不存在','code':'NOT_FOUND'}},status=404)
        game = GamePartition.objects.get(pk=p.game_id)
        category = ProductCategory.objects.filter(pk=p.category_id).first()
        if not p.is_published or not game.is_enabled or not category or not category.is_enabled or category.game_id != game.id:
            return Response({'error':{'message':'商品已下架','code':'PRODUCT_UNAVAILABLE'}},status=409)
        if quantity < p.min_quantity or quantity > p.max_quantity:
            return Response({'error':{'message':'购买数量超出范围','code':'INVALID_QUANTITY'}},status=400)
        partner = None
        if cleaned.get('partner_id'):
            partner = Partner.objects.filter(pk=cleaned['partner_id']).first()
            if not partner: return Response({'error':{'message':'陪玩不存在','code':'NOT_FOUND'}},status=404)
        order = Order.objects.create(
            order_no='GC'+uuid.uuid4().hex[:30], user=customer, product=p, partner=partner,
            game_name_snapshot=game.name, product_title_snapshot=p.title, cover_url_snapshot=p.cover_url,
            unit_price_cents=p.price_cents, total_amount_cents=p.price_cents*quantity, quantity=quantity,
            appointment_date=cleaned.get('appointment_date'), appointment_slot=cleaned.get('appointment_slot'),
            status=cleaned.get('status', Order.Status.PENDING_PAYMENT),
            payment_status=cleaned.get('payment_status', Order.PaymentStatus.UNPAID))
        OrderStatusHistory.objects.create(order=order, to_status=order.status, action='MANUAL_CREATE', actor=request.user)
        AuditLog.objects.create(actor=request.user, action='create_order', resource='order', resource_id=str(order.pk), after={'user_id':customer.id,'product_id':p.id,'quantity':quantity})
    return Response(OrderSerializer(order).data, status=201)

@endpoint(['PATCH'])
def order_update(request, pk):
    """管理员编辑订单：改客户/商品/数量/状态/付款/陪玩/时段。"""
    data = request.data if isinstance(request.data, dict) else {}
    err_resp, cleaned = _order_from_payload(data)
    if err_resp: return err_resp
    if not cleaned: return Response({'error':{'message':'没有可更新的字段','code':'NO_FIELDS'}},status=400)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    with transaction.atomic():
        try: order = Order.objects.select_for_update().get(pk=pk)
        except Order.DoesNotExist: return Response(status=404)
        if 'user_id' in cleaned:
            try: customer = User.objects.get(pk=cleaned['user_id'], is_staff=False, is_superuser=False)
            except User.DoesNotExist: return Response({'error':{'message':'客户不存在','code':'NOT_FOUND'}},status=404)
            order.user = customer
        if 'product_id' in cleaned:
            try: p = Product.objects.select_for_update().get(pk=cleaned['product_id'])
            except Product.DoesNotExist: return Response({'error':{'message':'商品不存在','code':'NOT_FOUND'}},status=404)
            game = GamePartition.objects.get(pk=p.game_id)
            category = ProductCategory.objects.filter(pk=p.category_id).first()
            if not p.is_published or not game.is_enabled or not category or not category.is_enabled or category.game_id != game.id:
                return Response({'error':{'message':'商品已下架','code':'PRODUCT_UNAVAILABLE'}},status=409)
            order.product = p; order.game_name_snapshot = game.name; order.product_title_snapshot = p.title
            order.cover_url_snapshot = p.cover_url; order.unit_price_cents = p.price_cents
        quantity = cleaned.get('quantity', order.quantity)
        if quantity < order.product.min_quantity or quantity > order.product.max_quantity:
            return Response({'error':{'message':'购买数量超出范围','code':'INVALID_QUANTITY'}},status=400)
        order.quantity = quantity
        order.total_amount_cents = order.unit_price_cents * quantity
        if 'status' in cleaned: order.status = cleaned['status']
        if 'payment_status' in cleaned: order.payment_status = cleaned['payment_status']
        if 'partner_id' in cleaned:
            if cleaned['partner_id'] is None:
                order.partner = None
            else:
                partner = Partner.objects.filter(pk=cleaned['partner_id']).first()
                if not partner: return Response({'error':{'message':'陪玩不存在','code':'NOT_FOUND'}},status=404)
                order.partner = partner
        if 'appointment_date' in cleaned: order.appointment_date = cleaned['appointment_date']
        if 'appointment_slot' in cleaned: order.appointment_slot = cleaned['appointment_slot']
        order.version += 1; order.save()
        AuditLog.objects.create(actor=request.user, action='update_order', resource='order', resource_id=str(pk), after={'status':order.status,'quantity':order.quantity})
    return Response(OrderSerializer(order).data)

@endpoint(['DELETE'])
def order_delete(request, pk):
    """管理员删除订单：先清关联的支付记录与状态历史。"""
    with transaction.atomic():
        try: order = Order.objects.select_for_update().get(pk=pk)
        except Order.DoesNotExist: return Response(status=404)
        order.payments.all().delete()
        OrderStatusHistory.objects.filter(order=order).delete()
        before = dict(OrderSerializer(order).data)
        order.delete()
        AuditLog.objects.create(actor=request.user, action='delete_order', resource='order', resource_id=str(pk), before=before)
    return Response({'id': pk, 'deleted': True})
