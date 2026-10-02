from django.db import models
from django.utils.text import slugify
import re
import uuid

class Category(models.Model):
    name=models.CharField(max_length=120,unique=True)
    slug=models.SlugField(max_length=140,unique=True,blank=True)
    description=models.TextField(blank=True)
    image=models.FileField(upload_to='categories/',blank=True,null=True)
    image_url=models.URLField(blank=True)
    icon=models.CharField(max_length=80,blank=True)
    is_active=models.BooleanField(default=True)
    sort_order=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['sort_order','name']
    def save(self,*args,**kwargs):
        if not self.slug:self.slug=slugify(self.name)
        super().save(*args,**kwargs)
    def __str__(self): return self.name

class Product(models.Model):
    category=models.ForeignKey(Category,on_delete=models.PROTECT,related_name='products')
    name=models.CharField(max_length=220)
    slug=models.SlugField(max_length=240,unique=True,blank=True)
    sku=models.CharField(max_length=80,unique=True)
    description=models.TextField(blank=True)
    short_description=models.CharField(max_length=400,blank=True)
    price=models.DecimalField(max_digits=12,decimal_places=2)
    sale_price=models.DecimalField(max_digits=12,decimal_places=2,blank=True,null=True)
    stock_quantity=models.PositiveIntegerField(default=0)
    low_stock_threshold=models.PositiveIntegerField(default=5)
    featured=models.BooleanField(default=False)
    is_new=models.BooleanField(default=True)
    bestseller=models.BooleanField(default=False)
    is_active=models.BooleanField(default=True)
    weight=models.DecimalField(max_digits=8,decimal_places=2,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-created_at']
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=slugify(self.name)
        if not self.sku:
            self.sku=self.generate_sku()
        super().save(*args,**kwargs)
    def generate_sku(self):
        category_name = self.category.name if self.category_id and self.category else 'Product'
        letters = re.sub(r'[^A-Za-z0-9]+', '', category_name).upper()
        prefix = (letters[:3] or 'GEN').ljust(3, 'X')
        for _ in range(20):
            candidate = f'PP-{prefix}-{uuid.uuid4().hex[:6].upper()}'
            if not Product.objects.filter(sku=candidate).exists():
                return candidate
        return f'PP-{prefix}-{uuid.uuid4().hex[:10].upper()}'
    @property
    def current_price(self): return self.sale_price if self.sale_price is not None else self.price
    @property
    def in_stock(self): return self.stock_quantity>0
    def __str__(self): return f'{self.name} ({self.sku})'

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.FileField(upload_to='products/',blank=True,null=True)
    image_url=models.URLField(blank=True)
    alt_text=models.CharField(max_length=220,blank=True)
    is_primary=models.BooleanField(default=False)
    sort_order=models.PositiveIntegerField(default=0)
    class Meta: ordering=['sort_order','id']
    def __str__(self): return f'{self.product.name} image'
