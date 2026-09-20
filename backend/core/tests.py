from rest_framework.test import APITestCase
from django.test import override_settings
from .models import GamePartition, Product, Order
@override_settings(DEBUG=True)
class FlowTests(APITestCase):
    def setUp(self):
        game=GamePartition.objects.create(name='王者荣耀'); self.product=Product.objects.create(game=game,title='测试服务',price_cents=2900,original_price_cents=3900)
    def login(self):
        response=self.client.post('/api/v1/auth/dev-login/',{},format='json'); self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}")
    def test_order_payment_and_snapshot(self):
        self.login(); response=self.client.post('/api/v1/me/orders/',{'product_id':self.product.id,'quantity':2,'expected_product_version':1},format='json',HTTP_IDEMPOTENCY_KEY='create-1'); self.assertEqual(response.status_code,201); order=response.data
        self.product.price_cents=3500; self.product.version=2; self.product.save(update_fields=['price_cents','version'])
        response=self.client.post(f"/api/v1/me/orders/{order['id']}/mock-pay/",{},format='json',HTTP_IDEMPOTENCY_KEY='pay-1'); self.assertEqual(response.status_code,200); self.assertEqual(response.data['total_amount_cents'],5800); self.assertEqual(response.data['status'],'PENDING_ARRANGEMENT')
    def test_idempotent_create_and_user_isolation(self):
        self.login(); payload={'product_id':self.product.id,'quantity':1,'expected_product_version':1}; a=self.client.post('/api/v1/me/orders/',payload,format='json',HTTP_IDEMPOTENCY_KEY='same'); b=self.client.post('/api/v1/me/orders/',payload,format='json',HTTP_IDEMPOTENCY_KEY='same'); self.assertEqual(a.data['id'],b.data['id']); self.assertEqual(Order.objects.count(),1)
    def test_product_version_conflict(self):
        self.login(); self.product.version=2; self.product.save(update_fields=['version']); response=self.client.post('/api/v1/me/orders/',{'product_id':self.product.id,'quantity':1,'expected_product_version':1},format='json',HTTP_IDEMPOTENCY_KEY='old'); self.assertEqual(response.status_code,409)
