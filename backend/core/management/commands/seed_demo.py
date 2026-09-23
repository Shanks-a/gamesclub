from django.core.management.base import BaseCommand
from core.models import GamePartition, Product, ProductCategory
from django.contrib.auth import get_user_model
class Command(BaseCommand):
    help = 'Create the first development catalog'
    def handle(self, *args, **kwargs):
        names=['王者荣耀','和平精英','无畏契约','英雄联盟']
        games={name:GamePartition.objects.get_or_create(name=name,defaults={'sort_order':i})[0] for i,name in enumerate(names)}
        category_names=['娱乐单','技术单','指定任务']
        categories={(game.name, name): ProductCategory.objects.get_or_create(game=game, name=name, defaults={'sort_order':i})[0] for game in games.values() for i,name in enumerate(category_names)}
        rows=[('双人默契上分','王者荣耀','娱乐单',2900,3900,0),('一起轻松吃鸡','和平精英','娱乐单',2500,3500,1),('周末欢乐五排','王者荣耀','技术单',3500,4900,2),('战术默契双排','无畏契约','技术单',3200,4500,3),('峡谷欢乐局','英雄联盟','指定任务',3900,4900,0)]
        for title,game,category,price,original,art in rows:
            Product.objects.get_or_create(title=title,game=games[game],defaults={'category':categories[(game,category)],'price_cents':price,'original_price_cents':original,'cover_url':f'/static/art/product-{art}.png','description':'一起享受游戏的快乐'})
        self.stdout.write(self.style.SUCCESS('demo catalog ready'))
