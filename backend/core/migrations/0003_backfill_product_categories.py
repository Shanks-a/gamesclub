from django.db import migrations

def backfill_categories(apps, schema_editor):
    GamePartition = apps.get_model('core', 'GamePartition')
    ProductCategory = apps.get_model('core', 'ProductCategory')
    Product = apps.get_model('core', 'Product')
    for game in GamePartition.objects.all():
        category, _ = ProductCategory.objects.get_or_create(game=game, name='娱乐单', defaults={'sort_order': 0})
        Product.objects.filter(game=game, category__isnull=True).update(category=category)

class Migration(migrations.Migration):
    dependencies = [('core', '0002_productcategory_product_category_and_more')]
    operations = [migrations.RunPython(backfill_categories, migrations.RunPython.noop)]
