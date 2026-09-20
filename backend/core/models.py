import hashlib, secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField(max_length=80, default='快乐玩家')
    avatar_url = models.URLField(blank=True)
    is_enabled = models.BooleanField(default=True)

class AccessToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    @staticmethod
    def issue(user):
        raw = secrets.token_urlsafe(32)
        from django.utils import timezone
        return raw, AccessToken.objects.create(user=user, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=timezone.now()+timedelta(days=30))

class GamePartition(models.Model):
    name = models.CharField(max_length=40, unique=True)
    icon = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

class Product(models.Model):
    game = models.ForeignKey(GamePartition, on_delete=models.PROTECT, related_name='products')
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    cover_url = models.CharField(max_length=255, blank=True)
    price_cents = models.PositiveIntegerField()
    original_price_cents = models.PositiveIntegerField()
    min_quantity = models.PositiveIntegerField(default=1)
    max_quantity = models.PositiveIntegerField(default=5)
    is_published = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: constraints = [models.UniqueConstraint(fields=['user','product'], name='uniq_user_product_favorite')]

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT='PENDING_PAYMENT'; PENDING_ARRANGEMENT='PENDING_ARRANGEMENT'; CANCELLED='CANCELLED'
    class PaymentStatus(models.TextChoices):
        UNPAID='UNPAID'; PAID='PAID'
    order_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    game_name_snapshot = models.CharField(max_length=40)
    product_title_snapshot = models.CharField(max_length=120)
    cover_url_snapshot = models.CharField(max_length=255, blank=True)
    unit_price_cents = models.PositiveIntegerField()
    total_amount_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_PAYMENT)
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=32, blank=True); to_status = models.CharField(max_length=32)
    action = models.CharField(max_length=40); actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

class PaymentAttempt(models.Model):
    class Status(models.TextChoices): PENDING='PENDING'; SUCCEEDED='SUCCEEDED'; FAILED='FAILED'
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments')
    idempotency_key = models.CharField(max_length=100, unique=True)
    amount_cents = models.PositiveIntegerField(); status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True); completed_at = models.DateTimeField(null=True)

class IdempotencyRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    key = models.CharField(max_length=100); action = models.CharField(max_length=80); resource_id = models.CharField(max_length=80, blank=True)
    request_hash = models.CharField(max_length=64); response_json = models.JSONField(default=dict); status_code = models.PositiveSmallIntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: constraints = [models.UniqueConstraint(fields=['user','key'], name='uniq_user_idempotency_key')]
