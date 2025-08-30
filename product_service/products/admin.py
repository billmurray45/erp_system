# product_service/products/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Supplier, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'products_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Количество товаров'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'products_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'email']
    readonly_fields = ['created_at', 'updated_at']

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Количество товаров'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.image.url
            )
        return "Нет изображения"

    image_preview.short_description = 'Предпросмотр'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'sku', 'category', 'supplier', 'selling_price',
        'stock_quantity', 'stock_status_colored', 'status', 'is_featured'
    ]
    list_filter = [
        'status', 'is_featured', 'category', 'supplier',
        'created_at', 'updated_at'
    ]
    search_fields = ['name', 'sku', 'barcode', 'description']
    readonly_fields = [
        'profit_margin_display', 'current_price', 'stock_status',
        'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'sku', 'barcode', 'description', 'category', 'supplier')
        }),
        ('Цены и финансы', {
            'fields': ('cost_price', 'selling_price', 'discount_price', 'profit_margin_display', 'current_price')
        }),
        ('Склад и запасы', {
            'fields': ('stock_quantity', 'min_stock_level', 'max_stock_level', 'stock_status')
        }),
        ('Характеристики', {
            'fields': ('weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Статус и настройки', {
            'fields': ('status', 'is_featured')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    inlines = [ProductImageInline]
    actions = ['sync_to_core', 'mark_as_featured', 'mark_as_discontinued']

    def profit_margin_display(self, obj):
        margin = obj.profit_margin
        color = 'green' if margin > 30 else 'orange' if margin > 10 else 'red'
        return format_html(
            '<span style="color: {};">{:.2f}%</span>',
            color, margin
        )

    profit_margin_display.short_description = 'Маржа прибыли'

    def stock_status_colored(self, obj):
        status = obj.stock_status
        if status == "Нет в наличии":
            color = 'red'
        elif status == "Заканчивается":
            color = 'orange'
        else:
            color = 'green'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )

    stock_status_colored.short_description = 'Статус запасов'

    def sync_to_core(self, request, queryset):
        success_count = 0
        for product in queryset:
            if product.sync_to_core_service():
                success_count += 1

        self.message_user(
            request,
            f'Синхронизировано {success_count} из {queryset.count()} товаров'
        )

    sync_to_core.short_description = 'Синхронизировать с Core Service'

    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(
            request,
            f'{updated} товаров отмечено как рекомендуемые'
        )

    mark_as_featured.short_description = 'Отметить как рекомендуемые'

    def mark_as_discontinued(self, request, queryset):
        """Снять с производства"""
        updated = queryset.update(status='DISCONTINUED')
        self.message_user(
            request,
            f'{updated} товаров снято с производства'
        )

    mark_as_discontinued.short_description = 'Снять с производства'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name', 'alt_text']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 150px;" />',
                obj.image.url
            )
        return "Нет изображения"

    image_preview.short_description = 'Предпросмотр'
