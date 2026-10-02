from django.contrib import admin
from .models import Order, OrderItem
class OrderItemInline(admin.TabularInline): model=OrderItem; extra=0; readonly_fields=['product_name','sku','quantity','unit_price','line_total']
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin): list_display=['order_number','email','status','subtotal','shipping_fee','tax','total','currency','created_at']; list_filter=['status','currency','created_at']; search_fields=['order_number','email']; readonly_fields=['order_number','subtotal','total','created_at','updated_at']; inlines=[OrderItemInline]
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin): list_display=['order','product_name','sku','quantity','unit_price','line_total']; search_fields=['order__order_number','product_name','sku']
