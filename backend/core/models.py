import hashlib, secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='用户')
    nickname = models.CharField('昵称', max_length=80, default='快乐玩家')
    avatar_url = models.URLField('头像地址', blank=True)
    is_enabled = models.BooleanField('启用', default=True)
    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

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
    def __str__(self):
        return self.name
    name = models.CharField('名称', max_length=40, unique=True)
    icon = models.CharField('图标地址', max_length=255, blank=True)
    sort_order = models.PositiveIntegerField('排序值', default=0)
    is_enabled = models.BooleanField('启用', default=True)
    version = models.PositiveIntegerField('版本', default=1)
    class Meta:
        verbose_name = '游戏分区'
        verbose_name_plural = '游戏分区'

class ProductCategory(models.Model):
    def __str__(self):
        return f'{self.game.name} / {self.name}'
    game = models.ForeignKey(GamePartition, on_delete=models.PROTECT, related_name='categories', verbose_name='所属游戏')
    name = models.CharField('类型名称', max_length=40)
    description = models.CharField('类型说明', max_length=255, blank=True)
    sort_order = models.PositiveIntegerField('排序值', default=0)
    is_enabled = models.BooleanField('启用', default=True)
    version = models.PositiveIntegerField('版本', default=1)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['game','name'], name='uniq_game_category_name')]
        ordering = ['sort_order', 'id']
        verbose_name = '商品类型'
        verbose_name_plural = '商品类型'

class Product(models.Model):
    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if not self.category_id:
            errors['category'] = '请选择商品类型'
        elif self.category.game_id != self.game_id:
            errors['category'] = '商品类型必须属于所选游戏'
        if self.min_quantity is not None and self.max_quantity is not None and (self.min_quantity < 1 or self.max_quantity < self.min_quantity):
            errors['max_quantity'] = '最大数量不能小于最小数量，最小数量至少为 1'
        if errors:
            raise ValidationError(errors)
    game = models.ForeignKey(GamePartition, on_delete=models.PROTECT, related_name='products', verbose_name='所属游戏')
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products', null=True, blank=True, verbose_name='商品类型')
    title = models.CharField('商品名称', max_length=120)
    description = models.TextField('商品说明', blank=True)
    cover_url = models.CharField('封面地址', max_length=255, blank=True)
    price_cents = models.PositiveIntegerField('售价（分）')
    original_price_cents = models.PositiveIntegerField('原价（分）')
    min_quantity = models.PositiveIntegerField('最小数量', default=1)
    max_quantity = models.PositiveIntegerField('最大数量', default=5)
    is_published = models.BooleanField('已上架', default=True)
    version = models.PositiveIntegerField('版本', default=1)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'

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
    order_no = models.CharField('订单号', max_length=32, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders', verbose_name='用户')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
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
    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=32, blank=True); to_status = models.CharField(max_length=32)
    action = models.CharField(max_length=40); actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

class PaymentAttempt(models.Model):
    class Meta:
        constraints = [models.UniqueConstraint(fields=['order'], condition=models.Q(status='SUCCEEDED'), name='one_successful_payment_per_order')]
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

class HomeEntry(models.Model):
    kind = models.CharField(max_length=16, choices=[('banner','轮播'),('special','特价'),('popular','人气')])
    title = models.CharField(max_length=120)
    image_url = models.CharField(max_length=255, blank=True)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    game = models.ForeignKey(GamePartition, null=True, blank=True, on_delete=models.PROTECT)
    target = models.CharField(max_length=16, choices=[('product','商品'),('game','游戏'),('none','不跳转')], default='none')
    sort_order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    resource = models.CharField(max_length=64)
    resource_id = models.CharField(max_length=80)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
