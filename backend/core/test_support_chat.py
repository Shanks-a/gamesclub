import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from .models import AccessToken, AfterSaleCase, Order, Refund, SupportMessage
from .test_staff_orders import fixture


class SupportChatTests(APITestCase):
    def setUp(self):
        self.staff, self.customer, self.partner, self.order = fixture()
        self.order.partner = self.partner
        self.order.save()
        self.staff.is_superuser = False
        self.staff.save()
        self.staff_client = APIClient()
        self.staff_client.force_login(self.staff)
        self.auth(self.customer)

    def auth(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)

    def open(self, client=None, **data):
        staff = client is not None
        return (client or self.client).post('/api/v1/' + ('management/' if staff else 'me/') + 'support-conversations/', data, format='json')

    def send(self, client, pk, staff, content='请帮我确认接单', key=None):
        return client.post(f'/api/v1/{"management" if staff else "me"}/support-conversations/{pk}/',
                           {'content': content, 'client_key': key or str(uuid.uuid4())}, format='json')

    def test_customer_staff_roundtrip_and_shared_read_reply_status(self):
        pk = self.open(order_no=self.order.order_no).data['id']
        key = str(uuid.uuid4())
        self.assertEqual(self.send(self.client, pk, False, key=key).status_code, 201)
        self.assertEqual(self.send(self.client, pk, False, key=key).status_code, 200)
        self.assertEqual(self.send(self.client, pk, False, content='另一条', key=key).status_code, 409)
        self.assertEqual(SupportMessage.objects.count(), 1)
        url = '/api/v1/management/support-conversations/'
        row = self.staff_client.get(url).data[0]
        self.assertEqual((row['unread_count'], row['reply_state']), (1, 'needs_reply'))
        row = self.staff_client.get(f'{url}{pk}/').data
        self.assertEqual((row['unread_count'], row['reply_state']), (0, 'needs_reply'))
        self.assertEqual(self.send(self.staff_client, pk, True, '已经联系陪玩，请稍候').status_code, 201)
        other_staff = get_user_model().objects.create_user('staff2', is_staff=True)
        self.staff_client.force_login(other_staff)
        self.assertEqual(self.staff_client.get(url).data[0]['reply_state'], 'awaiting_reply')
        row = self.client.get('/api/v1/me/support-conversations/').data[0]
        self.assertEqual((row['unread_count'], row['reply_state']), (1, 'needs_reply'))
        row = self.client.get(f'/api/v1/me/support-conversations/{pk}/').data
        self.assertEqual(row['messages'][-1]['content'], '已经联系陪玩，请稍候')
        self.assertIsNotNone(row['messages'][-1]['read_at'])

    def test_staff_can_contact_both_participants_but_they_cannot_read_each_other(self):
        user_id = self.open(self.staff_client, order_no=self.order.order_no, recipient='customer').data['id']
        partner_id = self.open(self.staff_client, order_no=self.order.order_no, recipient='partner').data['id']
        self.assertNotEqual(user_id, partner_id)
        self.assertEqual(self.client.get(f'/api/v1/me/support-conversations/{partner_id}/').status_code, 404)
        self.auth(self.partner.user)
        self.assertEqual(self.open(order_no=self.order.order_no).data['id'], partner_id)
        self.assertEqual(self.client.get(f'/api/v1/me/support-conversations/{user_id}/').status_code, 404)
        self.assertEqual(self.send(self.client, partner_id, False).status_code, 201)
        self.assertEqual(self.staff_client.get('/api/v1/management/support-conversations/').data[0]['role'], '陪玩')

    def test_unrelated_and_unauthenticated_users_cannot_access_threads(self):
        pk = self.open(order_no=self.order.order_no).data['id']
        self.auth(get_user_model().objects.create_user('stranger'))
        self.assertEqual(self.open(order_no=self.order.order_no).status_code, 404)
        self.assertEqual(self.send(self.client, pk, False).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/management/support-conversations/').status_code, 403)
        self.assertEqual(APIClient().get('/api/v1/me/support-conversations/').status_code, 401)

    def test_general_thread_is_reused_and_invalid_messages_rejected(self):
        pk = self.open().data['id']
        self.assertEqual(self.open(order_no='').data['id'], pk)
        self.assertEqual(self.open().data['id'], pk)
        for content in ['', '  ', 'a' * 2001]:
            self.assertEqual(self.send(self.client, pk, False, content).status_code, 400)
        self.assertEqual(self.send(self.client, pk, False, key='invalid').status_code, 400)
        self.assertEqual(SupportMessage.objects.count(), 0)

    def test_staff_write_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(self.open(client, order_no=self.order.order_no).status_code, 403)


class AftersaleVisibilityTests(APITestCase):
    def setUp(self):
        self.staff, self.customer, self.partner, self.order = fixture()
        self.order.status = Order.Status.IN_SERVICE
        self.order.save()
        raw, _ = AccessToken.issue(self.customer)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
        self.staff_client = APIClient()
        self.staff_client.force_login(self.staff)

    def apply(self, amount=50):
        return self.client.post(f'/api/v1/me/orders/{self.order.id}/aftersale/',
                                {'amount_cents': amount, 'reason': '服务没有达到约定要求'}, format='json',
                                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def summary(self):
        return self.client.get('/api/v1/me/orders/').data[0]['aftersale']

    def review(self, pk, decision):
        return self.staff_client.post(f'/api/v1/management/aftersales/{pk}/review/',
                                     {'decision': decision, 'resolution': '客服处理说明'}, format='json')

    def test_rejected_can_reapply_but_approved_partial_refund_cannot(self):
        case = self.apply().data
        self.assertEqual(self.apply().status_code, 409)
        self.assertEqual(self.summary()['status'], 'OPEN')
        detail = self.staff_client.get(f'/api/v1/management/aftersales/{case["id"]}/').data
        self.assertEqual(detail['reason'], '服务没有达到约定要求')
        self.assertEqual(self.review(case['id'], 'reject').status_code, 200)
        self.assertFalse(self.summary()['reapplication_blocked'])
        case = self.apply().data
        response = self.review(case['id'], 'approve')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.summary()['reapplication_blocked'])
        self.assertEqual(self.apply(amount=10).status_code, 409)
        refund_id = response.data['refunds'][0]['id']
        self.assertEqual(self.staff_client.post(f'/api/v1/management/refunds/{refund_id}/execute/', {'result': 'success'}, format='json').status_code, 200)
        self.assertEqual(self.summary()['refund_status'], 'SUCCEEDED')
        self.assertEqual(self.summary()['status'], 'CLOSED')
        self.assertEqual(self.apply(amount=10).status_code, 409)
        self.order.refresh_from_db()
        self.assertEqual(self.order.refunded_amount_cents, 50)

    def test_failed_or_unknown_refunds_still_block_new_applications(self):
        for result in ['fail', 'unknown']:
            with self.subTest(result=result):
                case = AfterSaleCase.objects.create(order=self.order, user=self.customer, case_no=result, amount_cents=30)
                response = self.review(case.id, 'approve')
                refund_id = response.data['refunds'][0]['id']
                self.staff_client.post(f'/api/v1/management/refunds/{refund_id}/execute/', {'result': result}, format='json')
                self.assertTrue(self.summary()['reapplication_blocked'])
                self.assertEqual(self.apply(amount=10).status_code, 409)

    def test_rejected_application_does_not_extend_deadline(self):
        case = self.apply().data
        self.review(case['id'], 'reject')
        self.order.status = Order.Status.COMPLETED
        self.order.aftersale_deadline = timezone.now() - timedelta(hours=1)
        self.order.save()
        self.assertEqual(self.apply().data['error']['code'], 'AFTERSALE_WINDOW_CLOSED')

    def test_approved_but_failed_refund_cannot_settle(self):
        case = self.apply().data
        response = self.review(case['id'], 'approve')
        refund_id = response.data['refunds'][0]['id']
        self.staff_client.post(f'/api/v1/management/refunds/{refund_id}/execute/', {'result': 'fail'}, format='json')
        self.order.refresh_from_db()
        self.order.status = Order.Status.COMPLETED
        self.order.partner = self.partner
        self.order.aftersale_deadline = timezone.now() - timedelta(hours=1)
        self.order.save()
        response = self.staff_client.post('/api/v1/management/settlements/', {'order_ids': [self.order.id]}, format='json')
        self.assertEqual(response.data['settled'], [])
        self.assertEqual(response.data['errors'][0]['code'], 'SETTLEMENT_NOT_READY')
