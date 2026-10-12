import uuid
from decimal import Decimal

from django.core import signing
from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.views import get_cart
from .models import Order, OrderItem


CHECKOUT_TOKEN_SALT = "polishpay.stripe-checkout"


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "sku", "quantity", "unit_price", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class CheckoutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    shipping_line1 = serializers.CharField()
    shipping_line2 = serializers.CharField(required=False, allow_blank=True)
    shipping_city = serializers.CharField()
    shipping_state = serializers.CharField(required=False, allow_blank=True)
    shipping_postal_code = serializers.CharField(required=False, allow_blank=True)
    shipping_country = serializers.CharField(default="United States")
    shipping_phone = serializers.CharField(required=False, allow_blank=True)
    shipping_fee = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_shipping_fee(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Shipping fee cannot be negative.")
        return value

    def validate_tax(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Tax cannot be negative.")
        return value


class CheckoutView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_cart(request)
        items = list(cart.items.select_related("product").select_for_update())
        if not items:
            return Response({"detail": "Your cart is empty."}, status=400)

        subtotal = Decimal("0.00")
        for item in items:
            if not item.product.is_active:
                return Response({"detail": f"{item.product.name} is unavailable."}, status=400)
            if item.quantity > item.product.stock_quantity:
                return Response({"detail": f"Insufficient stock for {item.product.name}."}, status=400)
            subtotal += item.line_total

        data = serializer.validated_data
        shipping = data.get("shipping_fee", Decimal("0.00"))
        tax = data.get("tax", Decimal("0.00"))
        total = subtotal + shipping + tax
        if total <= Decimal("0.00"):
            return Response({"detail": "The order total must be greater than zero."}, status=400)

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            order_number="PP-" + uuid.uuid4().hex[:10].upper(),
            status="pending",
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            shipping_line1=data["shipping_line1"],
            shipping_line2=data.get("shipping_line2", ""),
            shipping_city=data["shipping_city"],
            shipping_state=data.get("shipping_state", ""),
            shipping_postal_code=data.get("shipping_postal_code", ""),
            shipping_country=data.get("shipping_country", "United States"),
            shipping_phone=data.get("shipping_phone", ""),
            subtotal=subtotal,
            shipping_fee=shipping,
            tax=tax,
            total=total,
            notes=data.get("notes", ""),
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                sku=item.product.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )

        # This signed, order-specific capability lets guest customers start or
        # retry payment without exposing an endpoint that accepts order IDs alone.
        checkout_token = signing.dumps(
            {"order_id": order.pk, "order_number": order.order_number},
            salt=CHECKOUT_TOKEN_SALT,
        )

        # The cart is consumed only after the order has been saved successfully.
        cart.items.all().delete()

        response_data = dict(OrderSerializer(order).data)
        response_data["checkout_token"] = checkout_token
        return Response(response_data, status=201)
