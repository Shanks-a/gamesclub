from rest_framework import serializers
from .models import GamePartition, Product, Favorite, Order
class GameSerializer(serializers.ModelSerializer):
    class Meta: model=GamePartition; fields=['id','name','icon','sort_order','version']
class ProductSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    class Meta: model=Product; fields=['id','game','title','description','cover_url','price_cents','original_price_cents','min_quantity','max_quantity','is_published','version','updated_at']
class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta: model=Favorite; fields=['product','created_at']
class OrderSerializer(serializers.ModelSerializer):
    class Meta: model=Order; fields=['id','order_no','product','game_name_snapshot','product_title_snapshot','cover_url_snapshot','unit_price_cents','total_amount_cents','quantity','status','payment_status','version','created_at','updated_at']
class ProductWriteSerializer(serializers.ModelSerializer):
    game_id = serializers.PrimaryKeyRelatedField(source='game', queryset=GamePartition.objects.all())
    class Meta: model=Product; fields=['game_id','title','description','cover_url','price_cents','original_price_cents','min_quantity','max_quantity','is_published']
