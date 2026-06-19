from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CartItemView, CartView, ChangePasswordView, ChatView, CheckoutView,
    ContactView, HealthView, LoginView, LogoutView, MeView, NotificationView,
    OrderViewSet, ProductViewSet, RecentlyViewedView, SignupView, WishlistView,
)

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', HealthView.as_view(), name='health'),
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/<int:pk>/', CartItemView.as_view(), name='cart-item'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('recently-viewed/', RecentlyViewedView.as_view(), name='recently-viewed'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('notifications/', NotificationView.as_view(), name='notifications'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('chat/', ChatView.as_view(), name='chat'),
]
