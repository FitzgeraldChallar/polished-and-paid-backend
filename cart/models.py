from django.conf import settings
from django.db import models
from catalog.models import Product
class Cart(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,null=True,blank=True,related_name='cart')
    session_key=models.CharField(max_length=64,unique=True,null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    @property
    def subtotal(self): return sum((i.line_total for i in self.items.select_related('product')), 0)
class CartItem(models.Model):
    cart=models.ForeignKey(Cart,on_delete=models.CASCADE,related_name='items')
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)
    class Meta: unique_together=['cart','product']
    @property
    def unit_price(self): return self.product.current_price
    @property
    def line_total(self): return self.unit_price*self.quantity
