from django.core.management.base import BaseCommand
from core.models import GamePartition, Product
from django.contrib.auth import get_user_model
class Command(BaseCommand):
    help = 'Create the first development catalog'
    def handle(self, *args, **kwargs):
        user,_=get_user_model().objects.get_or_create(username='dev-admin',defaults={'is_staff':True,'is_superuser':True}); user.is_staff=True; user.is_superuser=True; user.save(update_fields=['is_staff','is_superuser'])
        names=['王者荣耀','和平精英','无畏契约','英雄联盟']
        games={name:GamePartition.objects.get_or_create(name=name,defaults={'sort_order':i})[0] for i,name in enumerate(names)}
        rows=[('双人默契上分','王者荣耀',2900,3900,0),('一起轻松吃鸡','和平精英',2500,3500,1),('周末欢乐五排','王者荣耀',3500,4900,2),('战术默契双排','无畏契约',3200,4500,3),('峡谷欢乐局','英雄联盟',3900,4900,0)]
        for title,game,price,original,art in rows:
            Product.objects.get_or_create(title=title,game=games[game],defaults={'price_cents':price,'original_price_cents':original,'cover_url':f'/static/art/product-{art}.png','description':'一起享受游戏的快乐'})
        self.stdout.write(self.style.SUCCESS('demo catalog ready'))
