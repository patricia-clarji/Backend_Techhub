from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='preview-home'),
    path('dashboard/', views.dashboard, name='preview-dashboard'),
    path('products/', views.product_list, name='preview-product-list'),
    path(
        'products/new/',
        views.product_create,
        name='preview-product-create',
    ),
    path(
        'products/<int:pk>/',
        views.product_detail,
        name='preview-product-detail',
    ),
    path('orders/', views.order_list, name='preview-order-list'),
    path(
        'orders/<uuid:pk>/',
        views.order_detail,
        name='preview-order-detail',
    ),
    path('cart/', views.cart_detail, name='preview-cart'),
    path('wishlist/', views.wishlist, name='preview-wishlist'),
    path(
        'notifications/',
        views.notification_list,
        name='preview-notifications',
    ),
    path(
        'contact-messages/',
        views.contact_messages,
        name='preview-contact-messages',
    ),
    path('chats/', views.chat_list, name='preview-chats'),
    path(
        'login/',
        LoginView.as_view(
            template_name='accounts/login.html',
            redirect_authenticated_user=True,
        ),
        name='preview-login',
    ),
    path('logout/', LogoutView.as_view(), name='preview-logout'),
    path('register/', views.register, name='preview-register'),
]
