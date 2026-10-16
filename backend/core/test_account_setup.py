from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import AccessToken, GamePartition, Partner, UserProfile, WechatIdentity
from .test_accounts import ACCOUNTS, GROUP_NAME


@override_settings(DEBUG=True, ALLOW_DEV_LOGIN=True)
class TestAccountSetupTests(APITestCase):
    def setUp(self):
        self.game = GamePartition.objects.create(name='王者荣耀')

    def setup_accounts(self):
        output = StringIO()
        call_command('setup_test_accounts', game_id=self.game.pk, stdout=output)
        return output.getvalue()

    def test_seven_accounts_roles_and_repeat_preserves_passwords(self):
        output = self.setup_accounts()
        users = get_user_model().objects.filter(groups__name=GROUP_NAME)
        self.assertEqual(users.count(), 7)
        self.assertEqual(users.filter(is_staff=True, is_superuser=False).count(), 2)
        self.assertEqual(Partner.objects.count(), 2)
        before = list(users.order_by('pk').values('id', 'username', 'password'))
        self.assertEqual(output.count('password='), 2)
        self.assertNotIn('password=', self.setup_accounts())
        self.assertEqual(before, list(users.order_by('pk').values('id', 'username', 'password')))

    def test_legacy_ids_and_real_wechat_are_preserved(self):
        old = get_user_model().objects.create_user(username='dev-player')
        partner = Partner.objects.create(user=old, game=self.game)
        real = get_user_model().objects.create_user(username='wx-owner')
        profile = UserProfile.objects.create(user=real, nickname='风中闻笛')
        identity = WechatIdentity.objects.create(user=real, appid='wx-test', openid='owner')
        self.setup_accounts()
        old.refresh_from_db(); partner.refresh_from_db(); profile.refresh_from_db(); identity.refresh_from_db()
        self.assertEqual(old.username, 'test-partner-01')
        self.assertEqual(partner.user_id, old.pk)
        self.assertEqual(profile.nickname, '风中闻笛')
        self.assertEqual(identity.user_id, real.pk)
        self.assertFalse(real.groups.filter(name=GROUP_NAME).exists())

    def test_wechat_collision_rolls_back_entire_setup(self):
        user = get_user_model().objects.create_user(username='dev-player')
        WechatIdentity.objects.create(user=user, appid='wx-test', openid='protected')
        with self.assertRaises(CommandError):
            self.setup_accounts()
        self.assertEqual(get_user_model().objects.count(), 1)
        user.refresh_from_db()
        self.assertEqual(user.username, 'dev-player')

    def test_dev_login_allows_only_five_fixed_accounts(self):
        self.setup_accounts()
        response = self.client.get('/api/v1/auth/dev-accounts/')
        self.assertEqual(len(response.data['accounts']), 5)
        for name, _, role, _ in ACCOUNTS:
            response = self.client.post('/api/v1/auth/dev-login/', {'username': name})
            self.assertEqual(response.status_code, 403 if role == 'staff' else 200)
        real = get_user_model().objects.create_user(username='wx-owner')
        UserProfile.objects.create(user=real)
        self.assertEqual(self.client.post('/api/v1/auth/dev-login/', {'username': real.username}).status_code, 403)
        default = self.client.post('/api/v1/auth/dev-login/', {})
        self.assertEqual(default.data['user']['nickname'], '测试用户01')

    def test_disabled_or_wechat_bound_test_identity_is_rejected(self):
        self.setup_accounts()
        user = get_user_model().objects.get(username='test-user-01')
        user.profile.is_enabled = False
        user.profile.save()
        self.assertEqual(self.client.post('/api/v1/auth/dev-login/', {}).status_code, 403)
        user.profile.is_enabled = True
        user.profile.save()
        WechatIdentity.objects.create(user=user, appid='wx-test', openid='protected')
        self.assertEqual(self.client.post('/api/v1/auth/dev-login/', {}).status_code, 403)
        self.assertEqual(AccessToken.objects.count(), 0)

    def test_staff_password_login_and_configuration_permissions(self):
        output = self.setup_accounts()
        password = next(line.split('password=')[1] for line in output.splitlines() if 'test-staff-01' in line)
        response = self.client.post('/api/v1/management/login/', {'username': 'test-staff-01', 'password': password})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/management/orders/').status_code, 200)
        self.assertEqual(self.client.patch('/api/v1/management/support-settings/', {'mode': 'disabled'}, format='json').status_code, 403)

    def test_production_exposes_no_test_accounts_or_login(self):
        self.setup_accounts()
        for config in ({'DEBUG': False}, {'ALLOW_DEV_LOGIN': False}):
            with self.subTest(config=config), override_settings(**config):
                self.assertEqual(self.client.get('/api/v1/auth/dev-accounts/').data['accounts'], [])
                self.assertEqual(self.client.get('/api/v1/management/session/').data['test_accounts'], [])
                self.assertEqual(self.client.post('/api/v1/auth/dev-login/', {}).status_code, 403)
                with self.assertRaises(CommandError):
                    self.setup_accounts()
