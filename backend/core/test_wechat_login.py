from unittest import mock
from rest_framework.test import APITestCase
from django.test import override_settings
from .models import WechatIdentity, UserProfile
from django.contrib.auth import get_user_model

FAKE_APPID = 'wxtestappid'
FAKE_SECRET = 'test-secret'


@override_settings(WECHAT_APPID=FAKE_APPID, WECHAT_APPSECRET=FAKE_SECRET, DEBUG=True)
class WechatLoginTests(APITestCase):
    def _call(self, code):
        return self.client.post('/api/v1/auth/wechat-login/', {'code': code}, format='json')

    def test_first_login_creates_user_and_identity(self):
        with mock.patch('core.views.code2session', return_value={'openid': 'openid-1', 'session_key': 'sk', 'unionid': ''}) as m:
            response = self._call('code-1')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access_token', response.data)
        User = get_user_model()
        user = User.objects.get(username='wx_' + __import__('hashlib').sha256(b'openid-1').hexdigest()[:20])
        self.assertTrue(WechatIdentity.objects.filter(user=user, appid=FAKE_APPID, openid='openid-1').exists())
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_same_openid_returns_same_user(self):
        with mock.patch('core.views.code2session', return_value={'openid': 'openid-2', 'session_key': 'sk', 'unionid': ''}):
            first = self._call('code-a')
            second = self._call('code-b')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['user']['id'], second.data['user']['id'])
        self.assertEqual(WechatIdentity.objects.filter(openid='openid-2').count(), 1)

    def test_invalid_code_returns_error(self):
        from .wechat import WechatLoginError
        with mock.patch('core.views.code2session', side_effect=WechatLoginError(40029, '登录凭证无效或已过期，请重新登录')):
            response = self._call('bad-code')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'WECHAT_LOGIN_FAILED')
        # 报错文案安全，不泄露 openid/session_key
        self.assertNotIn('openid', str(response.data))

    def test_missing_code(self):
        response = self.client.post('/api/v1/auth/wechat-login/', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'WECHAT_CODE_REQUIRED')

    def test_unconfigured_secret_returns_error(self):
        with override_settings(WECHAT_APPID='', WECHAT_APPSECRET=''):
            response = self._call('code-x')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'WECHAT_LOGIN_FAILED')


class WechatCode2SessionUnitTests(APITestCase):
    @override_settings(WECHAT_APPID=FAKE_APPID, WECHAT_APPSECRET=FAKE_SECRET)
    def test_code2session_success_parse(self):
        from .wechat import code2session
        payload = b'{"openid":"o1","session_key":"sk1","unionid":"u1"}'
        with mock.patch('urllib.request.urlopen') as m:
            m.return_value.__enter__.return_value.read.return_value = payload
            result = code2session('code-1')
        self.assertEqual(result['openid'], 'o1')
        self.assertEqual(result['session_key'], 'sk1')

    @override_settings(WECHAT_APPID=FAKE_APPID, WECHAT_APPSECRET=FAKE_SECRET)
    def test_code2session_errcode(self):
        from .wechat import code2session, WechatLoginError
        payload = b'{"errcode":40029,"errmsg":"invalid code"}'
        with mock.patch('urllib.request.urlopen') as m:
            m.return_value.__enter__.return_value.read.return_value = payload
            with self.assertRaises(WechatLoginError) as cm:
                code2session('bad')
        self.assertEqual(cm.exception.errcode, 40029)
