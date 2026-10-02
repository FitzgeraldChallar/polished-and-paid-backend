from django.db import models
from catalog.models import Product
class InventoryTransaction(models.Model):
    TYPES=[('restock','Restock'),('sale','Sale'),('adjustment','Adjustment'),('return','Return')]
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='inventory_transactions')
    transaction_type=models.CharField(max_length=20,choices=TYPES); quantity=models.IntegerField(); note=models.CharField(max_length=255,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.product.sku}: {self.quantity}'
