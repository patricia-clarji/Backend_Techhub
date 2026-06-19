from django.contrib import admin

from .models import (
    Cart, CartItem, ContactMessage, CustomerProfile, Notification, Order,
    OrderItem, Product, ProductVariant, RecentlyViewed, Review, WishlistItem,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('user', 'rating', 'comment', 'created_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'brand', 'price', 'stock', 'is_active',
        'is_featured', 'is_on_sale',
    )
    list_filter = ('is_active', 'is_featured', 'is_on_sale', 'category', 'brand')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (ProductVariantInline, ReviewInline)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        'product', 'product_name', 'variant_name', 'quantity', 'unit_price',
        'line_total',
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'full_name', 'email', 'status', 'total', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('number', 'email', 'full_name')
    readonly_fields = (
        'number', 'user', 'subtotal', 'discount_total', 'shipping_total',
        'total', 'created_at', 'updated_at',
    )
    inlines = (OrderItemInline,)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')


admin.site.register(CustomerProfile)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(RecentlyViewed)
admin.site.register(Notification)
