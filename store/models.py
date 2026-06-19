import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Product(TimeStampedModel):
    slug = models.SlugField(max_length=160, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, db_index=True)
    brand = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    primary_image = models.URLField(max_length=1000, blank=True)
    images = models.JSONField(default=list, blank=True)
    colors = models.JSONField(default=list, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    features = models.JSONField(default=list, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_on_sale = models.BooleanField(default=False, db_index=True)
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100)]
    )

    class Meta:
        ordering = ('-is_featured', '-created_at', 'name')
        indexes = [
            models.Index(fields=('category', 'brand')),
            models.Index(fields=('is_active', 'stock')),
        ]

    def __str__(self):
        return self.name

    @property
    def in_stock(self):
        return self.is_active and self.stock > 0


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(
        Product, related_name='variants', on_delete=models.CASCADE
    )
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=120)
    stock = models.PositiveIntegerField(default=0)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('product', 'code'), name='unique_product_variant_code'
            )
        ]

    def __str__(self):
        return f'{self.product.name} - {self.name}'


class Review(TimeStampedModel):
    product = models.ForeignKey(
        Product, related_name='reviews', on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='reviews', on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('product', 'user'), name='one_review_per_product_per_user'
            )
        ]


class CustomerProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name='customer_profile',
        on_delete=models.CASCADE,
    )
    phone = models.CharField(max_length=40, blank=True)
    avatar = models.TextField(blank=True)
    language = models.CharField(max_length=30, default='English')
    currency = models.CharField(max_length=8, default='USD')
    notify_orders = models.BooleanField(default=True)
    notify_promotions = models.BooleanField(default=False)
    notify_alerts = models.BooleanField(default=True)
    billing_name = models.CharField(max_length=200, blank=True)
    billing_address = models.TextField(blank=True)
    card_brand = models.CharField(max_length=30, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_expiry = models.CharField(max_length=5, blank=True)


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name='cart', on_delete=models.CASCADE
    )


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant, null=True, blank=True, on_delete=models.SET_NULL
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('cart', 'product', 'variant'), name='unique_cart_line'
            )
        ]


class WishlistItem(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='wishlist_items',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'product'), name='unique_wishlist_product'
            )
        ]


class RecentlyViewed(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='recently_viewed',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'product'), name='unique_recent_product'
            )
        ]
        ordering = ('-updated_at',)


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=24, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='orders',
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    email = models.EmailField()
    full_name = models.CharField(max_length=200)
    shipping_address = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, default='demo')
    payment_reference = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = f'TH-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    product_slug = models.CharField(max_length=160)
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=120, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class Notification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='notifications',
        on_delete=models.CASCADE,
    )
    message = models.CharField(max_length=500)
    kind = models.CharField(max_length=30, default='system')
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_at',)


class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=250)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_at',)
