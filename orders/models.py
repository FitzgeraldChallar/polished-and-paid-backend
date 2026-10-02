from django.conf import settings
from django.db import models
from catalog.models import Product
class Order(models.Model):
    STATUS_CHOICES=[('pending','Pending'),('paid','Paid'),('processing','Processing'),('shipped','Shipped'),('delivered','Delivered'),('cancelled','Cancelled'),('refunded','Refunded')]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='orders')
    order_number=models.CharField(max_length=30,unique=True)
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    email=models.EmailField(); first_name=models.CharField(max_length=80); last_name=models.CharField(max_length=80)
    shipping_line1=models.CharField(max_length=220); shipping_line2=models.CharField(max_length=220,blank=True); shipping_city=models.CharField(max_length=100); shipping_state=models.CharField(max_length=100,blank=True); shipping_postal_code=models.CharField(max_length=30,blank=True); shipping_country=models.CharField(max_length=100,default='United States'); shipping_phone=models.CharField(max_length=40,blank=True)
    subtotal=models.DecimalField(max_digits=12,decimal_places=2); shipping_fee=models.DecimalField(max_digits=12,decimal_places=2,default=0); tax=models.DecimalField(max_digits=12,decimal_places=2,default=0); total=models.DecimalField(max_digits=12,decimal_places=2)
    currency=models.CharField(max_length=10,default='USD'); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-created_at']
    def __str__(self): return self.order_number
class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    product=models.ForeignKey(Product,on_delete=models.SET_NULL,null=True,blank=True)
    product_name=models.CharField(max_length=220); sku=models.CharField(max_length=80); quantity=models.PositiveIntegerField(); unit_price=models.DecimalField(max_digits=12,decimal_places=2); line_total=models.DecimalField(max_digits=12,decimal_places=2)
    def __str__(self): return f'{self.product_name} x {self.quantity}'
