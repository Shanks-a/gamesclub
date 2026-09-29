import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOW_DEV_LOGIN = os.getenv('ALLOW_DEV_LOGIN', '0') == '1'
ALLOW_MOCK_PAYMENT = os.getenv('ALLOW_MOCK_PAYMENT', '0') == '1'
WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')
ALLOWED_HOSTS = [h for h in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        'http://127.0.0.1:5174,http://localhost:5174',
    ).split(',')
    if origin.strip()
]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','rest_framework','core.apps.CoreConfig']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
if os.getenv('DATABASE_URL'):
    import urllib.parse
    u = urllib.parse.urlparse(os.environ['DATABASE_URL'])
    DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql','NAME':u.path.lstrip('/'),'USER':u.username,'PASSWORD':u.password,'HOST':u.hostname,'PORT':u.port or 5432}}
elif os.getenv('ALLOW_SQLITE_DEV') == '1':
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR / 'dev.sqlite3'}}
else:
    raise ImproperlyConfigured('请设置 DATABASE_URL；仅本地兼容测试可显式设置 ALLOW_SQLITE_DEV=1')
LANGUAGE_CODE = 'zh-hans'; TIME_ZONE = 'Asia/Shanghai'; USE_I18N = True; USE_TZ = True
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_DIRS = [BASE_DIR.parent / 'apps' / 'miniapp' / 'src' / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES':['core.authentication.BearerAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'],'DEFAULT_RENDERER_CLASSES':['core.renderers.UTF8JSONRenderer'],'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema'}
SPECTACULAR_SETTINGS = {'TITLE':'GamesClub API','VERSION':'1.0.0'}
REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'core.errors.api_exception_handler'
MIDDLEWARE.append('core.errors.RequestLogMiddleware')
