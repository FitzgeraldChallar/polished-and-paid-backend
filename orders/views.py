import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderItem
from cart.views import get_cart
from cart.models import Cart
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta: model=OrderItem; fields=['id','product','product_name','sku','quantity','unit_price','line_total']
class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    class Meta: model=Order; fields='__all__'
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=OrderSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self): return Order.objects.filter(user=self.request.user).prefetch_related('items')
class CheckoutSerializer(serializers.Serializer):
    email=serializers.EmailField(); first_name=serializers.CharField(); last_name=serializers.CharField(); shipping_line1=serializers.CharField(); shipping_line2=serializers.CharField(required=False,allow_blank=True); shipping_city=serializers.CharField(); shipping_state=serializers.CharField(required=False,allow_blank=True); shipping_postal_code=serializers.CharField(required=False,allow_blank=True); shipping_country=serializers.CharField(default='United States'); shipping_phone=serializers.CharField(required=False,allow_blank=True); shipping_fee=serializers.DecimalField(max_digits=12,decimal_places=2,required=False,default=0); tax=serializers.DecimalField(max_digits=12,decimal_places=2,required=False,default=0); notes=serializers.CharField(required=False,allow_blank=True)
class CheckoutView(APIView):
    permission_classes=[AllowAny]
    @transaction.atomic
    def post(self,request):
        s=CheckoutSerializer(data=request.data); s.is_valid(raise_exception=True); cart=get_cart(request); items=list(cart.items.select_related('product').select_for_update())
        if not items:return Response({'detail':'Your cart is empty.'},status=400)
        subtotal=Decimal('0.00')
        for item in items:
            if not item.product.is_active:return Response({'detail':f'{item.product.name} is unavailable.'},status=400)
            if item.quantity>item.product.stock_quantity:return Response({'detail':f'Insufficient stock for {item.product.name}.'},status=400)
            subtotal += item.line_total
        d=s.validated_data; shipping=d.get('shipping_fee',Decimal('0')); tax=d.get('tax',Decimal('0')); total=subtotal+shipping+tax
        order=Order.objects.create(user=request.user if request.user.is_authenticated else None,order_number='PP-'+uuid.uuid4().hex[:10].upper(),status='pending',email=d['email'],first_name=d['first_name'],last_name=d['last_name'],shipping_line1=d['shipping_line1'],shipping_line2=d.get('shipping_line2',''),shipping_city=d['shipping_city'],shipping_state=d.get('shipping_state',''),shipping_postal_code=d.get('shipping_postal_code',''),shipping_country=d.get('shipping_country','United States'),shipping_phone=d.get('shipping_phone',''),subtotal=subtotal,shipping_fee=shipping,tax=tax,total=total,notes=d.get('notes',''))
        for item in items:
            OrderItem.objects.create(order=order,product=item.product,product_name=item.product.name,sku=item.product.sku,quantity=item.quantity,unit_price=item.unit_price,line_total=item.line_total)
        cart.items.all().delete()
        return Response(OrderSerializer(order).data,status=201)
