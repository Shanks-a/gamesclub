import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import GamePartition, Partner, UserProfile
from core.test_accounts import ACCOUNTS, GROUP_NAME, enabled


class Command(BaseCommand):
    help = 'Normalize the seven local test identities, preserving IDs and business records.'

    def add_arguments(self, parser):
        parser.add_argument('--game-id', type=int, required=True)

    def handle(self, *args, **options):
        if not enabled():
            raise CommandError('Requires DEBUG and ALLOW_DEV_LOGIN.')
        try:
            game = GamePartition.objects.get(pk=options['game_id'], is_enabled=True)
        except GamePartition.DoesNotExist:
            raise CommandError('Choose an enabled game ID.')
        output = []
        with transaction.atomic():
            group, _ = Group.objects.get_or_create(name=GROUP_NAME)
            for name, label, role, legacy in ACCOUNTS:
                candidates = list(get_user_model().objects.select_for_update().filter(
                    username__in=[value for value in (name, legacy) if value]
                ))
                if len(candidates) > 1:
                    raise CommandError(f'Both legacy and canonical accounts exist for {name}; resolve manually.')
                user = candidates[0] if candidates else None
                if user and (user.wechat_identities.exists() or user.is_superuser):
                    raise CommandError(f'Refusing to modify protected identity for {name}.')
                if user and user.is_staff != (role == 'staff'):
                    raise CommandError(f'Existing role conflicts for {name}.')
                if user and user.username == name and not user.groups.filter(pk=group.pk).exists():
                    raise CommandError(f'Unmanaged canonical username already exists: {name}.')
                if user and not user.is_active:
                    raise CommandError(f'Disabled account requires manual review: {name}.')
                password = None
                if user is None:
                    user = get_user_model()(username=name, is_staff=role == 'staff')
                    if role == 'staff':
                        password = secrets.token_urlsafe(18)
                        user.set_password(password)
                    else:
                        user.set_unusable_password()
                    user.save()
                else:
                    user.username = name
                    user.save(update_fields=['username'])
                user.groups.add(group)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if not profile.is_enabled:
                    raise CommandError(f'Disabled profile requires manual review: {name}.')
                profile.nickname = label
                profile.save(update_fields=['nickname'])
                if role == 'partner':
                    partner, _ = Partner.objects.get_or_create(user=user, defaults={'game': game})
                    if partner.game_id != game.pk:
                        raise CommandError(f'Existing partner game differs for {name}; not rebinding historical orders.')
                elif Partner.objects.filter(user=user).exists():
                    raise CommandError(f'Unexpected partner role for {name}.')
                output.append(f'{label} | {name} | user_id={user.pk}' + (f' | password={password}' if password else ''))
        # Only print credentials after the entire transaction succeeds. Reruns never reset passwords.
        self.stdout.write('\n'.join(output))
