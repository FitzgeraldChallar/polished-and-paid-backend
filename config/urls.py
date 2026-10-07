from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from catalog.views import CategoryViewSet, ProductViewSet
from accounts.views import RegisterView, LoginView, LogoutView, ProfileView, AddressViewSet, WishlistView
from cart.views import CartView, CartItemView
from orders.views import OrderViewSet, CheckoutView
from payments.views import CreateStripeCheckoutView, StripeWebhookView

router=DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('products', ProductViewSet, basename='product')
router.register('addresses', AddressViewSet, basename='address')
router.register('orders', OrderViewSet, basename='order')

urlpatterns=[
    path('admin/',admin.site.urls),
    path('api/',include(router.urls)),
    path('api/admin/', include('store_admin.urls')),
    path('api/auth/register/',RegisterView.as_view(),name='register'),
    path('api/auth/login/',LoginView.as_view(),name='login'),
    path('api/auth/logout/',LogoutView.as_view(),name='logout'),
    path('api/auth/profile/',ProfileView.as_view(),name='profile'),
    path('api/wishlist/',WishlistView.as_view(),name='wishlist'),
    path('api/wishlist/<int:product_id>/',WishlistView.as_view(),name='wishlist-item'),
    path('api/cart/',CartView.as_view(),name='cart'),
    path('api/cart/items/',CartItemView.as_view(),name='cart-items'),
    path('api/checkout/',CheckoutView.as_view(),name='checkout'),
    path('api/payments/stripe/create-checkout-session/',CreateStripeCheckoutView.as_view(),name='stripe-checkout'),
    path('api/payments/stripe/webhook/',StripeWebhookView.as_view(),name='stripe-webhook'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)