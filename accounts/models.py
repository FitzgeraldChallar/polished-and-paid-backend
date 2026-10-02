from django.conf import settings
from django.db import models
class CustomerProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='profile')
    phone=models.CharField(max_length=40,blank=True)
    marketing_opt_in=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.user.email or self.user.username
class Address(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='addresses')
    label=models.CharField(max_length=60,default='Home')
    first_name=models.CharField(max_length=80); last_name=models.CharField(max_length=80)
    line1=models.CharField(max_length=220); line2=models.CharField(max_length=220,blank=True)
    city=models.CharField(max_length=100); state=models.CharField(max_length=100,blank=True)
    postal_code=models.CharField(max_length=30,blank=True); country=models.CharField(max_length=100,default='United States')
    phone=models.CharField(max_length=40,blank=True); is_default=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-is_default','-created_at']
    def __str__(self): return f'{self.label} - {self.line1}, {self.city}'


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_wishlist_product',
            )
        ]

    def __str__(self):
        return f'{self.user.email or self.user.username} - {self.product.name}'
