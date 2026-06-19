from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Avg
from rest_framework import serializers

from .models import (
    Cart, CartItem, ContactMessage, CustomerProfile, Notification, Order,
    OrderItem, Product, ProductVariant, RecentlyViewed, Review, WishlistItem,
)

User = get_user_model()


class ReviewSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user_id', read_only=True)
    userName = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'userId', 'userName', 'rating', 'comment', 'date')
        read_only_fields = ('id', 'userId', 'userName', 'date')

    def get_userName(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='code')
    priceMod = serializers.DecimalField(
        source='price_modifier', max_digits=10, decimal_places=2, coerce_to_string=False
    )

    class Meta:
        model = ProductVariant
        fields = ('id', 'name', 'stock', 'priceMod')


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='slug')
    desc = serializers.CharField(source='description')
    img = serializers.URLField(source='primary_image', allow_blank=True)
    inStock = serializers.BooleanField(source='in_stock', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')
    averageRating = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)
    discountPercent = serializers.IntegerField(source='discount_percent', read_only=True)
    isOnSale = serializers.BooleanField(source='is_on_sale', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'category', 'brand', 'price', 'rating', 'averageRating',
            'inStock', 'reviews', 'createdAt', 'img', 'images', 'colors',
            'variants', 'specifications', 'stock', 'desc', 'features',
            'discountPercent', 'isOnSale',
        )

    def get_averageRating(self, obj):
        value = getattr(obj, 'average_rating', None)
        if value is None:
            value = obj.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))['avg']
        return round(float(value or 0), 1)

    def get_rating(self, obj):
        return self.get_averageRating(obj)


class ProfileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email')
    preferences = serializers.SerializerMethodField()
    billing = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile
        fields = (
            'name', 'email', 'phone', 'avatar', 'preferences', 'billing',
            'notifications',
        )

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_preferences(self, obj):
        return {
            'language': obj.language,
            'currency': obj.currency,
            'notifications': self.get_notifications(obj),
        }

    def get_notifications(self, obj):
        return {
            'orders': obj.notify_orders,
            'promotions': obj.notify_promotions,
            'alerts': obj.notify_alerts,
        }

    def get_billing(self, obj):
        return {
            'cardName': obj.billing_name,
            'cardNumber': f'**** **** **** {obj.card_last4}' if obj.card_last4 else '',
            'expiry': obj.card_expiry,
            'cvv': '',
            'address': obj.billing_address,
            'cardBrand': obj.card_brand,
        }


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='customer_profile.phone', read_only=True)
    avatar = serializers.CharField(source='customer_profile.avatar', read_only=True)
    preferences = serializers.SerializerMethodField()
    billing = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'name', 'email', 'phone', 'avatar', 'preferences', 'billing',
            'notifications',
        )

    def get_name(self, obj):
        return obj.get_full_name() or obj.username

    def _profile(self, obj):
        profile, _ = CustomerProfile.objects.get_or_create(user=obj)
        return ProfileSerializer(profile).data

    def get_preferences(self, obj):
        return self._profile(obj)['preferences']

    def get_billing(self, obj):
        return self._profile(obj)['billing']

    def get_notifications(self, obj):
        return self._profile(obj)['notifications']


