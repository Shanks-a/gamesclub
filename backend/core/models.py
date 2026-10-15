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

class WechatIdentity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wechat_identities')
    appid = models.CharField('小程序 AppID', max_length=64)
    openid = models.CharField('微信 openid', max_length=64)
    unionid = models.CharField('微信 unionid', max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['appid','openid'], name='uniq_appid_openid')]
        verbose_name = '微信身份'
        verbose_name_plural = '微信身份'

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
    # 支持的游戏平台规格，逗号分隔：mobile=手机端，pc=电脑端。双端游戏（如无畏契约、三角洲行动）的商品可填 "pc,mobile"
    platforms = models.CharField('支持平台', max_length=20, default='mobile')
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

class Partner(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='partner', verbose_name='陪玩账号')
    game = models.ForeignKey(GamePartition, on_delete=models.PROTECT, related_name='partners', verbose_name='绑定游戏分区')
    is_active = models.BooleanField('接单开关', default=True)
    intro = models.CharField('陪玩简介', max_length=255, blank=True)
    version = models.PositiveIntegerField('版本', default=1)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = '陪玩档案'
        verbose_name_plural = '陪玩档案'

class PartnerApplication(models.Model):
    class Status(models.TextChoices):
        PENDING='PENDING'; APPROVED='APPROVED'; REJECTED='REJECTED'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='partner_applications', verbose_name='申请人')
    game = models.ForeignKey(GamePartition, on_delete=models.PROTECT, related_name='partner_applications', verbose_name='意向游戏分区')
    reason = models.TextField('申请说明', blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='reviewed_applications', verbose_name='审核人')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','game'], name='uniq_user_game_application')]
        verbose_name = '陪玩入驻申请'
        verbose_name_plural = '陪玩入驻申请'

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT='PENDING_PAYMENT'; PENDING_ARRANGEMENT='PENDING_ARRANGEMENT'; PENDING_ACCEPTANCE='PENDING_ACCEPTANCE'; ACCEPTED='ACCEPTED'; IN_SERVICE='IN_SERVICE'; PENDING_CONFIRMATION='PENDING_CONFIRMATION'; COMPLETED='COMPLETED'; CANCELLED='CANCELLED'
    class PaymentStatus(models.TextChoices):
        UNPAID='UNPAID'; PAID='PAID'
    class Slot(models.TextChoices):
        MORNING='morning'; AFTERNOON='afternoon'; EVENING='evening'
    class Platform(models.TextChoices):
        MOBILE='mobile'; PC='pc'
    order_no = models.CharField('订单号', max_length=32, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders', verbose_name='用户')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
    game_name_snapshot = models.CharField(max_length=40)
    product_title_snapshot = models.CharField(max_length=120)
    cover_url_snapshot = models.CharField(max_length=255, blank=True)
    unit_price_cents = models.PositiveIntegerField()
    total_amount_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    appointment_date = models.DateField('预约日期', null=True, blank=True)
    appointment_slot = models.CharField('预约时段', max_length=16, choices=Slot.choices, null=True, blank=True)
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, null=True, blank=True, related_name='orders', verbose_name='陪玩')
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_PAYMENT)
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    commission_bp = models.PositiveIntegerField('抽成基点', default=0)
    # 下单需求信息（提交订单页填写）
    platform = models.CharField('游戏平台', max_length=16, choices=Platform.choices, null=True, blank=True)
    role_name = models.CharField('游戏角色名称', max_length=80, blank=True)
    role_id = models.CharField('游戏角色ID', max_length=80, blank=True)
    message = models.CharField('留言', max_length=255, blank=True)
    remark = models.CharField('发单备注（仅接单陪玩可见）', max_length=255, blank=True)
    # 客户指定的期望陪玩（意向）；付款后统一进入待派单，由客服确认后人工派单，此字段仅作参考
    preferred_partner = models.ForeignKey(Partner, on_delete=models.PROTECT, null=True, blank=True, related_name='preferred_orders', verbose_name='客户指定陪玩')
    aftersale_deadline = models.DateTimeField('售后截止时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    refunded_amount_cents = models.PositiveIntegerField('累计退款（分）', default=0)
    reserved_refund_cents = models.PositiveIntegerField('预留退款（分）', default=0)
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

class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review', verbose_name='订单')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='评价用户')
    rating = models.PositiveSmallIntegerField('评分', default=5)
    content = models.TextField('评价内容', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '评价'
        verbose_name_plural = '评价'

class SystemConfig(models.Model):
    key = models.CharField('配置键', max_length=64, unique=True)
    value_json = models.JSONField('配置值', default=dict)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'

def get_config_int(key, default):
    """读取整数型系统配置，缺失或异常时返回默认值。"""
    try:
        val = SystemConfig.objects.get(key=key).value_json
        if isinstance(val, dict):
            v = val.get('value')
        else:
            v = val
        return int(v)
    except (SystemConfig.DoesNotExist, TypeError, ValueError):
        return default

class AfterSaleCase(models.Model):
    class Status(models.TextChoices):
        OPEN='OPEN'; APPROVED='APPROVED'; REJECTED='REJECTED'; CLOSED='CLOSED'
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='aftersale_cases', verbose_name='订单')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='申请人')
    case_no = models.CharField('案件号', max_length=32, unique=True)
    amount_cents = models.PositiveIntegerField('申请退款金额（分）')
    reason = models.TextField('申请说明', blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    resolution = models.TextField('复核结论', blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='reviewed_aftersales')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['order'], condition=models.Q(status='OPEN'), name='one_open_aftersale_per_order')]
        verbose_name = '售后案件'
        verbose_name_plural = '售后案件'

