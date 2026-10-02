from django.contrib import admin
from .models import Category, Product, ProductImage
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin): list_display=['name','is_active','sort_order']; prepopulated_fields={'slug':('name',)}; list_filter=['is_active']; search_fields=['name']
class ProductImageInline(admin.TabularInline): model=ProductImage; extra=1
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin): list_display=['name','sku','category','price','sale_price','stock_quantity','featured','is_new','bestseller','is_active']; list_filter=['category','featured','is_new','bestseller','is_active']; search_fields=['name','sku']; prepopulated_fields={'slug':('name',)}; inlines=[ProductImageInline]
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin): list_display=['product','is_primary','sort_order']
