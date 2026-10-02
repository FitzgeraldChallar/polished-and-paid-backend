from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from rest_framework import serializers, status, viewsets
from rest_framework.authentication import (
    TokenAuthentication,
    SessionAuthentication,
)
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    authentication_classes,
    parser_classes,
)
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
    JSONParser,
)
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter, OrderingFilter

from catalog.models import Category, Product, ProductImage
from orders.models import Order, OrderItem
from payments.models import Payment
from inventory.models import InventoryTransaction


User = get_user_model()


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

class AdminLoginSerializer(serializers.Serializer):
    """
    Login serializer for the dedicated Next.js admin portal.

    The admin portal intentionally uses:

        Email + Password

    rather than:

        Username + Password
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
        ]


class AdminLoginView(APIView):
    """
    POST /api/admin/login/

    Authenticates an administrator using EMAIL + PASSWORD.

    Important:
    Django's standard authentication backend normally expects
    the username. Our admin portal uses the administrator's
    email address instead, so we explicitly resolve the user
    by email before checking the password.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "detail": "Please provide a valid email address and password.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        # ----------------------------------------------------
        # Find the administrator by email.
        #
        # iexact makes the login case-insensitive:
        #
        # Admin@Example.com
        # admin@example.com
        #
        # will resolve to the same account.
        # ----------------------------------------------------
        user = (
            User.objects
            .filter(email__iexact=email)
            .first()
        )

        # Never reveal whether the email or password was wrong.
        if not user:
            return Response(
                {
                    "detail": "Invalid administrator credentials."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ----------------------------------------------------
        # Account must be active.
        # ----------------------------------------------------
        if not user.is_active:
            return Response(
                {
                    "detail": "This administrator account is inactive."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # Account must have staff/admin privileges.
        # ----------------------------------------------------
        if not user.is_staff:
            return Response(
                {
                    "detail": "You do not have permission to access the admin portal."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # Verify password.
        # ----------------------------------------------------
        if not user.check_password(password):
            return Response(
                {
                    "detail": "Invalid administrator credentials."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ----------------------------------------------------
        # Create or retrieve API token.
        # ----------------------------------------------------
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminMeView(APIView):
    """
    GET /api/admin/me/

    Returns the currently authenticated administrator.
    """

    permission_classes = [IsAdminUser]
    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    def get(self, request):
        return Response(
            AdminUserSerializer(request.user).data
        )


class AdminLogoutView(APIView):
    """
    POST /api/admin/logout/

    Invalidates the administrator's API token.
    """

    permission_classes = [IsAdminUser]
    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    def post(self, request):
        Token.objects.filter(
            user=request.user
        ).delete()

        return Response(
            {
                "detail": "Logged out successfully."
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CATEGORIES
# ============================================================

class AdminCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(
        read_only=True
    )

    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
        ]


class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = (
        Category.objects
        .all()
        .annotate(
            product_count=Count("products")
        )
    )

    serializer_class = AdminCategorySerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "slug",
        "description",
    ]

    ordering_fields = [
        "name",
        "sort_order",
        "created_at",
    ]


# ============================================================
# PRODUCT IMAGES
# ============================================================

class AdminProductImageSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductImage
        fields = "__all__"

        read_only_fields = [
            "id",
        ]


# ============================================================
# PRODUCTS
# ============================================================

class AdminProductSerializer(serializers.ModelSerializer):
    images = AdminProductImageSerializer(
        many=True,
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    current_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    in_stock = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "category_name",
            "description",
            "short_description",
            "price",
            "sale_price",
            "current_price",
            "stock_quantity",
            "in_stock",
            "low_stock_threshold",
            "featured",
            "is_new",
            "bestseller",
            "is_active",
            "weight",
            "images",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "sku",
            "current_price",
            "in_stock",
            "created_at",
            "updated_at",
        ]


class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects
        .all()
        .select_related("category")
        .prefetch_related("images")
    )

    serializer_class = AdminProductSerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "sku",
        "description",
        "short_description",
        "category__name",
    ]

    ordering_fields = [
        "name",
        "price",
        "sale_price",
        "stock_quantity",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_at"
    ]

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def images(self, request, pk=None):
        product = self.get_object()

        image_file = request.FILES.get("image")
        image_url = request.data.get(
            "image_url",
            "",
        )

        if not image_file and not image_url:
            return Response(
                {
                    "detail": "Provide an image file or image_url."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminProductImageSerializer(
            data={
                "image": image_file,
                "image_url": image_url,
                "alt_text": request.data.get(
                    "alt_text",
                    product.name,
                ),
                "is_primary": str(
                    request.data.get(
                        "is_primary",
                        "",
                    )
                ).lower()
                in ("1", "true", "yes"),
                "sort_order": request.data.get(
                    "sort_order",
                    0,
                ),
                "product": product.pk,
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        image = serializer.save(
            product=product
        )

        if image.is_primary:
            product.images.exclude(
                pk=image.pk
            ).update(
                is_primary=False
            )

        return Response(
            AdminProductImageSerializer(image).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"images/(?P<image_id>[^/.]+)",
    )
    def delete_image(
        self,
        request,
        pk=None,
        image_id=None,
    ):
        product = self.get_object()

        image = (
            product.images
            .filter(pk=image_id)
            .first()
        )

        if not image:
            return Response(
                {
                    "detail": "Image not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        image.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


# ============================================================
# ORDERS
# ============================================================

class AdminOrderItemSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = OrderItem

        fields = [
            "id",
            "product",
            "product_name",
            "sku",
            "quantity",
            "unit_price",
            "line_total",
        ]


class AdminOrderSerializer(serializers.ModelSerializer):
    items = AdminOrderItemSerializer(
        many=True,
        read_only=True,
    )

    customer_name = serializers.SerializerMethodField()

    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order

        fields = [
            "id",
            "order_number",
            "user",
            "status",
            "email",
            "first_name",
            "last_name",
            "shipping_line1",
            "shipping_line2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "shipping_phone",
            "subtotal",
            "shipping_fee",
            "tax",
            "total",
            "currency",
            "notes",
            "created_at",
            "updated_at",
            "items",
            "customer_name",
            "payment_status",
        ]

        read_only_fields = [
            "id",
            "order_number",
            "created_at",
            "updated_at",
            "items",
            "customer_name",
            "payment_status",
        ]

    def get_customer_name(self, obj):
        return (
            f"{obj.first_name} "
            f"{obj.last_name}"
        ).strip()

    def get_payment_status(self, obj):
        payment = getattr(
            obj,
            "payment",
            None,
        )

        return getattr(
            payment,
            "status",
            "unpaid",
        )


class AdminOrderViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        Order.objects
        .all()
        .select_related(
            "user",
            "payment",
        )
        .prefetch_related("items")
    )

    serializer_class = AdminOrderSerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "order_number",
        "email",
        "first_name",
        "last_name",
        "shipping_city",
    ]

    ordering_fields = [
        "created_at",
        "total",
        "status",
    ]

    ordering = [
        "-created_at"
    ]

    @action(
        detail=True,
        methods=["post"],
    )
    @transaction.atomic
    def status(
        self,
        request,
        pk=None,
    ):
        order = self.get_object()

        new_status = request.data.get(
            "status"
        )

        allowed = {
            choice[0]
            for choice in Order.STATUS_CHOICES
        }

        if new_status not in allowed:
            return Response(
                {
                    "detail": "Invalid order status."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return Response(
            self.get_serializer(order).data
        )


# ============================================================
# CUSTOMERS
# ============================================================

class AdminCustomerSerializer(
    serializers.ModelSerializer
):
    order_count = serializers.IntegerField(
        read_only=True
    )

    total_spent = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "order_count",
            "total_spent",
        ]


class AdminCustomerViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        User.objects
        .filter(is_staff=False)
        .annotate(
            order_count=Count(
                "orders"
            ),
            total_spent=Sum(
                "orders__total",
                filter=Q(
                    orders__status__in=[
                        "paid",
                        "processing",
                        "shipped",
                        "delivered",
                    ]
                ),
            ),
        )
    )

    serializer_class = AdminCustomerSerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
    ]

    ordering = [
        "-date_joined"
    ]


# ============================================================
# PAYMENTS
# ============================================================

class AdminPaymentSerializer(
    serializers.ModelSerializer
):
    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )

    customer_email = serializers.EmailField(
        source="order.email",
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = "__all__"


class AdminPaymentViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        Payment.objects
        .all()
        .select_related("order")
    )

    serializer_class = AdminPaymentSerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "order__order_number",
        "order__email",
        "stripe_payment_intent_id",
        "stripe_checkout_session_id",
    ]

    ordering = [
        "-created_at"
    ]


# ============================================================
# INVENTORY
# ============================================================

class AdminInventorySerializer(
    serializers.ModelSerializer
):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )

    class Meta:
        model = InventoryTransaction

        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
        ]


class AdminInventoryViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        InventoryTransaction.objects
        .all()
        .select_related("product")
    )

    serializer_class = AdminInventorySerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]

    ordering = [
        "-created_at"
    ]

    @action(
        detail=False,
        methods=["post"],
    )
    @transaction.atomic
    def adjust(
        self,
        request,
    ):
        product_id = request.data.get(
            "product_id"
        )

        quantity = request.data.get(
            "quantity"
        )

        transaction_type = request.data.get(
            "transaction_type",
            "adjustment",
        )

        note = request.data.get(
            "note",
            "",
        )

        if product_id is None or quantity is None:
            return Response(
                {
                    "detail": (
                        "product_id and quantity "
                        "are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quantity = int(quantity)

        except (
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "detail": (
                        "quantity must be an integer."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            transaction_type
            not in dict(
                InventoryTransaction.TYPES
            )
        ):
            return Response(
                {
                    "detail": (
                        "Invalid transaction_type."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = (
            Product.objects
            .select_for_update()
            .filter(pk=product_id)
            .first()
        )

        if not product:
            return Response(
                {
                    "detail": "Product not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if transaction_type in (
            "restock",
            "return",
        ):
            delta = abs(quantity)

        elif transaction_type == "sale":
            delta = -abs(quantity)

        else:
            delta = quantity

        new_stock = (
            product.stock_quantity
            + delta
        )

        if new_stock < 0:
            return Response(
                {
                    "detail": (
                        "Stock cannot be negative."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        product.stock_quantity = new_stock

        product.save(
            update_fields=[
                "stock_quantity",
                "updated_at",
            ]
        )

        record = (
            InventoryTransaction.objects.create(
                product=product,
                transaction_type=transaction_type,
                quantity=delta,
                note=note,
            )
        )

        return Response(
            AdminInventorySerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@api_view(["GET"])
@authentication_classes([
    TokenAuthentication,
    SessionAuthentication,
])
@permission_classes([IsAdminUser])
def dashboard(request):
    today = timezone.localdate()

    orders = Order.objects.all()

    products = Product.objects.all()

    paid_statuses = [
        "paid",
        "processing",
        "shipped",
        "delivered",
    ]

    revenue = (
        orders
        .filter(
            status__in=paid_statuses
        )
        .aggregate(
            value=Sum("total")
        )["value"]
        or Decimal("0.00")
    )

    today_revenue = (
        orders
        .filter(
            created_at__date=today,
            status__in=paid_statuses,
        )
        .aggregate(
            value=Sum("total")
        )["value"]
        or Decimal("0.00")
    )

    low_stock = (
        products
        .filter(
            is_active=True,
            stock_quantity__lte=F(
                "low_stock_threshold"
            ),
        )
        .count()
    )

    return Response(
        {
            "revenue": revenue,
            "today_revenue": today_revenue,
            "orders": orders.count(),
            "pending_orders": orders.filter(
                status="pending"
            ).count(),
            "processing_orders": orders.filter(
                status="processing"
            ).count(),
            "products": products.count(),
            "active_products": products.filter(
                is_active=True
            ).count(),
            "low_stock_products": low_stock,
            "customers": User.objects.filter(
                is_staff=False
            ).count(),
            "paid_orders": orders.filter(
                status__in=paid_statuses
            ).count(),
        }
    )