class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING='PENDING'; SUCCEEDED='SUCCEEDED'; FAILED='FAILED'; UNKNOWN='UNKNOWN'
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='refunds', verbose_name='订单')
    case = models.ForeignKey(AfterSaleCase, on_delete=models.PROTECT, null=True, blank=True, related_name='refunds', verbose_name='售后案件')
    refund_no = models.CharField('退款号', max_length=32, unique=True)
    amount_cents = models.PositiveIntegerField('退款金额（分）')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField('退款原因', max_length=255, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['order'], condition=models.Q(status='PENDING'), name='one_pending_refund_per_order')]
        verbose_name = '退款'
        verbose_name_plural = '退款'

class Evidence(models.Model):
    case = models.ForeignKey(AfterSaleCase, on_delete=models.CASCADE, null=True, blank=True, related_name='evidences', verbose_name='售后案件')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='上传者')
    file_path = models.CharField('文件路径', max_length=255)
    mime_type = models.CharField('MIME 类型', max_length=32)
    size_bytes = models.PositiveIntegerField('文件大小（字节）')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '售后凭证'
        verbose_name_plural = '售后凭证'

class Conversation(models.Model):
    """客户与陪玩围绕订单的会话。陪玩接单后自动创建，一单一会话。"""
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='conversation', verbose_name='订单')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='conversations', verbose_name='客户')
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='conversations', verbose_name='陪玩')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '会话'
        verbose_name_plural = '会话'

class Message(models.Model):
    class Sender(models.TextChoices):
        USER='USER'; PARTNER='PARTNER'
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name='会话')
    sender = models.CharField('发送方', max_length=16, choices=Sender.choices)
    content = models.TextField('消息内容')
    read_at = models.DateTimeField('已读时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['id']
        verbose_name = '消息'
        verbose_name_plural = '消息'

class Settlement(models.Model):
    batch_no = models.CharField('批次号', max_length=32, unique=True)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='结算人')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '结算批次'
        verbose_name_plural = '结算批次'

class SettlementItem(models.Model):
    settlement = models.ForeignKey(Settlement, on_delete=models.CASCADE, related_name='items', verbose_name='结算批次')
    order = models.ForeignKey(Order, on_delete=models.PROTECT, unique=True, related_name='settlement_item', verbose_name='订单')
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, verbose_name='陪玩')
    paid_amount_cents = models.PositiveIntegerField('实收（分）')
    refunded_amount_cents = models.PositiveIntegerField('已退款（分）')
    net_income_cents = models.PositiveIntegerField('净收入（分）')
    commission_bp = models.PositiveIntegerField('抽成基点')
    commission_cents = models.PositiveIntegerField('抽成（分）')
    partner_income_cents = models.PositiveIntegerField('陪玩收益（分）')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '结算明细'
        verbose_name_plural = '结算明细'

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
