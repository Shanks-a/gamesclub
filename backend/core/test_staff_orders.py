from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APITestCase, APIClient

from .models import (AccessToken, AuditLog, Conversation, GamePartition, Order,
                     OrderStatusHistory, Partner, Product, ProductCategory, UserProfile)


def fixture():
    user_model = get_user_model()
    staff = user_model.objects.create_user('staff', is_staff=True, is_superuser=True)
    customer = user_model.objects.create_user('customer')
    partner_user = user_model.objects.create_user('partner')
    UserProfile.objects.create(user=partner_user, nickname='接单陪玩', avatar_url='/media/avatar.jpg')
    game = GamePartition.objects.create(name='游戏')
    category = ProductCategory.objects.create(game=game, name='陪玩')
    product = Product.objects.create(game=game, category=category, title='商品', price_cents=100, original_price_cents=100)
    partner = Partner.objects.create(user=partner_user, game=game, is_active=True)
    order = Order.objects.create(order_no='STAFF-TEST', user=customer, product=product,
                                 game_name_snapshot=game.name, product_title_snapshot=product.title,
                                 unit_price_cents=100, total_amount_cents=100, quantity=1,
                                 status=Order.Status.PENDING_ARRANGEMENT, payment_status=Order.PaymentStatus.PAID)
    return staff, customer, partner, order


