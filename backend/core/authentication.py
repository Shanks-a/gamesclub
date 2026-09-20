import hashlib
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import AccessToken
class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        value = request.headers.get('Authorization','')
        if not value.startswith('Bearer '): return None
        token = value[7:].strip()
        try: record = AccessToken.objects.select_related('user').get(token_hash=hashlib.sha256(token.encode()).hexdigest())
        except AccessToken.DoesNotExist: raise AuthenticationFailed('无效登录态')
        if record.expires_at <= timezone.now() or not record.user.is_active or not record.user.profile.is_enabled: raise AuthenticationFailed('登录态已失效')
        return record.user, record
