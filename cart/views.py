from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem
from catalog.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True,
    )

    name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )

    image = serializers.SerializerMethodField()

    unit_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "name",
            "sku",
            "image",
            "quantity",
            "unit_price",
            "line_total",
        ]

    def get_image(self, obj):
        image = (
            obj.product.images.filter(is_primary=True).first()
            or obj.product.images.first()
        )

        if not image:
            return None

        if getattr(image, "image", None):
            return image.image.url

        if getattr(image, "image_url", None):
            return image.image_url

        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    subtotal = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "subtotal",
            "item_count",
        ]

    def get_subtotal(self, obj):
        return sum(
            (
                Decimal(str(item.line_total))
                for item in obj.items.select_related("product")
            ),
            Decimal("0.00"),
        )

    def get_item_count(self, obj):
        return sum(
            item.quantity
            for item in obj.items.all()
        )


def get_cart(request):
    """
    Resolve the active cart.

    Authenticated customers always use their persistent
    user-owned cart.

    Guests use the Django session cart.
    """

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
        )
        return cart

    # Make sure an anonymous browser has a persistent
    # Django session before resolving its cart.
    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key

    cart, _ = Cart.objects.get_or_create(
        session_key=session_key,
        user=None,
    )

    return cart


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_cart(request)

        return Response(
            CartSerializer(cart).data
        )

    def delete(self, request):
        cart = get_cart(request)

        cart.items.all().delete()

        return Response(
            CartSerializer(cart).data
        )


class CartItemView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        product = Product.objects.filter(
            pk=request.data.get("product_id"),
            is_active=True,
        ).first()

        if not product:
            return Response(
                {"detail": "Product not found."},
                status=404,
            )

        try:
            quantity = int(
                request.data.get("quantity", 1)
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": (
                        "Quantity must be a valid integer."
                    )
                },
                status=400,
            )

        if quantity < 1:
            return Response(
                {
                    "detail": (
                        "Quantity must be at least 1."
                    )
                },
                status=400,
            )

        cart = get_cart(request)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": 0,
            },
        )

        new_quantity = item.quantity + quantity

        if new_quantity > product.stock_quantity:
            return Response(
                {
                    "detail": (
                        f"Only {product.stock_quantity} "
                        "item(s) available."
                    )
                },
                status=400,
            )

        item.quantity = new_quantity
        item.save(
            update_fields=["quantity"]
        )

        return Response(
            CartSerializer(cart).data,
            status=201 if created else 200,
        )

    def patch(self, request):
        cart = get_cart(request)

        item = (
            CartItem.objects
            .filter(
                pk=request.data.get("item_id"),
                cart=cart,
            )
            .select_related("product")
            .first()
        )

        if not item:
            return Response(
                {
                    "detail": (
                        "Cart item not found."
                    )
                },
                status=404,
            )

        try:
            quantity = int(
                request.data.get("quantity", 0)
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": (
                        "Quantity must be a valid integer."
                    )
                },
                status=400,
            )

        if quantity <= 0:
            item.delete()

        elif quantity > item.product.stock_quantity:
            return Response(
                {
                    "detail": (
                        f"Only {item.product.stock_quantity} "
                        "item(s) available."
                    )
                },
                status=400,
            )

        else:
            item.quantity = quantity
            item.save(
                update_fields=["quantity"]
            )

        return Response(
            CartSerializer(cart).data
        )

    def delete(self, request):
        cart = get_cart(request)

        CartItem.objects.filter(
            pk=request.data.get("item_id"),
            cart=cart,
        ).delete()

        return Response(
            CartSerializer(cart).data
        )