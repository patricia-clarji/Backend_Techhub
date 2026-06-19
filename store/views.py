import json
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Cart, CartItem, ContactMessage, CustomerProfile, Notification, Order,
    OrderItem, Product, RecentlyViewed, Review, WishlistItem,
)
from .serializers import (
    CartItemWriteSerializer, CartSerializer, CheckoutSerializer,
    ContactMessageSerializer, NotificationSerializer, OrderSerializer,
    ProductSerializer, ProfileUpdateSerializer, ReviewSerializer,
    SignupSerializer, UserSerializer, cart_totals,
)


def token_payload(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }


class HealthView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({'status': 'ok', 'service': 'techhub-api'})


class SignupView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'auth'

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(token_payload(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'auth'

    def post(self, request):
        email = str(request.data.get('email', '')).lower().strip()
        password = request.data.get('password', '')
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {'detail': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(token_payload(user))


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        token = request.data.get('refresh')
        if token:
            try:
                RefreshToken(token).blacklist()
            except Exception:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        current = request.data.get('currentPassword', '')
        new = request.data.get('newPassword', '')
        if not request.user.check_password(current):
            return Response(
                {'currentPassword': ['Incorrect current password.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new) < 8:
            return Response(
                {'newPassword': ['Password must be at least 8 characters.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new)
        request.user.save(update_fields=('password',))
        return Response({'detail': 'Password updated.'})


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).prefetch_related(
            'variants', 'reviews__user'
        ).annotate(average_rating=Avg(
            'reviews__rating', filter=Q(reviews__is_approved=True)
        ))
        params = self.request.query_params
        search = params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(category__icontains=search) |
                Q(brand__icontains=search) |
                Q(description__icontains=search)
            )
        if params.get('category') and params['category'].lower() != 'all':
            queryset = queryset.filter(category__iexact=params['category'])
        if params.get('brand'):
            brands = [item.strip() for item in params.getlist('brand') if item.strip()]
            queryset = queryset.filter(brand__in=brands)
        if params.get('min_price'):
            queryset = queryset.filter(price__gte=params['min_price'])
        if params.get('max_price'):
            queryset = queryset.filter(price__lte=params['max_price'])
        if params.get('in_stock', '').lower() == 'true':
            queryset = queryset.filter(stock__gt=0)
        ordering = {
            'price-low': 'price',
            'price-high': '-price',
            'rating': '-average_rating',
            'newest': '-created_at',
            'featured': '-is_featured',
        }.get(params.get('sort'), '-is_featured')
        return queryset.order_by(ordering, 'name')

    @action(detail=False, methods=('get',))
    def facets(self, request):
        queryset = Product.objects.filter(is_active=True)
        return Response({
            'categories': ['All'] + list(
                queryset.order_by('category').values_list('category', flat=True).distinct()
            ),
            'brands': list(
                queryset.order_by('brand').values_list('brand', flat=True).distinct()
            ),
        })

    @action(
        detail=True, methods=('post',), permission_classes=(IsAuthenticated,),
        url_path='reviews',
    )
    def add_review(self, request, slug=None):
        product = self.get_object()
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response(
                {'detail': 'You have already reviewed this product.'},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(product=product, user=request.user)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=('post',), permission_classes=(IsAuthenticated,),
        url_path='viewed',
    )
    def mark_viewed(self, request, slug=None):
        product = self.get_object()
        item, _ = RecentlyViewed.objects.get_or_create(
            user=request.user, product=product
        )
        item.save()
        stale_ids = list(
            RecentlyViewed.objects.filter(user=request.user)
            .order_by('-updated_at').values_list('id', flat=True)[8:]
        )
        RecentlyViewed.objects.filter(id__in=stale_ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return Cart.objects.prefetch_related(
            'items__product__reviews__user', 'items__product__variants',
            'items__variant',
        ).get(pk=cart.pk)

    def get(self, request):
        return Response(CartSerializer(self.get_cart(request.user)).data)

    def post(self, request):
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = self.get_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=data['product'], variant=data['variant'],
            defaults={'quantity': data['quantity']},
        )
        if not created:
            new_quantity = item.quantity + data['quantity']
            available = item.variant.stock if item.variant else item.product.stock
            if new_quantity > available:
                return Response(
                    {'quantity': [f'Only {available} item(s) available.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.quantity = new_quantity
            item.save(update_fields=('quantity', 'updated_at'))
        return Response(
            CartSerializer(self.get_cart(request.user)).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        self.get_cart(request.user).items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request, pk):
        item = get_object_or_404(
            CartItem.objects.select_related('cart', 'product', 'variant'),
            pk=pk, cart__user=request.user,
        )
        try:
            quantity = int(request.data.get('quantity'))
        except (TypeError, ValueError):
            return Response(
                {'quantity': ['A valid quantity is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        available = item.variant.stock if item.variant else item.product.stock
        if quantity < 1 or quantity > available:
            return Response(
                {'quantity': [f'Quantity must be between 1 and {available}.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.quantity = quantity
        item.save(update_fields=('quantity', 'updated_at'))
        return Response(CartSerializer(item.cart).data)

    def delete(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        products = Product.objects.filter(
            wishlistitem__user=request.user, is_active=True
        ).prefetch_related('variants', 'reviews__user')
        return Response(ProductSerializer(products, many=True).data)

    def post(self, request):
        product = get_object_or_404(
            Product, slug=request.data.get('product_id'), is_active=True
        )
        item, created = WishlistItem.objects.get_or_create(
            user=request.user, product=product
        )
        if not created:
            item.delete()
        return Response({'wishlisted': created, 'productId': product.slug})

    def delete(self, request):
        WishlistItem.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecentlyViewedView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        product_ids = RecentlyViewed.objects.filter(user=request.user).values_list(
            'product_id', flat=True
        )[:8]
        products = {p.pk: p for p in Product.objects.filter(pk__in=product_ids)}
        ordered = [products[pk] for pk in product_ids if pk in products]
        return Response(ProductSerializer(ordered, many=True).data)

    def delete(self, request):
        RecentlyViewed.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart.objects.select_for_update().prefetch_related(
            'items__product', 'items__variant'
        ).filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response(
                {'detail': 'Your cart is empty.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = list(cart.items.all())
        for item in items:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            variant = None
            if item.variant_id:
                variant = product.variants.select_for_update().get(pk=item.variant_id)
            available = variant.stock if variant else product.stock
            if item.quantity > available:
                return Response(
                    {'detail': f'{product.name} only has {available} available.'},
                    status=status.HTTP_409_CONFLICT,
                )

        subtotal, discount, total = cart_totals(cart)
        shipping = Decimal('0') if total >= Decimal('500') else Decimal('25')
        data = serializer.validated_data
        order = Order.objects.create(
            user=request.user,
            email=data['email'],
            full_name=data['fullName'],
            shipping_address=data['address'],
            subtotal=subtotal,
            discount_total=discount,
            shipping_total=shipping,
            total=total + shipping,
            payment_method=data['paymentMethod'],
            status=Order.Status.PROCESSING,
        )
        for item in items:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            variant = None
            if item.variant_id:
                variant = product.variants.select_for_update().get(pk=item.variant_id)
                variant.stock -= item.quantity
                variant.save(update_fields=('stock', 'updated_at'))
            else:
                product.stock -= item.quantity
                product.save(update_fields=('stock', 'updated_at'))
            unit = product.price + (
                variant.price_modifier if variant else Decimal('0')
            )
            OrderItem.objects.create(
                order=order, product=product, product_slug=product.slug,
                product_name=product.name,
                variant_name=variant.name if variant else '',
                quantity=item.quantity, unit_price=unit,
                line_total=unit * item.quantity,
            )
        cart.items.all().delete()
        Notification.objects.create(
            user=request.user, kind='order',
            message=f'Order {order.number} was placed successfully.',
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = 'number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class NotificationView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = Notification.objects.filter(user=request.user)
        return Response({
            'notifications': NotificationSerializer(queryset, many=True).data,
            'unreadCount': queryset.filter(is_read=False).count(),
        })

    def patch(self, request):
        queryset = Notification.objects.filter(user=request.user)
        notification_id = request.data.get('id')
        if notification_id:
            queryset = queryset.filter(pk=notification_id)
        queryset.update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        Notification.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'contact'

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        send_mail(
            f'TechHub contact: {message.subject}',
            f'From: {message.name} <{message.email}>\n\n{message.message}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.SUPPORT_EMAIL],
            fail_silently=True,
        )
        return Response(
            ContactMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )


class ChatView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'chat'

    def post(self, request):
        prompt = str(request.data.get('message', '')).strip()
        history = request.data.get('history', [])[-6:]
        if not prompt:
            return Response(
                {'message': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        products = Product.objects.filter(is_active=True)[:50]
        catalog = '\n'.join(
            f'{p.name} (${p.price}): {p.description}; features: '
            f'{", ".join(p.features)}' for p in products
        )
        if not settings.OPENROUTER_API_KEY:
            matches = Product.objects.filter(
                Q(name__icontains=prompt) | Q(category__icontains=prompt) |
                Q(brand__icontains=prompt), is_active=True
            )[:3]
            if matches:
                names = ', '.join(f'**{p.name}** (${p.price})' for p in matches)
                return Response({'message': f'You may like {names}.', 'provider': 'local'})
            return Response({
                'message': (
                    'I can help with product recommendations, comparisons, deals, '
                    'and shipping. Try asking about a category or brand.'
                ),
                'provider': 'local',
            })
        payload = json.dumps({
            'model': settings.OPENROUTER_MODEL,
            'temperature': 0.7,
            'messages': [{
                'role': 'system',
                'content': (
                    'You are TechHub Concierge. Be concise, polished, and accurate. '
                    'Only recommend products in the catalog. Free shipping applies '
                    f'at $500.\n\nCatalog:\n{catalog}'
                ),
            }, *history, {'role': 'user', 'content': prompt}],
        }).encode()
        upstream = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=payload,
            headers={
                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'TechHub Concierge',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(upstream, timeout=30) as response:
                result = json.loads(response.read())
            return Response({
                'message': result['choices'][0]['message']['content'],
                'provider': 'openrouter',
            })
        except (urllib.error.URLError, KeyError, ValueError):
            return Response(
                {'detail': 'The concierge is temporarily unavailable.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
