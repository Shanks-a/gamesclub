from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import AccessToken, UserProfile, GamePartition, Product, ProductCategory, Order, Partner, PartnerApplication


@override_settings(DEBUG=True, ALLOW_MOCK_PAYMENT=True, ALLOW_DEV_LOGIN=True)
class P4Base(APITestCase):
    def _user(self, name):
        User = get_user_model()
        user = User.objects.create_user(username=name)
        UserProfile.objects.create(user=user)
        return user

    def _auth(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
        return raw

    def _post(self, path, data=None):
        """带幂等键的 POST，简化状态流转测试。"""
        key = path.replace('/', '-') + '-' + str(self._key_counter)
        self._key_counter += 1
        return self.client.post(path, data or {}, format='json', HTTP_IDEMPOTENCY_KEY=key)

    _key_counter = 0

    def _make_partner(self, user, game, active=True):
        return Partner.objects.create(user=user, game=game, is_active=active)

    def _game(self, name='王者荣耀'):
        return GamePartition.objects.create(name=name, is_enabled=True)

    def _product(self, game):
        cat = ProductCategory.objects.create(game=game, name='陪玩', is_enabled=True)
        return Product.objects.create(game=game, category=cat, title='上分陪玩', price_cents=2900, original_price_cents=3900, is_published=True)

    def _paid_order(self, user, product, date=None, slot=None):
        from django.utils import timezone
        order = Order.objects.create(
            order_no='GC' + str(Order.objects.count() + 1).zfill(8), user=user, product=product,
            game_name_snapshot=product.game.name, product_title_snapshot=product.title, cover_url_snapshot='',
            unit_price_cents=product.price_cents, total_amount_cents=product.price_cents, quantity=1,
            appointment_date=date, appointment_slot=slot,
            status=Order.Status.PENDING_ARRANGEMENT, payment_status=Order.PaymentStatus.PAID,
        )
        return order


class PartnerApplicationTests(P4Base):
    def test_submit_and_list_application(self):
        user = self._user('alice')
        self._auth(user)
        game = self._game()
        resp = self.client.post('/api/v1/me/partner-application/', {'game': game.id, 'reason': '擅长打野'}, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['status'], 'PENDING')
        # 重复提交同分区待审申请 → 409
        resp2 = self.client.post('/api/v1/me/partner-application/', {'game': game.id, 'reason': '再次'}, format='json')
        self.assertEqual(resp2.status_code, 409)
        # 列表可查
        resp3 = self.client.get('/api/v1/me/partner-application/')
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(len(resp3.data), 1)

    def test_submit_requires_valid_game(self):
        user = self._user('bob')
        self._auth(user)
        resp = self.client.post('/api/v1/me/partner-application/', {'game': 999, 'reason': 'x'}, format='json')
        self.assertEqual(resp.status_code, 404)


class PartnerReviewTests(P4Base):
    def _staff(self, name='admin'):
        User = get_user_model()
        admin = User.objects.create_user(username=name, is_staff=True)
        UserProfile.objects.create(user=admin)
        return admin

    def test_approve_creates_partner(self):
        user = self._user('carol'); game = self._game()
        app = PartnerApplication.objects.create(user=user, game=game, reason='申请')
        admin = self._staff()
        self.client.force_login(admin)
        resp = self.client.post(f'/api/v1/management/partner-applications/{app.id}/approve/', {})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(Partner.objects.filter(user=user, game=game).exists())
        app.refresh_from_db()
        self.assertEqual(app.status, 'APPROVED')

    def test_reject(self):
        user = self._user('dave'); game = self._game()
        app = PartnerApplication.objects.create(user=user, game=game, reason='申请')
        admin = self._staff()
        self.client.force_login(admin)
        resp = self.client.post(f'/api/v1/management/partner-applications/{app.id}/reject/', {})
        self.assertEqual(resp.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'REJECTED')
        self.assertFalse(Partner.objects.filter(user=user).exists())


class PartnerWorkflowTests(P4Base):
    def test_full_workflow_assign_accept_start_complete_confirm(self):
        customer = self._user('customer')
        partner_user = self._user('partner1')
        game = self._game(); product = self._product(game)
        partner = self._make_partner(partner_user, game)
        order = self._paid_order(customer, product, date='2026-10-10', slot='evening')

        # 管理端派单
        admin = self._user('admin'); admin.is_staff = True; admin.save()
        self.client.force_login(admin)
        resp = self.client.post(f'/api/v1/management/orders/{order.id}/assign/', {'partner_id': partner.id}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'PENDING_ACCEPTANCE')
        self.assertEqual(order.partner_id, partner.id)

        # 陪玩接受
        self._auth(partner_user)
        resp = self._post(f'/api/v1/me/partner/orders/{order.id}/accept/')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db(); self.assertEqual(order.status, 'ACCEPTED')

        # 开始服务
        resp = self._post(f'/api/v1/me/partner/orders/{order.id}/start/')
        self.assertEqual(resp.status_code, 200); order.refresh_from_db(); self.assertEqual(order.status, 'IN_SERVICE')

        # 完成服务
        resp = self._post(f'/api/v1/me/partner/orders/{order.id}/complete/')
        self.assertEqual(resp.status_code, 200); order.refresh_from_db(); self.assertEqual(order.status, 'PENDING_CONFIRMATION')

        # 客户验收
        self._auth(customer)
        resp = self._post(f'/api/v1/me/orders/{order.id}/confirm/')
        self.assertEqual(resp.status_code, 200, resp.data); order.refresh_from_db(); self.assertEqual(order.status, 'COMPLETED')

    def test_partner_reject_returns_to_arrangement(self):
        customer = self._user('customer2')
        partner_user = self._user('partner2')
        game = self._game(); product = self._product(game)
        partner = self._make_partner(partner_user, game)
        order = self._paid_order(customer, product, date='2026-10-10', slot='morning')

        admin = self._user('admin2'); admin.is_staff = True; admin.save()
        self.client.force_login(admin)
        self.client.post(f'/api/v1/management/orders/{order.id}/assign/', {'partner_id': partner.id}, format='json')

        self._auth(partner_user)
        resp = self._post(f'/api/v1/me/partner/orders/{order.id}/reject/')
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'PENDING_ARRANGEMENT')
        self.assertIsNone(order.partner)

    def test_conflict_check_blocks_double_booking(self):
        customer = self._user('customer3')
        partner_user = self._user('partner3')
        game = self._game(); product = self._product(game)
        partner = self._make_partner(partner_user, game)
        order1 = self._paid_order(customer, product, date='2026-10-10', slot='evening')
        order2 = self._paid_order(customer, product, date='2026-10-10', slot='evening')

        admin = self._user('admin3'); admin.is_staff = True; admin.save()
        self.client.force_login(admin)
        # 第一单派给 partner 成功
        r1 = self.client.post(f'/api/v1/management/orders/{order1.id}/assign/', {'partner_id': partner.id}, format='json')
        self.assertEqual(r1.status_code, 200)
        # 第二单同时段 → 冲突
        r2 = self.client.post(f'/api/v1/management/orders/{order2.id}/assign/', {'partner_id': partner.id}, format='json')
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r2.data['error']['code'], 'PARTNER_CONFLICT')

    def test_inactive_partner_cannot_be_assigned(self):
        customer = self._user('customer4')
        partner_user = self._user('partner4')
        game = self._game(); product = self._product(game)
        partner = self._make_partner(partner_user, game, active=False)
        order = self._paid_order(customer, product, date='2026-10-10', slot='morning')

        admin = self._user('admin4'); admin.is_staff = True; admin.save()
        self.client.force_login(admin)
        resp = self.client.post(f'/api/v1/management/orders/{order.id}/assign/', {'partner_id': partner.id}, format='json')
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['error']['code'], 'PARTNER_DISABLED')

    def test_non_partner_cannot_access_workbench(self):
        user = self._user('nobody')
        self._auth(user)
        resp = self.client.get('/api/v1/me/partner/orders/')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data['error']['code'], 'NOT_PARTNER')