class StaffOrderTests(APITestCase):
    def setUp(self):
        self.staff, self.customer, self.partner, self.order = fixture()
        self.client.force_login(self.staff)

    def action(self, name, **extra):
        return self.client.post(f'/api/v1/management/orders/{self.order.id}/{name}/',
                                {'version': self.order.version, **extra}, format='json')

    def assign(self, **extra):
        return self.action('assign', partner_id=self.partner.id, **extra)

    def token(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)

    def test_full_flow_preserves_customer_acceptance_and_public_partner_fields(self):
        result = self.assign()
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['partner_info'], {'id': self.partner.id, 'nickname': '接单陪玩', 'avatar_url': '/media/avatar.jpg'})
        self.assertNotIn('username', result.data['partner_info'])
        self.assertIsNotNone(result.data['conversation_id'])
        self.assertEqual(Conversation.objects.get(order=self.order).partner_id, self.partner.id)
        self.order.refresh_from_db()
        self.token(self.partner.user)
        self.assertEqual(self.client.post(f'/api/v1/me/partner/orders/{self.order.id}/start/', {'version':self.order.version},format='json',HTTP_IDEMPOTENCY_KEY='start').status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.client.post(f'/api/v1/me/partner/orders/{self.order.id}/complete/', {'version':self.order.version},format='json',HTTP_IDEMPOTENCY_KEY='complete').status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_CONFIRMATION)
        self.assertIsNone(self.order.completed_at)
        self.assertIsNone(self.order.aftersale_deadline)
        self.assertEqual(OrderStatusHistory.objects.filter(order=self.order, actor=self.staff).count(), 1)
        self.assertEqual(AuditLog.objects.filter(resource_id=str(self.order.id)).count(), 3)
        self.token(self.customer)
        response = self.client.post(f'/api/v1/me/orders/{self.order.id}/confirm/', {}, format='json', HTTP_IDEMPOTENCY_KEY='confirm-staff-order')
        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.COMPLETED)
        self.assertIsNotNone(self.order.completed_at)
        self.assertGreater(self.order.aftersale_deadline, self.order.completed_at)

    def test_versions_permissions_and_out_of_order_actions(self):
        self.assertEqual(self.action('start').status_code, 403)
        self.assertEqual(self.action('complete').status_code, 403)
        self.assertEqual(self.assign(version=99).status_code, 409)
        self.assertEqual(self.client.post(f'/api/v1/management/orders/{self.order.id}/assign/', {'partner_id':self.partner.id}).status_code, 400)
        self.client.logout()
        self.token(self.partner.user)
        self.assertEqual(self.assign().status_code, 403)
        self.client.force_login(self.customer)
        self.assertEqual(self.assign().status_code, 403)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_duplicate_assignment_does_not_duplicate_history_or_conversation(self):
        self.assertEqual(self.assign().status_code, 200)
        self.assertEqual(self.assign().status_code, 409)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(OrderStatusHistory.objects.count(), 1)

    def test_different_game_and_disabled_user_are_rejected(self):
        other = GamePartition.objects.create(name='其他游戏')
        self.partner.game = other; self.partner.save()
        result = self.assign()
        self.assertEqual(result.data['error']['code'], 'PARTNER_GAME_MISMATCH')
        self.partner.game = self.order.product.game; self.partner.save()
        profile = self.partner.user.profile; profile.is_enabled = False; profile.save()
        self.assertEqual(self.assign().data['error']['code'], 'PARTNER_DISABLED')
        self.assertFalse(Conversation.objects.exists())

    def test_preferred_partner_remains_intent_and_change_requires_reason(self):
        other_user = get_user_model().objects.create_user('preferred')
        preferred = Partner.objects.create(user=other_user, game=self.order.product.game)
        self.order.preferred_partner = preferred; self.order.save()
        self.assertEqual(self.assign().data['error']['code'], 'CHANGE_REASON_REQUIRED')
        result = self.assign(note='原指定陪玩无空档，客户同意更换')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['preferred_partner'], preferred.id)
        self.assertEqual(result.data['partner'], self.partner.id)
        self.assertEqual(AuditLog.objects.get(action='staff_assign').after['note'], '原指定陪玩无空档，客户同意更换')

    def test_legacy_pending_acceptance_can_be_confirmed_by_staff(self):
        self.order.status = Order.Status.PENDING_ACCEPTANCE
        self.order.partner = self.partner; self.order.save()
        self.assertEqual(self.assign().status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.ACCEPTED)

    def test_existing_conversation_cannot_be_rebound(self):
        other_user = get_user_model().objects.create_user('old-partner')
        other = Partner.objects.create(user=other_user, game=self.order.product.game)
        Conversation.objects.create(order=self.order, user=self.customer, partner=other)
        self.assertEqual(self.assign().data['error']['code'], 'CONVERSATION_CONFLICT')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_ARRANGEMENT)
        self.assertEqual(Conversation.objects.get(order=self.order).partner_id, other.id)

    def test_unpaid_and_unassigned_orders_cannot_progress(self):
        self.order.payment_status = Order.PaymentStatus.UNPAID; self.order.save()
        self.assertEqual(self.assign().data['error']['code'], 'ORDER_UNPAID')
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.status = Order.Status.ACCEPTED; self.order.save()
        self.assertEqual(self.action('start').data['error']['code'], 'PARTNER_MANAGED_SERVICE')

    def test_old_partner_mutations_are_disabled(self):
        self.assertEqual(self.assign().status_code, 200)
        self.token(self.partner.user)
        for action in ('accept', 'reject'):
            response = self.client.post(f'/api/v1/me/partner/orders/{self.order.id}/{action}/', {})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data['error']['code'], 'STAFF_MANAGED_WORKFLOW')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.ACCEPTED)

    def test_admin_edit_and_create_cannot_bypass_fulfilment(self):
        response = self.client.patch(f'/api/v1/management/orders/{self.order.id}/edit/', {'status':'COMPLETED'}, format='json')
        self.assertEqual(response.status_code, 409)
        response = self.client.delete(f'/api/v1/management/orders/{self.order.id}/delete/')
        self.assertEqual(response.status_code, 409)
        response = self.client.post('/api/v1/management/orders/create/', {'user_id':self.customer.id, 'product_id':self.order.product_id, 'status':'COMPLETED','payment_status':'PAID'}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_audit_failure_rolls_back_assignment_and_conversation(self):
        with patch('core.staff_orders.AuditLog.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.assign()
        self.order.refresh_from_db()
        self.assertIsNone(self.order.partner_id)
        self.assertFalse(Conversation.objects.exists())
        self.assertFalse(OrderStatusHistory.objects.exists())

    def test_support_config_permissions_validation_and_public_defaults(self):
        self.assertEqual(self.client.get('/api/v1/support/').data['mode'], 'disabled')
        config = {'mode':'enterprise','corp_id':'wwtest123','url':'https://work.weixin.qq.com/kfid/test123','notice':'服务时间 9:00–22:00'}
        response = self.client.patch('/api/v1/management/support-settings/', config, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.logout()
        self.assertEqual(self.client.get('/api/v1/support/').data, config)
        self.assertEqual(self.client.patch('/api/v1/management/support-settings/',config,format='json').status_code, 403)
        self.staff.is_superuser=False; self.staff.save(); self.client.force_login(self.staff)
        self.assertEqual(self.client.patch('/api/v1/management/support-settings/',config,format='json').status_code, 403)
        self.staff.is_superuser=True; self.staff.save()
        for url in ['javascript:alert(1)','https://evil.test/kfid/test','https://work.weixin.qq.com.evil.test/kfid/test','https://work.weixin.qq.com/kfid/test?redirect=evil']:
            response = self.client.patch('/api/v1/management/support-settings/',{**config,'url':url},format='json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/api/v1/support/').data, config)


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
class StaffOrderConcurrencyTests(TransactionTestCase):
    def test_two_operators_cannot_confirm_the_same_order_twice(self):
        staff, _, partner, order = fixture()
        staff2 = get_user_model().objects.create_user('staff2', is_staff=True)
        # Build independent sessions before parallel requests to avoid session creation races.
        clients = [APIClient(), APIClient()]
        clients[0].force_login(staff); clients[1].force_login(staff2)
        def assign(client):
            close_old_connections()
            try:
                return client.post(f'/api/v1/management/orders/{order.id}/assign/',
                                   {'partner_id':partner.id,'version':order.version},format='json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(assign,clients))
        self.assertEqual(sorted(results),[200,409])
        self.assertEqual(Conversation.objects.count(),1)
        self.assertEqual(OrderStatusHistory.objects.count(),1)
