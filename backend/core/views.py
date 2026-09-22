import hashlib, json
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import AccessToken, GamePartition, Product, ProductCategory, Favorite, Order, OrderStatusHistory, PaymentAttempt, IdempotencyRecord, UserProfile
from .serializers import GameSerializer, CategorySerializer, ProductSerializer, FavoriteSerializer, OrderSerializer, ProductWriteSerializer

def err(message, code, http=400):
    return Response({'error': {'code': code, 'message': message}}, status=http)
def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def get_idem(user, request, action):
    key = request.headers.get('Idempotency-Key')
    if not key: return None, err('缺少 Idempotency-Key', 'IDEMPOTENCY_KEY_REQUIRED')
    h = digest(request.data); old = IdempotencyRecord.objects.filter(user=user, key=key).first()
    if old:
        if old.request_hash != h or old.action != action: return None, err('幂等键已用于其他请求', 'IDEMPOTENCY_CONFLICT', 409)
        return old, Response(old.response_json, status=old.status_code)
    return (key, h), None
def save_idem(user, state, action, resource, response):
    key, h = state
    IdempotencyRecord.objects.create(user=user, key=key, request_hash=h, action=action, resource_id=str(resource), response_json=response.data, status_code=response.status_code)

@api_view(['POST'])
@permission_classes([AllowAny])
def dev_login(request):
    if not settings.DEBUG: return err('开发登录未开放', 'DEV_LOGIN_DISABLED', 403)
    User = get_user_model(); user, _ = User.objects.get_or_create(username='dev-player'); UserProfile.objects.get_or_create(user=user)
    raw, _ = AccessToken.issue(user)
    return Response({'access_token': raw, 'user': {'id':user.id, 'nickname':user.profile.nickname, 'avatar_url':user.profile.avatar_url}})

@api_view(['GET'])
def me(request):
    return Response({'id':request.user.id, 'nickname':request.user.profile.nickname, 'avatar_url':request.user.profile.avatar_url})

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
    if request.method == 'GET': return Response(OrderSerializer(Order.objects.filter(user=request.user).order_by('-created_at'), many=True).data)
    quantity = request.data.get('quantity'); expected = request.data.get('expected_product_version')
    if not isinstance(quantity, int): return err('数量必须为整数', 'INVALID_QUANTITY')
    with transaction.atomic():
        try: p = Product.objects.select_for_update().select_related('game').get(pk=request.data.get('product_id'))
        except Product.DoesNotExist: return err('商品不存在', 'NOT_FOUND', 404)
        if not p.is_published or not p.game.is_enabled: return err('商品已下架', 'PRODUCT_UNAVAILABLE', 409)
        if expected != p.version: return err('商品已更新，请重新确认价格', 'PRODUCT_VERSION_CONFLICT', 409)
        if quantity < p.min_quantity or quantity > p.max_quantity: return err('购买数量超出范围', 'INVALID_QUANTITY')
        state, replay = get_idem(request.user, request, 'CREATE_ORDER')
        if replay: return replay
        key, h = state
        order = Order.objects.create(order_no=f'GC{timezone.now():%Y%m%d%H%M%S}', user=request.user, product=p, game_name_snapshot=p.game.name, product_title_snapshot=p.title, cover_url_snapshot=p.cover_url, unit_price_cents=p.price_cents, total_amount_cents=p.price_cents*quantity, quantity=quantity)
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
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        if order.status != Order.Status.PENDING_PAYMENT: return err('当前状态不能取消', 'ORDER_STATE_CONFLICT', 409)
        old = order.status; order.status = Order.Status.CANCELLED; order.version += 1; order.save(update_fields=['status','version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action='CANCEL', actor=request.user)
    return Response(OrderSerializer(order).data)

@api_view(['POST'])
def mock_pay(request, pk):
    with transaction.atomic():
        try: order = Order.objects.select_for_update().get(pk=pk, user=request.user)
        except Order.DoesNotExist: return err('订单不存在', 'NOT_FOUND', 404)
        state, replay = get_idem(request.user, request, 'MOCK_PAY')
        if replay: return replay
        if order.status != Order.Status.PENDING_PAYMENT or order.payment_status != Order.PaymentStatus.UNPAID: return err('当前状态不能付款', 'ORDER_STATE_CONFLICT', 409)
        key, h = state; PaymentAttempt.objects.create(order=order, idempotency_key=key, amount_cents=order.total_amount_cents, status=PaymentAttempt.Status.SUCCEEDED, completed_at=timezone.now())
        old = order.status; order.payment_status=Order.PaymentStatus.PAID; order.status=Order.Status.PENDING_ARRANGEMENT; order.version += 1; order.save(update_fields=['payment_status','status','version','updated_at'])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=order.status, action='MOCK_PAY', actor=request.user)
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