class OrderCrudTests(P4Base):
    def _staff(self, name='admin'):
        User = get_user_model()
        admin = User.objects.create_user(username=name, is_staff=True)
        UserProfile.objects.create(user=admin)
        return admin

    def test_create_order(self):
        customer = self._user('crud_customer')
        game = self._game(); product = self._product(game)
        admin = self._staff(); self.client.force_login(admin)
        resp = self.client.post('/api/v1/management/orders/create/', {
            'user_id': customer.id, 'product_id': product.id, 'quantity': 2,
            'appointment_date': '2026-10-12', 'appointment_slot': 'morning',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['total_amount_cents'], product.price_cents * 2)
        self.assertEqual(resp.data['status'], 'PENDING_PAYMENT')
        order = Order.objects.get(pk=resp.data['id'])
        self.assertEqual(order.user_id, customer.id)
        self.assertEqual(order.appointment_date.isoformat(), '2026-10-12')

    def test_create_order_with_status_and_payment(self):
        customer = self._user('crud_customer2')
        partner_user = self._user('crud_partner')
        game = self._game(); product = self._product(game)
        partner = self._make_partner(partner_user, game)
        admin = self._staff('admin2'); self.client.force_login(admin)
        resp = self.client.post('/api/v1/management/orders/create/', {
            'user_id': customer.id, 'product_id': product.id, 'quantity': 1,
            'status': 'ACCEPTED', 'payment_status': 'PAID', 'partner_id': partner.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['status'], 'ACCEPTED')
        self.assertEqual(resp.data['payment_status'], 'PAID')
        self.assertEqual(resp.data['partner'], partner.id)

    def test_update_order(self):
        customer = self._user('crud_customer3')
        game = self._game(); product = self._product(game)
        admin = self._staff('admin3'); self.client.force_login(admin)
        order = self._paid_order(customer, product, date='2026-10-10', slot='evening')
        resp = self.client.patch(f'/api/v1/management/orders/{order.id}/edit/', {
            'status': 'COMPLETED', 'quantity': 3,
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.status, 'COMPLETED')
        self.assertEqual(order.quantity, 3)
        self.assertEqual(order.total_amount_cents, product.price_cents * 3)

    def test_delete_order(self):
        customer = self._user('crud_customer4')
        game = self._game(); product = self._product(game)
        admin = self._staff('admin4'); self.client.force_login(admin)
        order = self._paid_order(customer, product, date='2026-10-10', slot='morning')
        from core.models import OrderStatusHistory
        OrderStatusHistory.objects.create(order=order, to_status=order.status, action='X', actor=customer)
        resp = self.client.delete(f'/api/v1/management/orders/{order.id}/delete/')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertFalse(Order.objects.filter(pk=order.id).exists())
        self.assertFalse(OrderStatusHistory.objects.filter(order_id=order.id).exists())

    def test_customers_list_excludes_staff(self):
        customer = self._user('crud_customer5')
        admin = self._staff('admin5'); self.client.force_login(admin)
        resp = self.client.get('/api/v1/management/customers/')
        self.assertEqual(resp.status_code, 200)
        ids = [r['id'] for r in resp.data['results']]
        self.assertIn(customer.id, ids)
        self.assertNotIn(admin.id, ids)

    def test_update_rejects_invalid_status(self):
        customer = self._user('crud_customer6')
        game = self._game(); product = self._product(game)
        admin = self._staff('admin6'); self.client.force_login(admin)
        order = self._paid_order(customer, product)
        resp = self.client.patch(f'/api/v1/management/orders/{order.id}/edit/', {'status': 'BOGUS'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['error']['code'], 'INVALID_STATUS')
