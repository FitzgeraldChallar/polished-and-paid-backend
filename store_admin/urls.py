from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminLoginView, AdminLogoutView, AdminMeView, dashboard,
    AdminCategoryViewSet, AdminProductViewSet, AdminOrderViewSet,
    AdminCustomerViewSet, AdminPaymentViewSet, AdminInventoryViewSet,
)

router = DefaultRouter()
router.register('categories', AdminCategoryViewSet, basename='admin-category')
router.register('products', AdminProductViewSet, basename='admin-product')
router.register('orders', AdminOrderViewSet, basename='admin-order')
router.register('customers', AdminCustomerViewSet, basename='admin-customer')
router.register('payments', AdminPaymentViewSet, basename='admin-payment')
router.register('inventory', AdminInventoryViewSet, basename='admin-inventory')

urlpatterns = [
    path('auth/login/', AdminLoginView.as_view(), name='admin-login'),
    path('auth/logout/', AdminLogoutView.as_view(), name='admin-logout'),
    path('auth/me/', AdminMeView.as_view(), name='admin-me'),
    path('dashboard/', dashboard, name='admin-dashboard'),
    path('', include(router.urls)),
]
