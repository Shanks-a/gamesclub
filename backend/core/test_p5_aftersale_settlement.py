from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import AccessToken, UserProfile, GamePartition, Product, ProductCategory, Order, Partner, Review, AfterSaleCase, Refund, SystemConfig, Settlement, SettlementItem


@override_settings(DEBUG=True, ALLOW_MOCK_PAYMENT=True, ALLOW_DEV_LOGIN=True)
class P5Base(APITestCase):
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
        key = path.replace('/', '-') + '-' + str(self._key_counter)
        self._key_counter += 1
        return self.client.post(path, data or {}, format='json', HTTP_IDEMPOTENCY_KEY=key)

    _key_counter = 0

    def _game(self, name='王者荣耀'):
        return GamePartition.objects.create(name=name, is_enabled=True)

    def _product(self, game):
        cat = ProductCategory.objects.create(game=game, name='陪玩', is_enabled=True)
        return Product.objects.create(game=game, category=cat, title='上分陪玩', price_cents=2900, original_price_cents=3900, is_published=True)

    def _order(self, user, product, status, payment_status=Order.PaymentStatus.PAID):
        order = Order.objects.create(
            order_no='GC' + str(Order.objects.count() + 1).zfill(8), user=user, product=product,
            game_name_snapshot=product.game.name, product_title_snapshot=product.title, cover_url_snapshot='',
            unit_price_cents=product.price_cents, total_amount_cents=product.price_cents, quantity=1,
            status=status, payment_status=payment_status,
            commission_bp=2000,
        )
        if status == Order.Status.COMPLETED:
            order.completed_at = timezone.now()
            order.save(update_fields=['completed_at'])
        return order


