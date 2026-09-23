"""Session-authenticated operations console; public catalog remains array-compatible."""
import io
import uuid
from django.contrib.auth import authenticate, login, logout
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, Count
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
from .models import GamePartition, ProductCategory, Product, HomeEntry, AuditLog, Order
from .serializers import ProductSerializer, OrderSerializer

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

class ProductWrite(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all(), required=True, allow_null=False)
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

def page(request, qs, serialize):
    try: number=max(1,int(request.query_params.get('page',1))); size=min(100,max(1,int(request.query_params.get('page_size',20))))
    except ValueError: raise serializers.ValidationError('分页参数必须为整数')
    return Response({'count':qs.count(),'page':number,'page_size':size,'results':[serialize(o) for o in qs[(number-1)*size:number*size]]})

@endpoint(['GET','POST','PATCH'])
def catalog(request, resource, pk=None):
    if resource not in REGISTRY: return Response(status=404)
    model, serializer = REGISTRY[resource]
    if request.method == 'GET':
        qs=model.objects.all().order_by('id')
        if pk:
            obj=qs.filter(pk=pk).first()
            return Response(serializer(obj).data) if obj else Response(status=404)
        q=request.query_params.get('q','')
        if q: qs=qs.filter(**{('title' if resource in ('products','home') else 'name')+'__icontains':q})
        for field in ('game','category'):
            if request.query_params.get(field) and field in {f.name for f in model._meta.fields}:
                try: qs=qs.filter(**{field+'_id':int(request.query_params[field])})
                except ValueError: raise serializers.ValidationError('筛选编号必须为整数')
        flag='is_published' if resource=='products' else 'is_enabled'
        if request.query_params.get('enabled') in ('true','false'): qs=qs.filter(**{flag:request.query_params['enabled']=='true'})
        return page(request,qs,lambda o:serializer(o).data)
    if (request.method=='POST' and pk) or (request.method=='PATCH' and not pk): return Response(status=405)
    with transaction.atomic():
        obj=model.objects.select_for_update().filter(pk=pk).first() if pk else None
        if pk and not obj: return Response(status=404)
        if obj and request.data.get('version') != obj.version: return Response({'error':{'message':'数据已更新，请重新加载后编辑','code':'VERSION_CONFLICT'}},status=409)
        before=dict(serializer(obj).data) if obj else {}
        form=serializer(obj,data=request.data,partial=bool(obj)); form.is_valid(raise_exception=True)
        saved=form.save(version=obj.version+1 if obj else 1)
        result=dict(serializer(saved).data)
        AuditLog.objects.create(actor=request.user,action='update' if obj else 'create',resource=resource,resource_id=str(saved.pk),before=before,after=result)
        return Response(result,status=200 if obj else 201)

@endpoint(['GET'])
def overview(request):
    return Response({'products':Product.objects.count(),'published':Product.objects.filter(is_published=True).count(),'orders':Order.objects.count(),'states':list(Order.objects.values('status').annotate(count=Count('id'))),'simulation':True})

@endpoint(['GET'])
def orders(request, pk=None):
    qs=Order.objects.select_related('user').order_by('-id')
    if pk:
        obj=qs.filter(pk=pk).first()
        if not obj:return Response(status=404)
        return Response({**OrderSerializer(obj).data,'user':obj.user.username,'history':list(obj.status_history.values('from_status','to_status','action','actor_id','created_at')),'payments':list(obj.payments.values('id','amount_cents','status','created_at','completed_at'))})
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
