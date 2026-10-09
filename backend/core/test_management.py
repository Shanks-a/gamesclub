from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import GamePartition, ProductCategory, Product, UserProfile, AccessToken, AuditLog, Order, PaymentAttempt, HomeEntry

@override_settings(DEBUG=True, ALLOW_DEV_LOGIN=True, ALLOW_MOCK_PAYMENT=True)
class ManagementTests(TestCase):
    def setUp(self):
        self.staff=get_user_model().objects.create_user('operator',password='Test-only-password-123',is_staff=True)
        self.user=get_user_model().objects.create_user('customer')
        UserProfile.objects.create(user=self.user)
        self.game=GamePartition.objects.create(name='测试游戏')
        self.category=ProductCategory.objects.create(game=self.game,name='娱乐单')
        self.product=Product.objects.create(game=self.game,category=self.category,title='商品',price_cents=199,original_price_cents=299)
        self.web=APIClient(enforce_csrf_checks=True)

    def authenticate_web(self):
        info=self.web.get('/api/v1/management/session/')
        token=info.data['csrf_token']
        response=self.web.post('/api/v1/management/login/',{'username':'operator','password':'Test-only-password-123'},format='json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200,response.data)
        self.web.credentials(HTTP_X_CSRFTOKEN=response.data['csrf_token'])

    def test_login_requires_csrf(self):
        response=self.web.post('/api/v1/management/login/',{'username':'operator','password':'Test-only-password-123'},format='json')
        self.assertEqual(response.status_code,403)

    def test_permissions_versions_and_audit(self):
        self.assertEqual(self.web.get('/api/v1/management/products/').status_code,403)
        self.authenticate_web()
        url=f'/api/v1/management/products/{self.product.id}/'
        response=self.web.patch(url,{'title':'新名称','version':1},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['version'],2)
        self.assertEqual(AuditLog.objects.count(),1)
        self.assertEqual(self.web.patch(url,{'title':'旧覆盖','version':1},format='json').status_code,409)
        self.web.credentials()
        self.assertEqual(self.web.patch(url,{'title':'无CSRF','version':2},format='json').status_code,403)

    def test_invalid_category(self):
        self.authenticate_web()
        other=GamePartition.objects.create(name='另一个游戏')
        response=self.web.patch(f'/api/v1/management/products/{self.product.id}/',{'game':other.id,'version':1},format='json')
        self.assertEqual(response.status_code,400)

    def test_product_homeplacements_sync(self):
        self.authenticate_web()
        url=f'/api/v1/management/products/{self.product.id}/'
        # 初始无投放
        self.assertEqual(self.web.get('/api/v1/management/products/').data['results'][0]['homeplacements'],[])
        # 投放 banner + special
        response=self.web.patch(url,{'version':1,'homeplacements':['banner','special']},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(sorted(response.data['homeplacements']),['banner','special'])
        self.assertEqual(set(HomeEntry.objects.filter(product=self.product).values_list('kind',flat=True)),{'banner','special'})
        # 改投放为只 popular：移除 banner/special，新增 popular
        response=self.web.patch(url,{'version':2,'homeplacements':['popular']},format='json')
        self.assertEqual(response.data['homeplacements'],['popular'])
        self.assertEqual(set(HomeEntry.objects.filter(product=self.product).values_list('kind',flat=True)),{'popular'})
        # 清空投放
        response=self.web.patch(url,{'version':3,'homeplacements':[]},format='json')
        self.assertEqual(response.data['homeplacements'],[])
        self.assertEqual(HomeEntry.objects.filter(product=self.product).count(),0)
        # 不传 homeplacements 时不影响现有首页配置
        HomeEntry.objects.create(kind='banner',title='保留',product=self.product)
        self.web.patch(url,{'version':4,'title':'改名'},format='json')
        self.assertEqual(HomeEntry.objects.filter(product=self.product).count(),1)

    def test_home_entry_patch_and_create_ok(self):
        """回归：首页配置自身的增改不能因 homeplacements 逻辑报错（ValueError: Must be Product instance）。"""
        self.authenticate_web()
        home=HomeEntry.objects.create(kind='banner',title='旧标题',product=self.product)
        # PATCH 改标题和图片
        response=self.web.patch(f'/api/v1/management/home/{home.pk}/',{'title':'新标题','image_url':'/media/covers/x.jpg','version':1},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['title'],'新标题')
        home.refresh_from_db()
        self.assertEqual(home.image_url,'/media/covers/x.jpg')
        # POST 新建不跳转的轮播
        response=self.web.post('/api/v1/management/home/',{'kind':'banner','title':'纯展示','target':'none','sort_order':0,'is_enabled':True},format='json')
        self.assertEqual(response.status_code,201,response.data)
        # 新建带商品的特价位
        response=self.web.post('/api/v1/management/home/',{'kind':'special','title':'特价','product':self.product.id,'target':'product','sort_order':0,'is_enabled':True},format='json')
        self.assertEqual(response.status_code,201,response.data)

    def test_catalog_delete_protects_references_and_audits_success(self):
        product_url=f'/api/v1/management/products/{self.product.pk}/'
        self.assertEqual(self.web.delete(product_url,{'version':1},format='json').status_code,403)
        self.authenticate_web()
        home=HomeEntry.objects.create(kind='special',title='精选',product=self.product)
        home_url=f'/api/v1/management/home/{home.pk}/'
        self.assertEqual(self.web.delete(product_url,{'version':1},format='json').status_code,409)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(AuditLog.objects.count(),0)
        self.assertEqual(self.web.delete(home_url,{'version':0},format='json').status_code,409)
        self.assertEqual(self.web.delete(home_url,{'version':1},format='json').status_code,200)
        self.assertFalse(HomeEntry.objects.filter(pk=home.pk).exists())
        self.assertEqual(self.web.delete(product_url,{'version':1},format='json').status_code,200)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(list(AuditLog.objects.values_list('action','resource')), [('delete','home'),('delete','products')])

    def test_ordered_product_cannot_be_deleted(self):
        self.authenticate_web()
        order=self.create_order(self.api_for(self.user))
        self.assertEqual(order.status_code,201,order.data)
        result=self.web.delete(f'/api/v1/management/products/{self.product.pk}/',{'version':1},format='json')
        self.assertEqual(result.status_code,409,result.data)
        self.assertTrue(Order.objects.filter(pk=order.data['id']).exists())
        self.assertEqual(self.web.delete(f'/api/v1/management/orders/{order.data["id"]}/',{'version':1},format='json').status_code,405)

    def api_for(self,user):
        raw,_=AccessToken.issue(user); client=APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+raw);return client

    def create_order(self,client,key='create'):
        return client.post('/api/v1/me/orders/',{'product_id':self.product.id,'quantity':2,'expected_product_version':self.product.version},format='json',HTTP_IDEMPOTENCY_KEY=key)

    def test_snapshot_replay_and_user_isolation(self):
        client=self.api_for(self.user)
        a=self.create_order(client); b=self.create_order(client,'another')
        self.assertEqual(a.status_code,201,a.data); self.assertEqual(b.status_code,201,b.data)
        self.assertNotEqual(a.data['order_no'],b.data['order_no'])
        self.product.price_cents=500;self.product.version=2;self.product.save()
        snapshot=client.get(f"/api/v1/me/orders/{a.data['id']}/")
        self.assertEqual(snapshot.data['total_amount_cents'],398)
        other=get_user_model().objects.create_user('other'); UserProfile.objects.create(user=other)
        other_client=self.api_for(other)
        self.assertEqual(other_client.get('/api/v1/me/orders/').data,[])
        self.assertEqual(other_client.get(f"/api/v1/me/orders/{a.data['id']}/").status_code,404)
        client.post('/api/v1/me/favorites/',{'product_id':self.product.id},format='json')
        self.assertEqual(other_client.get('/api/v1/me/favorites/').data,[])

    def test_payment_resource_and_cancel(self):
        client=self.api_for(self.user); a=self.create_order(client).data; b=self.create_order(client,'second').data
        pay=lambda oid:client.post(f'/api/v1/me/orders/{oid}/mock-pay/',{},format='json',HTTP_IDEMPOTENCY_KEY='payment')
        self.assertEqual(pay(a['id']).status_code,200)
        self.assertEqual(pay(a['id']).status_code,200)
        self.assertEqual(pay(b['id']).status_code,409)
        self.assertEqual(PaymentAttempt.objects.count(),1)
        url=f"/api/v1/me/orders/{b['id']}/cancel/"
        for _ in range(2):self.assertEqual(client.post(url,{},format='json',HTTP_IDEMPOTENCY_KEY='cancel').status_code,200)
        self.assertEqual(client.post(f"/api/v1/me/orders/{b['id']}/mock-pay/",{},format='json',HTTP_IDEMPOTENCY_KEY='cancelled-pay').status_code,409)

    def test_disabled_category_and_logout(self):
        client=self.api_for(self.user); self.category.is_enabled=False; self.category.save()
        self.assertEqual(self.create_order(client).status_code,409)
        self.assertFalse(client.get(f'/api/v1/products/{self.product.pk}/').data['is_available'])
        self.assertEqual(client.post('/api/v1/auth/logout/',{},format='json').status_code,200)
        self.assertEqual(client.get('/api/v1/me/').status_code,401)

    def test_home_visibility_and_upload(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from tempfile import TemporaryDirectory
        from .models import HomeEntry
        self.authenticate_web()
        HomeEntry.objects.create(kind='special',title='精选',product=self.product)
        self.assertEqual(len(APIClient().get('/api/v1/home/').data),1)
        self.product.is_published=False;self.product.save()
        self.assertEqual(APIClient().get('/api/v1/home/').data,[])
        with override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'}}):
            output=io.BytesIO();Image.new('RGB',(8,8)).save(output,'PNG')
            response=self.web.post('/api/v1/management/upload/',{'file':SimpleUploadedFile('test.png',output.getvalue(),content_type='image/png')},format='multipart')
            self.assertEqual(response.status_code,201,response.data)
            bad=self.web.post('/api/v1/management/upload/',{'file':SimpleUploadedFile('bad.png',b'not an image',content_type='image/png')},format='multipart')
            self.assertEqual(bad.status_code,400)