class ReviewTests(P5Base):
    def test_review_after_complete(self):
        user = self._user('alice')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.COMPLETED)
        resp = self._post(f'/api/v1/me/orders/{order.id}/review/', {'rating': 5, 'content': '很棒'})
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['rating'], 5)
        self.assertEqual(resp.data['content'], '很棒')

    def test_review_twice_conflict(self):
        user = self._user('bob')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.COMPLETED)
        r1 = self._post(f'/api/v1/me/orders/{order.id}/review/', {'rating': 4, 'content': '不错'})
        self.assertEqual(r1.status_code, 201)
        r2 = self._post(f'/api/v1/me/orders/{order.id}/review/', {'rating': 3, 'content': '再次'})
        self.assertEqual(r2.status_code, 409, r2.data)
        self.assertEqual(r2.data['error']['code'], 'REVIEW_EXISTS')

    def test_review_requires_completed(self):
        user = self._user('carol')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.PENDING_PAYMENT, Order.PaymentStatus.UNPAID)
        resp = self._post(f'/api/v1/me/orders/{order.id}/review/', {'rating': 5})
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data['error']['code'], 'ORDER_STATE_CONFLICT')

    def test_review_rating_range(self):
        user = self._user('dave')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.COMPLETED)
        resp = self._post(f'/api/v1/me/orders/{order.id}/review/', {'rating': 9})
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertEqual(resp.data['error']['code'], 'INVALID_RATING')

    def test_get_review(self):
        user = self._user('eve')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.COMPLETED)
        Review.objects.create(order=order, user=user, rating=5, content='好')
        resp = self.client.get(f'/api/v1/me/orders/{order.id}/review/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['rating'], 5)

    def test_review_idempotent_replay(self):
        user = self._user('frank')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.COMPLETED)
        path = f'/api/v1/me/orders/{order.id}/review/'
        key = 'review-key-1'
        r1 = self.client.post(path, {'rating': 5, 'content': 'a'}, format='json', HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post(path, {'rating': 5, 'content': 'a'}, format='json', HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(Review.objects.filter(order=order).count(), 1)


class AftersaleTests(P5Base):
    def _completed_order(self, user, product, hours_ago=1):
        order = self._order(user, product, Order.Status.COMPLETED)
        order.completed_at = timezone.now() - timezone.timedelta(hours=hours_ago)
        order.aftersale_deadline = order.completed_at + timezone.timedelta(hours=48)
        order.save(update_fields=['completed_at', 'aftersale_deadline'])
        return order

    def _staff(self, name='admin'):
        User = get_user_model()
        admin = User.objects.create_user(username=name, is_staff=True)
        return admin

    def _staff_auth(self):
        """用管理端 session 登录。"""
        admin = self._staff()
        self.client.force_login(admin)
        return admin

    def test_apply_aftersale_in_service(self):
        user = self._user('alice')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.IN_SERVICE)
        resp = self._post(f'/api/v1/me/orders/{order.id}/aftersale/', {'amount_cents': 1000, 'reason': '服务不满意'})
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['status'], 'OPEN')
        self.assertEqual(AfterSaleCase.objects.filter(order=order).count(), 1)

    def test_apply_aftersale_after_deadline_rejected(self):
        user = self._user('bob')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._completed_order(user, product, hours_ago=100)  # 超过 48h 截止
        resp = self._post(f'/api/v1/me/orders/{order.id}/aftersale/', {'amount_cents': 1000})
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data['error']['code'], 'AFTERSALE_WINDOW_CLOSED')

    def test_apply_aftersale_amount_exceeded(self):
        user = self._user('carol')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.IN_SERVICE)  # total 2900
        resp = self._post(f'/api/v1/me/orders/{order.id}/aftersale/', {'amount_cents': 9999})
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data['error']['code'], 'REFUND_AMOUNT_EXCEEDED')

    def test_apply_aftersale_duplicate_open(self):
        user = self._user('dave')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.IN_SERVICE)
        r1 = self._post(f'/api/v1/me/orders/{order.id}/aftersale/', {'amount_cents': 500})
        self.assertEqual(r1.status_code, 201)
        r2 = self._post(f'/api/v1/me/orders/{order.id}/aftersale/', {'amount_cents': 500})
        self.assertEqual(r2.status_code, 409, r2.data)
        self.assertEqual(r2.data['error']['code'], 'AFTERSALE_EXISTS')

    def test_apply_aftersale_unpaid_rejected(self):
        user = self._user('eve')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.PENDING_PAYMENT, Order.PaymentStatus.UNPAID)
        resp = self._post(f'/api/v1/me/orders/{order.id}/aftersale/', {'amount_cents': 500})
        self.assertEqual(resp.status_code, 409, resp.data)

    def test_review_approve_creates_pending_refund(self):
        user = self._user('frank')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.IN_SERVICE)
        case = AfterSaleCase.objects.create(order=order, user=user, case_no='AS1', amount_cents=1000)
        self._staff_auth()
        resp = self.client.post(f'/api/v1/management/aftersales/{case.id}/review/', {'decision': 'approve', 'resolution': '同意退款'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.reserved_refund_cents, 1000)
        self.assertTrue(Refund.objects.filter(order=order, status=Refund.Status.PENDING).exists())

    def test_refund_success(self):
        user = self._user('grace')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.IN_SERVICE)
        case = AfterSaleCase.objects.create(order=order, user=user, case_no='AS2', amount_cents=1000, status=AfterSaleCase.Status.APPROVED)
        refund = Refund.objects.create(order=order, case=case, refund_no='RF1', amount_cents=1000)
        order.reserved_refund_cents = 1000; order.save(update_fields=['reserved_refund_cents'])
        self._staff_auth()
        resp = self.client.post(f'/api/v1/management/refunds/{refund.id}/execute/', {'result': 'success'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.refunded_amount_cents, 1000)
        self.assertEqual(order.reserved_refund_cents, 0)
        case.refresh_from_db()
        self.assertEqual(case.status, AfterSaleCase.Status.CLOSED)

    def test_refund_fail_releases_reserve(self):
        user = self._user('henry')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.IN_SERVICE)
        refund = Refund.objects.create(order=order, refund_no='RF2', amount_cents=1000)
        order.reserved_refund_cents = 1000; order.save(update_fields=['reserved_refund_cents'])
        self._staff_auth()
        resp = self.client.post(f'/api/v1/management/refunds/{refund.id}/execute/', {'result': 'fail'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.refunded_amount_cents, 0)
        self.assertEqual(order.reserved_refund_cents, 0)

    def test_cancel_refund_full(self):
        user = self._user('ivy')
        self._auth(user)
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.PENDING_ARRANGEMENT)
        self._staff_auth()
        resp = self.client.post(f'/api/v1/management/orders/{order.id}/cancel-refund/', {}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(order.refunded_amount_cents, order.total_amount_cents)

    def test_settings_read_write(self):
        self._staff_auth()
        resp = self.client.get('/api/v1/management/settings/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['commission_bp'], 2000)

    def test_settings_write_requires_superuser(self):
        admin = self._staff()
        self.client.force_login(admin)
        resp = self.client.patch('/api/v1/management/settings/', {'commission_bp': 3000}, format='json')
        self.assertEqual(resp.status_code, 403)


class SettlementTests(P5Base):
    def _staff(self, name='admin'):
        User = get_user_model()
        admin = User.objects.create_user(username=name, is_staff=True)
        return admin

    def _staff_auth(self):
        admin = self._staff()
        self.client.force_login(admin)
        return admin

    def _settle_ready_order(self, user, product):
        """造一个可结算的已完成订单：有 partner、已过售后截止。"""
        partner_user = self._user('partner')
        partner = Partner.objects.create(user=partner_user, game=product.game, is_active=True)
        order = self._order(user, product, Order.Status.COMPLETED)
        order.partner = partner
        order.completed_at = timezone.now() - timezone.timedelta(hours=50)
        order.aftersale_deadline = order.completed_at + timezone.timedelta(hours=48)
        order.save(update_fields=['partner', 'completed_at', 'aftersale_deadline'])
        return order

    def test_settle_basic(self):
        user = self._user('alice')
        game = self._game(); product = self._product(game)  # total 2900
        order = self._settle_ready_order(user, product)
        self._staff_auth()
        resp = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data['settled']), 1)
        item = SettlementItem.objects.get(order=order)
        # net = 2900, commission_bp=2000 → commission = round(2900*0.2)=580, partner_income=2320
        self.assertEqual(item.net_income_cents, 2900)
        self.assertEqual(item.commission_cents, 580)
        self.assertEqual(item.partner_income_cents, 2320)

    def test_settle_twice_conflict(self):
        user = self._user('bob')
        game = self._game(); product = self._product(game)
        order = self._settle_ready_order(user, product)
        self._staff_auth()
        r1 = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(len(r1.data['settled']), 1)
        r2 = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(len(r2.data['settled']), 0)
        self.assertEqual(r2.data['errors'][0]['code'], 'ALREADY_SETTLED')

    def test_settle_partial_refund_recalc(self):
        user = self._user('carol')
        game = self._game(); product = self._product(game)
        order = self._settle_ready_order(user, product)
        order.refunded_amount_cents = 1000
        order.save(update_fields=['refunded_amount_cents'])
        self._staff_auth()
        resp = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(resp.status_code, 200)
        item = SettlementItem.objects.get(order=order)
        # net = 2900 - 1000 = 1900, commission = round(1900*0.2)=380, partner = 1520
        self.assertEqual(item.net_income_cents, 1900)
        self.assertEqual(item.commission_cents, 380)
        self.assertEqual(item.partner_income_cents, 1520)

    def test_settle_full_refund_zero_income(self):
        user = self._user('dave')
        game = self._game(); product = self._product(game)
        order = self._settle_ready_order(user, product)
        order.refunded_amount_cents = order.total_amount_cents
        order.save(update_fields=['refunded_amount_cents'])
        self._staff_auth()
        resp = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(resp.status_code, 200)
        item = SettlementItem.objects.get(order=order)
        self.assertEqual(item.net_income_cents, 0)
        self.assertEqual(item.partner_income_cents, 0)

    def test_settle_rounding(self):
        # 构造 net=2, commission_bp=2500 → 2*0.25=0.5 分，四舍五入到 1 分
        user = self._user('eve')
        game = self._game(); product = self._product(game)
        partner_user = self._user('partner2')
        partner = Partner.objects.create(user=partner_user, game=product.game, is_active=True)
        order = self._order(user, product, Order.Status.COMPLETED)
        order.partner = partner
        order.total_amount_cents = 2
        order.commission_bp = 2500
        order.completed_at = timezone.now() - timezone.timedelta(hours=50)
        order.aftersale_deadline = order.completed_at + timezone.timedelta(hours=48)
        order.save(update_fields=['partner', 'total_amount_cents', 'commission_bp', 'completed_at', 'aftersale_deadline'])
        self._staff_auth()
        self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        item = SettlementItem.objects.get(order=order)
        self.assertEqual(item.commission_cents, 1)
        self.assertEqual(item.partner_income_cents, 1)

    def test_settle_not_ready_open_aftersale(self):
        user = self._user('frank')
        game = self._game(); product = self._product(game)
        order = self._settle_ready_order(user, product)
        AfterSaleCase.objects.create(order=order, user=user, case_no='ASX', amount_cents=100, status=AfterSaleCase.Status.OPEN)
        self._staff_auth()
        resp = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(len(resp.data['settled']), 0)
        self.assertEqual(resp.data['errors'][0]['code'], 'SETTLEMENT_NOT_READY')

    def test_settle_not_ready_pending_refund(self):
        user = self._user('grace')
        game = self._game(); product = self._product(game)
        order = self._settle_ready_order(user, product)
        Refund.objects.create(order=order, refund_no='RFX', amount_cents=100, status=Refund.Status.UNKNOWN)
        self._staff_auth()
        resp = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(len(resp.data['settled']), 0)
        self.assertEqual(resp.data['errors'][0]['code'], 'SETTLEMENT_NOT_READY')

    def test_settle_requires_partner(self):
        user = self._user('henry')
        game = self._game(); product = self._product(game)
        order = self._order(user, product, Order.Status.COMPLETED)
        order.completed_at = timezone.now() - timezone.timedelta(hours=50)
        order.aftersale_deadline = order.completed_at + timezone.timedelta(hours=48)
        order.save(update_fields=['completed_at', 'aftersale_deadline'])
        self._staff_auth()
        resp = self.client.post('/api/v1/management/settlements/', {'order_ids': [order.id]}, format='json')
        self.assertEqual(len(resp.data['settled']), 0)
        self.assertEqual(resp.data['errors'][0]['code'], 'NO_PARTNER')


