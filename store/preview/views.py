from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    Cart, ContactMessage, Notification, Order, Product, Review, WishlistItem,
)
from .forms import ProductForm, RegistrationForm

User = get_user_model()


def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    orders = Order.objects.all() if request.user.is_staff else request.user.orders.all()
    messages_count = ContactMessage.objects.count() if request.user.is_staff else 0
    context = {
        'total_products': Product.objects.count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'featured_products': Product.objects.filter(is_featured=True).count(),
        'orders_count': orders.count(),
        'customers_count': User.objects.count() if request.user.is_staff else 1,
        'messages_count': messages_count,
        'notifications_count': request.user.notifications.count(),
        'chats_count': 0,
        'recent_orders': orders.prefetch_related('items')[:5],
    }
    return render(request, 'dashboard.html', context)


def product_list(request):
    products = Product.objects.all().prefetch_related(
        Prefetch(
            'reviews',
            queryset=Review.objects.filter(is_approved=True).select_related('user'),
        ),
        'variants',
    )
    return render(request, 'products/product_list.html', {'products': products})


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.prefetch_related('variants', 'reviews__user'),
        pk=pk,
    )
    return render(request, 'products/product_detail.html', {'product': product})


@staff_member_required(login_url='preview-login')
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f'{product.name} was created successfully.')
        return redirect('preview-product-detail', pk=product.pk)
    return render(request, 'products/product_form.html', {'form': form})


@login_required
def order_list(request):
    orders = Order.objects.all() if request.user.is_staff else request.user.orders.all()
    return render(
        request,
        'orders/order_list.html',
        {'orders': orders.prefetch_related('items')},
    )


@login_required
def order_detail(request, pk):
    orders = Order.objects.all() if request.user.is_staff else request.user.orders.all()
    order = get_object_or_404(orders.prefetch_related('items'), pk=pk)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart = Cart.objects.prefetch_related(
        'items__product', 'items__variant'
    ).get(pk=cart.pk)
    cart_items = list(cart.items.all())
    for item in cart_items:
        item.preview_unit_price = (
            item.product.price
            + (item.variant.price_modifier if item.variant else 0)
        )
    subtotal = sum(
        item.preview_unit_price * item.quantity for item in cart_items
    )
    return render(
        request,
        'cart/cart_detail.html',
        {'cart': cart, 'cart_items': cart_items, 'subtotal': subtotal},
    )


@login_required
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    return render(request, 'wishlist/wishlist.html', {'wishlist_items': items})


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    return render(
        request,
        'notifications/notification_list.html',
        {'notifications': notifications},
    )


@staff_member_required(login_url='preview-login')
def contact_messages(request):
    return render(
        request,
        'contact/contact_messages.html',
        {'contact_messages': ContactMessage.objects.all()},
    )


@login_required
def chat_list(request):
    return render(
        request,
        'chat/chat_list.html',
        {
            'chats': (),
            'chat_persistence_available': False,
        },
    )


def register(request):
    if request.user.is_authenticated:
        return redirect('preview-dashboard')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Your preview account is ready.')
        return redirect('preview-dashboard')
    return render(request, 'accounts/register.html', {'form': form})
