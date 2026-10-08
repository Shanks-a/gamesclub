from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import AccessToken, UserProfile


class MeProfileTests(APITestCase):
    def _auth(self, user):
        raw, _ = AccessToken.issue(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
        return user

    def _new_user(self):
        User = get_user_model()
        user = User.objects.create_user(username='u' + str(User.objects.count()))
        UserProfile.objects.create(user=user, nickname='微信玩家')
        return user

    def test_get_me_returns_profile(self):
        user = self._new_user()
        self._auth(user)
        response = self.client.get('/api/v1/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nickname'], '微信玩家')

    def test_patch_nickname(self):
        user = self._new_user()
        self._auth(user)
        response = self.client.patch('/api/v1/me/', {'nickname': ' 阿杰 '}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['nickname'], '阿杰')
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.nickname, '阿杰')

    def test_patch_avatar_url(self):
        user = self._new_user()
        self._auth(user)
        response = self.client.patch('/api/v1/me/', {'avatar_url': '/media/avatars/x.jpg'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['avatar_url'], '/media/avatars/x.jpg')

    def test_patch_rejects_unknown_field(self):
        user = self._new_user()
        self._auth(user)
        response = self.client.patch('/api/v1/me/', {'is_enabled': False}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'INVALID_FIELDS')

    def test_patch_rejects_empty_nickname(self):
        user = self._new_user()
        self._auth(user)
        response = self.client.patch('/api/v1/me/', {'nickname': '   '}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'INVALID_NICKNAME')

    def test_patch_requires_auth(self):
        self.client.credentials()
        response = self.client.patch('/api/v1/me/', {'nickname': 'x'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_upload_avatar(self):
        user = self._new_user()
        self._auth(user)
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new('RGB', (16, 16), (200, 100, 80)).save(buf, format='JPEG')
        buf.seek(0)
        uploaded = SimpleUploadedFile('a.jpg', buf.read(), content_type='image/jpeg')
        response = self.client.post('/api/v1/me/avatar/', {'file': uploaded}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['avatar_url'].startswith('/media/avatars/'))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.avatar_url, response.data['avatar_url'])
