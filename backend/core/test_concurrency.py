"""Run against an isolated PostgreSQL test database, never the business database."""
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from django.db import connection, close_old_connections
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from .models import GamePartition, ProductCategory, Product, UserProfile, AccessToken, Order, PaymentAttempt

@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
@override_settings(DEBUG=True,ALLOW_MOCK_PAYMENT=True)
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        user=get_user_model().objects.create_user('concurrent');UserProfile.objects.create(user=user)
        self.token,_=AccessToken.issue(user)
        game=GamePartition.objects.create(name='并发游戏')
        category=ProductCategory.objects.create(game=game,name='娱乐单')
        self.product=Product.objects.create(game=game,category=category,title='商品',price_cents=100,original_price_cents=100)

    def post(self,path,key,data):
        close_old_connections()
        try:
            client=APIClient();client.credentials(HTTP_AUTHORIZATION='Bearer '+self.token)
            result=client.post(path,data,format='json',HTTP_IDEMPOTENCY_KEY=key)
            return result.status_code,result.data
        finally:close_old_connections()

    def payload(self):return {'product_id':self.product.id,'quantity':1,'expected_product_version':1}

    def test_concurrent_create_same_key(self):
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.post('/api/v1/me/orders/','same',self.payload()),range(2)))
        self.assertEqual([x[0] for x in results],[201,201]);self.assertEqual(Order.objects.count(),1)

    def test_concurrent_pay_different_keys(self):
        _,order=self.post('/api/v1/me/orders/','create',self.payload())
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda key:self.post(f"/api/v1/me/orders/{order['id']}/mock-pay/",key,{}),['pay-a','pay-b']))
        self.assertEqual(sorted(x[0] for x in results),[200,409]);self.assertEqual(PaymentAttempt.objects.filter(status='SUCCEEDED').count(),1)
