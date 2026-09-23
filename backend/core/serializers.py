from rest_framework import serializers
from .models import GamePartition, Product, ProductCategory, Favorite, Order
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
    class Meta: model=Product; fields=['id','game','category','title','description','cover_url','price_cents','original_price_cents','min_quantity','max_quantity','is_published','is_available','version','updated_at']
class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta: model=Favorite; fields=['product','created_at']
class OrderSerializer(serializers.ModelSerializer):
    class Meta: model=Order; fields=['id','order_no','product','game_name_snapshot','product_title_snapshot','cover_url_snapshot','unit_price_cents','total_amount_cents','quantity','status','payment_status','version','created_at','updated_at']
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
