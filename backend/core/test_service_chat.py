from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APITestCase, APIClient

from .models import AccessToken, Conversation, Message, Order, OrderStatusHistory
from .test_staff_orders import fixture


class ServiceChatTests(APITestCase):
    def setUp(self):
        self.staff, self.customer, self.partner, self.order = fixture()
        self.client.force_login(self.staff)
        response = self.client.post(f'/api/v1/management/orders/{self.order.id}/assign/',
                                    {'partner_id':self.partner.id, 'version':1}, format='json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.conv = Conversation.objects.get(order=self.order)
        self.auth(self.partner.user)

    def auth(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)

    def action(self, name, key=None, version=None):
        self.order.refresh_from_db()
        return self.client.post(f'/api/v1/me/partner/orders/{self.order.id}/{name}/',
                                {'version': self.order.version if version is None else version},
                                format='json', HTTP_IDEMPOTENCY_KEY=key or name)

    def board(self):
        response = self.client.get(f'/api/v1/games/{self.partner.game_id}/leaderboard/')
        self.assertEqual(response.status_code, 200)
        return response.data['results'][0]

    def test_complete_requires_customer_consent_and_counts_once(self):
        self.assertEqual(self.board()['completed_orders'], 0)
        self.assertEqual(self.action('start').status_code, 200)
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.started_at)
        self.assertIsNone(self.order.completed_at)
        self.assertEqual(self.action('complete').status_code, 200)
        self.order.refresh_from_db()
        self.assertGreaterEqual(self.order.completion_requested_at, self.order.started_at)
        self.assertIsNone(self.order.aftersale_deadline)
        self.assertEqual(self.board()['recent_orders'], 0)
        url = f'/api/v1/me/orders/{self.order.id}/confirm/'
        self.assertEqual(self.client.post(url, {}, HTTP_IDEMPOTENCY_KEY='wrong-person').status_code, 404)
        self.auth(self.customer)
        detail = self.client.get(f'/api/v1/me/conversations/{self.conv.id}/').data
        self.assertEqual(detail['viewer_role'], 'USER')
        self.assertEqual(detail['service']['status'], 'PENDING_CONFIRMATION')
        self.assertEqual([m['kind'] for m in detail['messages']], ['SERVICE_STARTED','COMPLETION_REQUEST'])
        for _ in range(2):
            response = self.client.post(url, {'version':self.order.version}, format='json', HTTP_IDEMPOTENCY_KEY='confirm')
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.board()['recent_orders'], 1)
        self.assertEqual(self.board()['completed_orders'], 1)
        self.assertEqual(Message.objects.filter(kind='COMPLETION_CONFIRMED').count(), 1)
        self.assertEqual(OrderStatusHistory.objects.filter(action='CONFIRM').count(), 1)
        self.order.refresh_from_db()
        self.assertGreaterEqual(self.order.completed_at, self.order.completion_requested_at)

    def test_retry_and_stale_requests_do_not_duplicate_events(self):
        self.assertEqual(self.action('start', version=2).status_code, 200)
        self.assertEqual(self.action('start', version=2).status_code, 200)
        self.assertEqual(self.action('start', key='another', version=2).status_code, 409)
        self.assertEqual(self.action('start', key='third').status_code, 409)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(self.action('complete', version=3).status_code, 200)
        self.assertEqual(self.action('complete', version=3).status_code, 200)
        self.assertEqual(Message.objects.count(), 2)

    def test_permissions_order_and_conversation_isolation(self):
        self.assertEqual(self.action('complete').status_code, 409)
        for user in (self.customer, self.staff, get_user_model().objects.create_user('outsider')):
            self.auth(user)
            self.assertEqual(self.action('start', key=str(user.pk)).status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/me/conversations/{self.conv.id}/').status_code, 404)
        self.assertEqual(Message.objects.count(), 0)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ACCEPTED')

    def test_failure_to_write_event_rolls_back_progress(self):
        with patch('core.service_orders.Message.objects.create', side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError):
                self.action('start')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ACCEPTED')
        self.assertIsNone(self.order.started_at)
        self.assertEqual(self.order.version, 2)

    def test_text_cannot_forge_service_events(self):
        url = f'/api/v1/me/conversations/{self.conv.id}/send/'
        forged = self.client.post(url, {'content':'done', 'kind':'COMPLETION_REQUEST'}, HTTP_IDEMPOTENCY_KEY='forged')
        self.assertEqual(forged.status_code, 400)
        result = self.client.post(url, {'content':'服务完成申请'}, HTTP_IDEMPOTENCY_KEY='text')
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data['kind'], 'TEXT')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ACCEPTED')

    def test_stale_confirmation_and_old_staff_actions_rejected(self):
        self.action('start'); self.action('complete')
        self.auth(self.customer)
        self.assertEqual(self.client.post(f'/api/v1/me/orders/{self.order.id}/confirm/', {'version':1},
                                         HTTP_IDEMPOTENCY_KEY='stale').status_code, 409)
        for action in ('start', 'complete'):
            self.assertEqual(self.client.post(f'/api/v1/management/orders/{self.order.id}/{action}/', {'version':4}).status_code, 403)

    def test_product_platform_is_checked_by_server(self):
        self.auth(self.customer)
        product = self.order.product
        for platforms, selected, expected in [('mobile','pc',400),('pc','mobile',400),('pc','pc',201),('mobile,pc','pc',201),('mobile','mobile',201)]:
            product.platforms = platforms; product.save()
            payload = {'product_id': product.pk, 'quantity':1, 'expected_product_version':product.version, 'platform':selected}
            result = self.client.post('/api/v1/me/orders/', payload, format='json', HTTP_IDEMPOTENCY_KEY=platforms+selected)
            self.assertEqual(result.status_code, expected, result.data)

    def test_recent_ranking_excludes_older_completions(self):
        from datetime import timedelta
        from django.utils import timezone
        self.order.status = 'COMPLETED'; self.order.completed_at = timezone.now()-timedelta(days=31)
        self.order.save()
        self.assertEqual(self.board()['recent_orders'], 0)
        self.assertEqual(self.board()['completed_orders'], 1)

    def test_historical_service_times_come_from_history_without_completing_order(self):
        import importlib
        from django.apps import apps
        self.action('start'); self.action('complete')
        self.order.refresh_from_db()
        Order.objects.filter(pk=self.order.pk).update(started_at=None, completion_requested_at=None)
        migration = importlib.import_module('core.migrations.0014_service_chat_progress')
        with connection.schema_editor() as editor:
            migration.backfill_service_times(apps, editor)
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.started_at)
        self.assertIsNotNone(self.order.completion_requested_at)
        self.assertEqual(self.order.status, 'PENDING_CONFIRMATION')
        self.assertIsNone(self.order.completed_at)


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
class ServiceConcurrencyTests(TransactionTestCase):
    def test_concurrent_completion_creates_one_request(self):
        _, customer, partner, order = fixture()
        order.partner=partner; order.status='IN_SERVICE'; order.save()
        Conversation.objects.create(order=order, user=customer, partner=partner)
        raw, _ = AccessToken.issue(partner.user)
        def complete(key):
            close_old_connections()
            try:
                client=APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
                return client.post(f'/api/v1/me/partner/orders/{order.id}/complete/', {'version':1},
                                   format='json', HTTP_IDEMPOTENCY_KEY=key).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(complete, ['one','two']))
        self.assertEqual(sorted(results), [200,409])
        self.assertEqual(Message.objects.filter(kind='COMPLETION_REQUEST').count(), 1)
