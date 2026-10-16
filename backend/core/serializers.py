from rest_framework import serializers
from .models import GamePartition, Product, ProductCategory, Favorite, Order, Partner, PartnerApplication, Review, SystemConfig, AfterSaleCase, Refund, Evidence, Settlement, SettlementItem, Conversation, Message
class GameSerializer(serializers.ModelSerializer):
    class Meta: model=GamePartition; fields=['id','name','icon','sort_order','version']
class CategorySerializer(serializers.ModelSerializer):
    class Meta: model=ProductCategory; fields=['id','game','name','description','sort_order','is_enabled','version','updated_at']
class ProductSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    def get_is_available(self, obj):
        return bool(obj.is_published and obj.game.is_enabled and obj.category_id and obj.category.is_enabled and obj.category.game_id == obj.game_id)
    game = GameSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    class Meta: model=Product; fields=['id','game','category','title','description','cover_url','price_cents','original_price_cents','min_quantity','max_quantity','platforms','is_published','is_available','version','updated_at']
class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta: model=Favorite; fields=['product','created_at']
class ReviewSerializer(serializers.ModelSerializer):
    class Meta: model=Review; fields=['id','order','user','rating','content','created_at']
class OrderSerializer(serializers.ModelSerializer):
    aftersale = serializers.SerializerMethodField()
    def get_aftersale(self, obj):
        cases = list(obj.aftersale_cases.all())
        if not cases:
            return None
        latest = max(cases, key=lambda case: case.id)
        refunds = list(latest.refunds.all())
        refund = max(refunds, key=lambda item: item.id) if refunds else None
        return {'status': latest.status, 'reason': latest.reason, 'resolution': latest.resolution,
                'refund_status': refund.status if refund else None,
                'reapplication_blocked': any(case.status != AfterSaleCase.Status.REJECTED for case in cases)}
    game_id = serializers.IntegerField(source='product.game_id', read_only=True)
    partner_info = serializers.SerializerMethodField()
    preferred_partner_info = serializers.SerializerMethodField()
    conversation_id = serializers.SerializerMethodField()

    def _partner_info(self, partner):
        if partner is None:
            return None
        profile = getattr(partner.user, 'profile', None)
        return {'id': partner.id, 'nickname': profile.nickname if profile else '陪玩',
                'avatar_url': profile.avatar_url if profile else ''}

    def get_partner_info(self, obj):
        return self._partner_info(obj.partner)

    def get_preferred_partner_info(self, obj):
        return self._partner_info(obj.preferred_partner)

    def get_conversation_id(self, obj):
        conversation = getattr(obj, 'conversation', None)
        return conversation.id if conversation else None

    review = serializers.SerializerMethodField()
    def get_review(self, obj):
        # 优先取 prefetch_related 的缓存，避免列表场景逐条查询（N+1）。
        # 注意：OneToOne 反向关系在对象上缓存的是单个实例或抛 DoesNotExist，
        # 需用 try/except 兜底单条查询场景。
        if hasattr(obj, '_prefetched_objects_cache') and 'review' in obj._prefetched_objects_cache:
            r = obj._prefetched_objects_cache['review'][0] if obj._prefetched_objects_cache['review'] else None
        else:
            try: r = obj.review
            except Review.DoesNotExist: r = None
        return ReviewSerializer(r).data if r else None
    class Meta: model=Order; fields=['aftersale','game_id','partner_info','preferred_partner_info','conversation_id','id','order_no','product','game_name_snapshot','product_title_snapshot','cover_url_snapshot','unit_price_cents','total_amount_cents','quantity','appointment_date','appointment_slot','partner','platform','role_name','role_id','message','remark','preferred_partner','status','payment_status','commission_bp','aftersale_deadline','started_at','completion_requested_at','completed_at','refunded_amount_cents','reserved_refund_cents','review','version','created_at','updated_at']
class PartnerSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    nickname = serializers.CharField(source='user.profile.nickname', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta: model=Partner; fields=['id','user','username','nickname','game','is_active','intro','version','created_at']
class PartnerApplicationSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    nickname = serializers.CharField(source='user.profile.nickname', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta: model=PartnerApplication; fields=['id','user','username','nickname','game','reason','status','reviewed_by','reviewed_at','created_at']
class ProductWriteSerializer(serializers.ModelSerializer):
    game_id = serializers.PrimaryKeyRelatedField(source='game', queryset=GamePartition.objects.all())
    category_id = serializers.PrimaryKeyRelatedField(source='category', queryset=ProductCategory.objects.all())
    class Meta: model=Product; fields=['game_id','category_id','title','description','cover_url','price_cents','original_price_cents','min_quantity','max_quantity','is_published']
    def validate(self, attrs):
        game = attrs.get('game', getattr(self.instance, 'game', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        if category and game and category.game_id != game.id:
            raise serializers.ValidationError({'category_id': '商品类型必须属于同一个游戏'})
        return attrs

class EvidenceSerializer(serializers.ModelSerializer):
    class Meta: model=Evidence; fields=['id','case','file_path','mime_type','size_bytes','created_at']
class RefundSerializer(serializers.ModelSerializer):
    class Meta: model=Refund; fields=['id','refund_no','order','case','amount_cents','status','reason','reviewed_by','reviewed_at','created_at']
class AfterSaleCaseSerializer(serializers.ModelSerializer):
    evidences = EvidenceSerializer(many=True, read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)
    nickname = serializers.CharField(source='user.profile.nickname', read_only=True)
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    product_title = serializers.CharField(source='order.product_title_snapshot', read_only=True)
    class Meta: model=AfterSaleCase; fields=['id','case_no','order','order_no','product_title','user','nickname','amount_cents','reason','status','resolution','reviewed_by','reviewed_at','evidences','refunds','created_at','updated_at']
class SettlementItemSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    nickname = serializers.CharField(source='partner.user.profile.nickname', read_only=True)
    class Meta: model=SettlementItem; fields=['id','order','order_no','partner','nickname','paid_amount_cents','refunded_amount_cents','net_income_cents','commission_bp','commission_cents','partner_income_cents','created_at']
class SettlementSerializer(serializers.ModelSerializer):
    items = SettlementItemSerializer(many=True, read_only=True)
    class Meta: model=Settlement; fields=['id','batch_no','executed_by','items','created_at']

class MessageSerializer(serializers.ModelSerializer):
    class Meta: model=Message; fields=['id','conversation','sender','kind','content','read_at','created_at']

class ConversationSerializer(serializers.ModelSerializer):
    """会话列表项：含对方昵称/头像、最后一条消息与未读数（未读数由视图按当前用户计算）。"""
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)
    partner_name = serializers.CharField(source='partner.user.profile.nickname', read_only=True)
    partner_avatar = serializers.CharField(source='partner.user.profile.avatar_url', read_only=True)
    user_name = serializers.CharField(source='user.profile.nickname', read_only=True)
    user_avatar = serializers.CharField(source='user.profile.avatar_url', read_only=True)
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    product_title = serializers.CharField(source='order.product_title_snapshot', read_only=True)
    def get_last_message(self, obj):
        messages = list(obj.messages.all())
        lm = messages[-1] if messages else None
        return MessageSerializer(lm).data if lm else None
    class Meta:
        model = Conversation
        fields = ['id','order','order_no','product_title','user','user_name','user_avatar','partner','partner_name','partner_avatar','last_message','unread_count','created_at']