class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def create(self, validated_data):
        name = validated_data.pop('name').strip()
        email = validated_data.pop('email')
        user = User.objects.create_user(
            username=email, email=email, password=validated_data['password']
        )
        parts = name.split(maxsplit=1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.save(update_fields=('first_name', 'last_name'))
        CustomerProfile.objects.create(user=user)
        Cart.objects.create(user=user)
        return user


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    avatar = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferences = serializers.DictField(required=False)
    notifications = serializers.DictField(required=False)
    billing = serializers.DictField(required=False)

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value.lower().strip()

    def update(self, user, validated_data):
        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        if 'name' in validated_data:
            parts = validated_data['name'].strip().split(maxsplit=1)
            user.first_name = parts[0] if parts else ''
            user.last_name = parts[1] if len(parts) > 1 else ''
        if 'email' in validated_data:
            user.email = validated_data['email']
            user.username = validated_data['email']
        user.save()

        for field in ('phone', 'avatar'):
            if field in validated_data:
                setattr(profile, field, validated_data[field] or '')

        prefs = validated_data.get('preferences', {})
        if 'language' in prefs:
            profile.language = prefs['language']
        if 'currency' in prefs:
            profile.currency = prefs['currency']

        notifications = validated_data.get(
            'notifications', prefs.get('notifications', {})
        )
        mapping = {
            'orders': 'notify_orders',
            'promotions': 'notify_promotions',
            'alerts': 'notify_alerts',
        }
        for source, target in mapping.items():
            if source in notifications:
                setattr(profile, target, bool(notifications[source]))

        billing = validated_data.get('billing', {})
        if billing:
            profile.billing_name = billing.get('cardName', profile.billing_name)
            profile.billing_address = billing.get('address', profile.billing_address)
            profile.card_expiry = billing.get('expiry', profile.card_expiry)
            number = ''.join(filter(str.isdigit, billing.get('cardNumber', '')))
            if number:
                if len(number) < 12:
                    raise serializers.ValidationError(
                        {'billing': 'Card number is invalid.'}
                    )
                profile.card_last4 = number[-4:]
                profile.card_brand = detect_card_brand(number)
        profile.save()
        return user


def detect_card_brand(number):
    if number.startswith('4'):
        return 'Visa'
    if number[:2] in {'51', '52', '53', '54', '55'}:
        return 'Mastercard'
    if number.startswith(('34', '37')):
        return 'American Express'
    return 'Card'


class CartItemWriteSerializer(serializers.Serializer):
    product_id = serializers.SlugRelatedField(
        slug_field='slug', queryset=Product.objects.filter(is_active=True)
    )
    variant_id = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)

    def validate(self, attrs):
        product = attrs['product_id']
        variant_code = attrs.get('variant_id')
        variant = None
        if variant_code:
            try:
                variant = product.variants.get(code=variant_code)
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({'variant_id': 'Invalid variant.'})
        available = variant.stock if variant else product.stock
        if attrs['quantity'] > available:
            raise serializers.ValidationError(
                {'quantity': f'Only {available} item(s) available.'}
            )
        attrs['product'] = product
        attrs['variant'] = variant
        return attrs


class CartItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    product = ProductSerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    quantity = serializers.IntegerField()
    unitPrice = serializers.SerializerMethodField()
    lineTotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'variant', 'quantity', 'unitPrice', 'lineTotal')

    def get_unitPrice(self, obj):
        return float(obj.product.price + (obj.variant.price_modifier if obj.variant else 0))

    def get_lineTotal(self, obj):
        return round(self.get_unitPrice(obj) * obj.quantity, 2)


def cart_totals(cart):
    subtotal = Decimal('0')
    discount = Decimal('0')
    for item in cart.items.select_related('product', 'variant'):
        unit = item.product.price + (
            item.variant.price_modifier if item.variant else Decimal('0')
        )
        line = unit * item.quantity
        subtotal += line
        if item.product.is_on_sale:
            discount += line * Decimal(item.product.discount_percent) / Decimal('100')
    return subtotal, discount, subtotal - discount


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    discountTotal = serializers.SerializerMethodField()
    totalAmount = serializers.SerializerMethodField()
    itemCount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('items', 'subtotal', 'discountTotal', 'totalAmount', 'itemCount')

    def get_subtotal(self, obj):
        return float(cart_totals(obj)[0])

    def get_discountTotal(self, obj):
        return float(cart_totals(obj)[1])

    def get_totalAmount(self, obj):
        return float(cart_totals(obj)[2])

    def get_itemCount(self, obj):
        return sum(item.quantity for item in obj.items.all())


class OrderItemSerializer(serializers.ModelSerializer):
    productId = serializers.CharField(source='product_slug')
    productName = serializers.CharField(source='product_name')
    variantName = serializers.CharField(source='variant_name')
    unitPrice = serializers.DecimalField(
        source='unit_price', max_digits=12, decimal_places=2, coerce_to_string=False
    )
    lineTotal = serializers.DecimalField(
        source='line_total', max_digits=12, decimal_places=2, coerce_to_string=False
    )

    class Meta:
        model = OrderItem
        fields = (
            'productId', 'productName', 'variantName', 'quantity',
            'unitPrice', 'lineTotal',
        )


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    orderId = serializers.CharField(source='number')
    createdAt = serializers.DateTimeField(source='created_at')
    discountTotal = serializers.DecimalField(
        source='discount_total', max_digits=12, decimal_places=2,
        coerce_to_string=False,
    )
    shippingTotal = serializers.DecimalField(
        source='shipping_total', max_digits=12, decimal_places=2,
        coerce_to_string=False,
    )
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'orderId', 'status', 'email', 'full_name', 'shipping_address',
            'subtotal', 'discountTotal', 'shippingTotal', 'total', 'createdAt',
            'items',
        )


class CheckoutSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    address = serializers.CharField(max_length=2000)
    paymentMethod = serializers.ChoiceField(
        choices=('demo', 'cash_on_delivery'), default='demo'
    )


class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='kind')
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')
    read = serializers.BooleanField(source='is_read')

    class Meta:
        model = Notification
        fields = ('id', 'message', 'type', 'date', 'read')


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ('id', 'name', 'email', 'subject', 'message', 'created_at')
        read_only_fields = ('id', 'created_at')
