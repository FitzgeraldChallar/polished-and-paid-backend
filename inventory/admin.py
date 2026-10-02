from django.contrib import admin
from .models import InventoryTransaction
@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin): list_display=['product','transaction_type','quantity','note','created_at']; list_filter=['transaction_type']; search_fields=['product__sku','product__name']
