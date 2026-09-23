from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import F
from .models import GamePartition, ProductCategory, Product, Order, UserProfile

admin.site.site_header = '游伴 CLUB 管理后台'
admin.site.site_title = '游伴 CLUB 管理后台'
admin.site.index_title = '业务管理'

@admin.register(GamePartition)
class GamePartitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_enabled', 'version')
    list_editable = ('sort_order', 'is_enabled')

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('game', 'name', 'sort_order', 'is_enabled', 'version', 'updated_at')
    list_filter = ('game', 'is_enabled')
    list_editable = ('sort_order', 'is_enabled')
    search_fields = ('name', 'game__name')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'game', 'category', 'price_cents', 'is_published', 'version', 'updated_at', 'edit_product')
    readonly_fields = ('version', 'updated_at')
    actions = None
    fieldsets = (
        ('基本信息', {'fields': ('title', 'game', 'category', 'description', 'cover_url')}),
        ('价格与购买限制', {'fields': ('price_cents', 'original_price_cents', 'min_quantity', 'max_quantity')}),
        ('展示状态', {'fields': ('is_published', 'version', 'updated_at')}),
    )

    @admin.display(description='操作')
    def edit_product(self, obj):
        return format_html('<a href="{}">编辑商品</a>', reverse('admin:core_product_change', args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        if change:
            obj.version = F('version') + 1
        super().save_model(request, obj, form, change)
        obj.refresh_from_db()

    def has_delete_permission(self, request, obj=None):
        return False
    list_filter = ('game', 'category', 'is_published')
    search_fields = ('title', 'description')

admin.site.register(UserProfile)
admin.site.register(Order)

# Maintenance UI is read-only: all catalog writes go through the versioned,
# audited management API; orders must never bypass their state machine.
class ReadOnlyMaintenance(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    def get_readonly_fields(self, request, obj=None): return [f.name for f in self.model._meta.fields]

for model in (GamePartition, ProductCategory, Product, Order):
    admin.site.unregister(model)
    admin.site.register(model, ReadOnlyMaintenance)
