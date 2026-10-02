from django.db import models
from orders.models import Order
class Payment(models.Model):
    STATUS=[('pending','Pending'),('paid','Paid'),('failed','Failed'),('cancelled','Cancelled'),('refunded','Refunded')]
    order=models.OneToOneField(Order,on_delete=models.CASCADE,related_name='payment')
    provider=models.CharField(max_length=40,default='stripe')
    stripe_checkout_session_id=models.CharField(max_length=255,blank=True,unique=True,null=True)
    stripe_payment_intent_id=models.CharField(max_length=255,blank=True)
    amount=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=10,default='USD'); status=models.CharField(max_length=20,choices=STATUS,default='pending'); raw_response=models.JSONField(default=dict,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return f'{self.order.order_number} - {self.status}'
