from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Cart, CartItem
from catalog.models import Product
class CartItemSerializer(serializers.ModelSerializer):
    product_id=serializers.IntegerField(source='product.id',read_only=True); name=serializers.CharField(source='product.name',read_only=True); sku=serializers.CharField(source='product.sku',read_only=True); image=serializers.SerializerMethodField(); unit_price=serializers.DecimalField(max_digits=12,decimal_places=2,read_only=True); line_total=serializers.DecimalField(max_digits=12,decimal_places=2,read_only=True)
    class Meta: model=CartItem; fields=['id','product_id','name','sku','image','quantity','unit_price','line_total']
    def get_image(self,obj):
        im=obj.product.images.filter(is_primary=True).first() or obj.product.images.first(); return (im.image.url if im and im.image else (im.image_url if im else None))
class CartSerializer(serializers.ModelSerializer):
    items=CartItemSerializer(many=True,read_only=True); subtotal=serializers.SerializerMethodField(); item_count=serializers.SerializerMethodField()
    class Meta: model=Cart; fields=['id','items','subtotal','item_count']
    def get_subtotal(self,obj): return sum((Decimal(str(i.line_total)) for i in obj.items.select_related('product')),Decimal('0.00'))
    def get_item_count(self,obj): return sum(i.quantity for i in obj.items.all())
def get_cart(request):
    if request.user.is_authenticated: cart,_=Cart.objects.get_or_create(user=request.user); return cart
    if not request.session.session_key: request.session.create()
    cart,_=Cart.objects.get_or_create(session_key=request.session.session_key); return cart
class CartView(APIView):
    permission_classes=[AllowAny]
    def get(self,request): return Response(CartSerializer(get_cart(request)).data)
    def delete(self,request):
        c=get_cart(request); c.items.all().delete(); return Response(CartSerializer(c).data)
class CartItemView(APIView):
    permission_classes=[AllowAny]
    @transaction.atomic
    def post(self,request):
        product=Product.objects.filter(pk=request.data.get('product_id'),is_active=True).first()
        if not product:return Response({'detail':'Product not found.'},status=404)
        qty=int(request.data.get('quantity',1)); c=get_cart(request); item,_=CartItem.objects.get_or_create(cart=c,product=product,defaults={'quantity':0}); new=item.quantity+qty
        if new<1:return Response({'detail':'Quantity must be at least 1.'},status=400)
        if new>product.stock_quantity:return Response({'detail':f'Only {product.stock_quantity} item(s) available.'},status=400)
        item.quantity=new; item.save(); return Response(CartSerializer(c).data,status=201)
    def patch(self,request):
        item=CartItem.objects.filter(pk=request.data.get('item_id'),cart=get_cart(request)).select_related('product').first()
        if not item:return Response({'detail':'Cart item not found.'},status=404)
        qty=int(request.data.get('quantity',0))
        if qty<=0:item.delete()
        elif qty>item.product.stock_quantity:return Response({'detail':f'Only {item.product.stock_quantity} item(s) available.'},status=400)
        else:item.quantity=qty; item.save()
        return Response(CartSerializer(get_cart(request)).data)
    def delete(self,request):
        CartItem.objects.filter(pk=request.data.get('item_id'),cart=get_cart(request)).delete(); return Response(CartSerializer(get_cart(request)).data)
