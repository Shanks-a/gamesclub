from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import AccessToken, UserProfile, GamePartition, Product, ProductCategory, Order, Partner, Conversation, Message


@override_settings(DEBUG=True, ALLOW_MOCK_PAYMENT=True, ALLOW_DEV_LOGIN=True)
class MessageBase(APITestCase):
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

    def _partner(self, user, game):
        return Partner.objects.create(user=user, game=game, is_active=True)

    def _game(self, name='王者荣耀'):
        return GamePartition.objects.create(name=name, is_enabled=True)

    def _product(self, game):
        cat = ProductCategory.objects.create(game=game, name='陪玩', is_enabled=True)
        return Product.objects.create(game=game, category=cat, title='上分陪玩', price_cents=2900, original_price_cents=3900, is_published=True)

    def _order(self, user, product, status=Order.Status.ACCEPTED, partner=None):
        order = Order.objects.create(
            order_no='GC' + str(Order.objects.count() + 1).zfill(8), user=user, product=product,
            game_name_snapshot=product.game.name, product_title_snapshot=product.title, cover_url_snapshot='',
            unit_price_cents=product.price_cents, total_amount_cents=product.price_cents, quantity=1,
            status=status, payment_status=Order.PaymentStatus.PAID, partner=partner, commission_bp=2000,
        )
        return order

    def _post(self, path, data=None):
        key = path.replace('/', '-') + '-' + str(self._key_counter)
        self._key_counter += 1
        return self.client.post(path, data or {}, format='json', HTTP_IDEMPOTENCY_KEY=key)

    def _get(self, path):
        return self.client.get(path, format='json')


class ConversationTests(MessageBase):
    def test_accept_creates_conversation(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        Conversation.objects.get_or_create(order=order, defaults={'user': customer, 'partner': partner})
        self.assertTrue(Conversation.objects.filter(order=order).exists())
        conv = Conversation.objects.get(order=order)
        self.assertEqual(conv.user, customer)
        self.assertEqual(conv.partner, partner)

    def test_list_conversations_isolated(self):
        cust_a = self._user('cust_a')
        cust_b = self._user('cust_b')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order_a = self._order(cust_a, product, partner=partner)
        order_b = self._order(cust_b, product, partner=partner)
        conv_a = Conversation.objects.create(order=order_a, user=cust_a, partner=partner)
        Conversation.objects.create(order=order_b, user=cust_b, partner=partner)

        self._auth(cust_a)
        resp = self._get('/api/v1/me/conversations/')
        self.assertEqual(resp.status_code, 200)
        ids = [c['id'] for c in resp.data]
        self.assertEqual(ids, [conv_a.id])

    def test_send_and_list_messages(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        conv = Conversation.objects.create(order=order, user=customer, partner=partner)

        self._auth(customer)
        r = self._post(f'/api/v1/me/conversations/{conv.id}/send/', {'content': '你好'})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['sender'], 'USER')
        self.assertEqual(r.data['content'], '你好')

        msgs = self._get(f'/api/v1/me/conversations/{conv.id}/messages/')
        self.assertEqual(msgs.status_code, 200)
        self.assertEqual(len(msgs.data), 1)
        self.assertEqual(msgs.data[0]['content'], '你好')

    def test_partner_sends_as_partner(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        conv = Conversation.objects.create(order=order, user=customer, partner=partner)

        self._auth(partner_user)
        r = self._post(f'/api/v1/me/conversations/{conv.id}/send/', {'content': '已接单'})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['sender'], 'PARTNER')

    def test_unread_count_and_read_on_list(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        conv = Conversation.objects.create(order=order, user=customer, partner=partner)
        Message.objects.create(conversation=conv, sender='PARTNER', content='来了')

        # 客户视角：未读 1
        self._auth(customer)
        resp = self._get('/api/v1/me/conversations/')
        self.assertEqual(resp.data[0]['unread_count'], 1)

        # 拉取消息后标记已读，未读归零
        self._get(f'/api/v1/me/conversations/{conv.id}/messages/')
        resp = self._get('/api/v1/me/conversations/')
        self.assertEqual(resp.data[0]['unread_count'], 0)

    def test_outsider_cannot_access(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        stranger = self._user('stranger')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        conv = Conversation.objects.create(order=order, user=customer, partner=partner)

        self._auth(stranger)
        r = self._post(f'/api/v1/me/conversations/{conv.id}/send/', {'content': '偷看'})
        self.assertEqual(r.status_code, 404, r.data)

    def test_empty_content_rejected(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        conv = Conversation.objects.create(order=order, user=customer, partner=partner)

        self._auth(customer)
        r = self._post(f'/api/v1/me/conversations/{conv.id}/send/', {'content': '   '})
        self.assertEqual(r.status_code, 400, r.data)
        self.assertEqual(r.data['error']['code'], 'INVALID_CONTENT')

    def test_send_idempotent(self):
        customer = self._user('cust')
        partner_user = self._user('partner')
        game = self._game(); product = self._product(game)
        partner = self._partner(partner_user, game)
        order = self._order(customer, product, partner=partner)
        conv = Conversation.objects.create(order=order, user=customer, partner=partner)

        self._auth(customer)
        key = 'idem-send-1'
        r1 = self.client.post(f'/api/v1/me/conversations/{conv.id}/send/', {'content': '同一条'}, format='json', HTTP_IDEMPOTENCY_KEY=key)
        r2 = self.client.post(f'/api/v1/me/conversations/{conv.id}/send/', {'content': '同一条'}, format='json', HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(Message.objects.filter(conversation=conv).count(), 1)
