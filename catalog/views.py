from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter
from .models import Category, Product, ProductImage

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta: model=ProductImage; fields=['id','image','image_url','alt_text','is_primary','sort_order']

class CategorySerializer(serializers.ModelSerializer):
    class Meta: model=Category; fields='__all__'

class ProductSerializer(serializers.ModelSerializer):
    images=ProductImageSerializer(many=True,read_only=True)
    category_name=serializers.CharField(source='category.name',read_only=True)
    current_price=serializers.DecimalField(max_digits=12,decimal_places=2,read_only=True)
    in_stock=serializers.BooleanField(read_only=True)
    class Meta: model=Product; fields=['id','name','slug','sku','category','category_name','description','short_description','price','sale_price','current_price','stock_quantity','in_stock','low_stock_threshold','featured','is_new','bestseller','is_active','weight','images','created_at','updated_at']

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=Category.objects.filter(is_active=True)
    serializer_class=CategorySerializer
    lookup_field='slug'

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=ProductSerializer
    lookup_field='slug'
    filter_backends=[OrderingFilter]
    ordering_fields=['price','created_at','name']
    ordering='-created_at'
    def get_queryset(self):
        qs=Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        p=self.request.query_params
        if p.get('category'): qs=qs.filter(category__slug=p['category'])
        if p.get('search'): qs=qs.filter(Q(name__icontains=p['search'])|Q(sku__icontains=p['search'])|Q(description__icontains=p['search']))
        if p.get('featured') in ['1','true','True']: qs=qs.filter(featured=True)
        if p.get('new') in ['1','true','True']: qs=qs.filter(is_new=True)
        if p.get('bestseller') in ['1','true','True']: qs=qs.filter(bestseller=True)
        return qs
