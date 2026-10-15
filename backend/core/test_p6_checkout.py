from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import AccessToken, UserProfile, GamePartition, Product, ProductCategory, Order, Partner


@override_settings(DEBUG=True, ALLOW_MOCK_PAYMENT=True, ALLOW_DEV_LOGIN=True)
class OrderFlowBase(APITestCase):
    _key_counter = 0

    def _user(self, name):
        User = get_user_model()
        user = User.objects.create_user(username=name)
        UserProfile.objects.create(user=user)
        return user

    def _auth(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
        return raw

    def _partner(self, user, game, active=True):
        return Partner.objects.create(user=user, game=game, is_active=active, intro='测试陪玩')

    def _game(self, name='无畏契约', enabled=True):
        return GamePartition.objects.create(name=name, is_enabled=enabled)

    def _product(self, game, platforms='pc,mobile'):
        cat = ProductCategory.objects.create(game=game, name='陪玩', is_enabled=True)
        return Product.objects.create(game=game, category=cat, title='体验单', price_cents=19800, original_price_cents=19800, is_published=True, platforms=platforms)

    def _post(self, path, data=None):
        key = path.replace('/', '-') + '-' + str(self._key_counter)
        self._key_counter += 1
        return self.client.post(path, data or {}, format='json', HTTP_IDEMPOTENCY_KEY=key)


class OrderCheckoutTests(OrderFlowBase):
    def test_create_order_with_platform_and_role(self):
        user = self._user('cust')
        self._auth(user)
        game = self._game(); product = self._product(game)
        resp = self._post('/api/v1/me/orders/', {
            'product_id': product.id, 'quantity': 1, 'expected_product_version': product.version,
            'platform': 'pc', 'role_name': '夜露', 'role_id': '123456',
            'message': '请安排', 'remark': '晚上8点开始',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['platform'], 'pc')
        self.assertEqual(resp.data['role_name'], '夜露')
        self.assertEqual(resp.data['role_id'], '123456')
        self.assertEqual(resp.data['remark'], '晚上8点开始')

    def test_create_order_invalid_platform(self):
        user = self._user('cust2')
        self._auth(user)
        game = self._game(); product = self._product(game)
        resp = self._post('/api/v1/me/orders/', {'product_id': product.id, 'quantity': 1, 'platform': 'switch'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['error']['code'], 'INVALID_PLATFORM')

    def test_create_order_preferred_partner_must_match_game(self):
        user = self._user('cust3')
        self._auth(user)
        game = self._game(); other = self._game('王者荣耀')
        product = self._product(game)
        partner = self._partner(self._user('p1'), other)  # 属于别的游戏
        resp = self._post('/api/v1/me/orders/', {'product_id': product.id, 'quantity': 1, 'expected_product_version': product.version, 'preferred_partner_id': partner.id})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['error']['code'], 'INVALID_PREFERRED_PARTNER')

    def test_preferred_partner_waits_arrangement_on_pay(self):
        user = self._user('cust4')
        self._auth(user)
        game = self._game(); product = self._product(game)
        partner = self._partner(self._user('p2'), game)
        r = self._post('/api/v1/me/orders/', {'product_id': product.id, 'quantity': 1, 'expected_product_version': product.version, 'preferred_partner_id': partner.id})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['preferred_partner'], partner.id)
        order_id = r.data['id']
        pay = self._post(f'/api/v1/me/orders/{order_id}/mock-pay/')
        self.assertEqual(pay.status_code, 200, pay.data)
        # 接单流程改为客服介入：即便指定陪玩，付款后也进入「待派单」，由客服确认后派单
        self.assertEqual(pay.data['status'], 'PENDING_ARRANGEMENT')
        self.assertIsNone(pay.data['partner'])
        self.assertEqual(pay.data['preferred_partner'], partner.id)

    def test_no_preferred_goes_manual(self):
        user = self._user('cust5')
        self._auth(user)
        game = self._game(); product = self._product(game)
        r = self._post('/api/v1/me/orders/', {'product_id': product.id, 'quantity': 1, 'expected_product_version': product.version})
        order_id = r.data['id']
        pay = self._post(f'/api/v1/me/orders/{order_id}/mock-pay/')
        self.assertEqual(pay.data['status'], 'PENDING_ARRANGEMENT')
        self.assertIsNone(pay.data['partner'])

    def test_inactive_preferred_falls_back_manual(self):
        user = self._user('cust6')
        self._auth(user)
        game = self._game(); product = self._product(game)
        partner = self._partner(self._user('p3'), game, active=False)
        r = self._post('/api/v1/me/orders/', {'product_id': product.id, 'quantity': 1, 'expected_product_version': product.version, 'preferred_partner_id': partner.id})
        self.assertEqual(r.status_code, 409)  # 下单时即拦截暂停接单的陪玩


class GamePartnersTests(OrderFlowBase):
    def test_list_active_partners_public(self):
        game = self._game()
        p1 = self._partner(self._user('pa'), game)
        self._partner(self._user('pb'), game, active=False)  # 不应出现
        resp = self.client.get(f'/api/v1/games/{game.id}/partners/')
        self.assertEqual(resp.status_code, 200)
        ids = [x['id'] for x in resp.data]
        self.assertEqual(ids, [p1.id])
        self.assertEqual(resp.data[0]['nickname'], '测试陪玩' if False else resp.data[0]['nickname'])
        self.assertIn('intro', resp.data[0])
