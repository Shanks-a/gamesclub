"""Fixed identities for local manual acceptance; never real WeChat identities."""
from django.conf import settings
from django.contrib.auth import get_user_model

GROUP_NAME = 'gamesclub-local-test-accounts'
ACCOUNTS = (
    ('test-user-01', '测试用户01', 'user', 'test-customer'),
    ('test-user-02', '测试用户02', 'user', None),
    ('test-user-03', '测试用户03', 'user', None),
    ('test-partner-01', '测试陪玩01', 'partner', 'dev-player'),
    ('test-partner-02', '测试陪玩02', 'partner', 'test-partner'),
    ('test-staff-01', '测试客服01', 'staff', None),
    ('test-staff-02', '测试客服02', 'staff', None),
)


def enabled():
    return settings.DEBUG and settings.ALLOW_DEV_LOGIN


def available_accounts(*, staff=False):
    if not enabled():
        return get_user_model().objects.none()
    names = [name for name, _, role, _ in ACCOUNTS if (role == 'staff') == staff]
    return get_user_model().objects.filter(
        username__in=names, groups__name=GROUP_NAME, is_active=True,
        is_staff=staff, is_superuser=False, profile__is_enabled=True,
        wechat_identities__isnull=True,
    )


def roster(*, staff=False):
    users = {u.username: u for u in available_accounts(staff=staff)}
    return [
        {'username': name, 'label': label, 'role': role}
        for name, label, role, _ in ACCOUNTS if name in users
    ]
