from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Cart, CartItem, Product, Review

User = get_user_model()


class StoreApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            password='StrongPass123!',
        )
        Cart.objects.create(user=self.user)
        self.product = Product.objects.create(
            slug='test-device', name='Test Device', category='Testing',
            brand='TechHub', price=100, stock=5, is_active=True,
            is_on_sale=True, discount_percent=20,
        )

    def authenticate(self):
        response = self.client.post(reverse('login'), {
            'email': 'buyer@example.com', 'password': 'StrongPass123!',
        })
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_health_and_catalog_are_public(self):
        self.assertEqual(self.client.get(reverse('health')).status_code, 200)
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['id'], 'test-device')

    def test_signup_returns_tokens_and_safe_user(self):
        response = self.client.post(reverse('signup'), {
            'name': 'New Buyer',
            'email': 'new@example.com',
            'password': 'AnotherPass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertNotIn('password', response.data['user'])

    def test_signup_uses_django_password_validation(self):
        response = self.client.post(reverse('signup'), {
            'name': 'New Buyer',
            'email': 'weak@example.com',
            'password': 'password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_cart_and_checkout_use_server_prices(self):
        self.authenticate()
        response = self.client.post(reverse('cart'), {
            'product_id': self.product.slug, 'quantity': 2,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['subtotal'], 200.0)
        self.assertEqual(response.data['discountTotal'], 40.0)

        response = self.client.post(reverse('checkout'), {
            'fullName': 'Test Buyer',
            'email': 'buyer@example.com',
            'address': '123 Test Street',
            'paymentMethod': 'demo',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['total']), 185.0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_review_is_limited_to_one_per_user(self):
        self.authenticate()
        url = f'/api/products/{self.product.slug}/reviews/'
        first = self.client.post(url, {'rating': 5, 'comment': 'Excellent'})
        second = self.client.post(url, {'rating': 4, 'comment': 'Again'})
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)

    def test_catalog_rejects_invalid_price_filters(self):
        response = self.client.get('/api/products/?min_price=invalid')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('min_price', response.data)

    def test_catalog_hides_unapproved_reviews(self):
        Review.objects.create(
            product=self.product,
            user=self.user,
            rating=1,
            comment='Pending moderation',
            is_approved=False,
        )
        response = self.client.get(f'/api/products/{self.product.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reviews'], [])
        self.assertEqual(response.data['averageRating'], 0.0)

    def test_logout_requires_a_valid_refresh_token(self):
        self.authenticate()
        response = self.client.post(reverse('logout'), {'refresh': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_update_validates_nested_notification_booleans(self):
        self.authenticate()
        response = self.client.patch(
            reverse('me'),
            {'notifications': {'orders': 'false'}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['notifications']['orders'])

    def test_profile_update_does_not_partially_save_invalid_billing(self):
        self.authenticate()
        response = self.client.patch(
            reverse('me'),
            {
                'name': 'Changed Name',
                'billing': {'cardNumber': '123'},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, '')
        self.assertEqual(self.user.last_name, '')

    def test_checkout_rejects_product_deactivated_after_cart_add(self):
        self.authenticate()
        CartItem.objects.create(
            cart=self.user.cart,
            product=self.product,
            quantity=1,
        )
        self.product.is_active = False
        self.product.save(update_fields=('is_active',))
        response = self.client.post(reverse('checkout'), {
            'fullName': 'Test Buyer',
            'email': 'buyer@example.com',
            'address': '123 Test Street',
            'paymentMethod': 'demo',
        })
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_chat_rejects_oversized_messages(self):
        response = self.client.post(
            reverse('chat'),
            {'message': 'x' * 4001},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PreviewViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='preview@example.com',
            email='preview@example.com',
            password='StrongPass123!',
        )
        Cart.objects.create(user=self.user)
        self.product = Product.objects.create(
            slug='preview-device',
            name='Preview Device',
            category='Testing',
            brand='TechHub',
            price=100,
            stock=5,
        )

    def test_public_preview_routes_do_not_conflict_with_api_routes(self):
        self.assertEqual(
            self.client.get(reverse('preview-home')).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(reverse('preview-product-list')).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(reverse('health')).status_code,
            status.HTTP_200_OK,
        )

    def test_private_preview_routes_require_session_login(self):
        response = self.client.get(reverse('preview-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn(reverse('preview-login'), response.url)

        self.client.login(
            username=self.user.username,
            password='StrongPass123!',
        )
        self.assertEqual(
            self.client.get(reverse('preview-dashboard')).status_code,
            status.HTTP_200_OK,
        )

    def test_staff_preview_routes_reject_non_staff_users(self):
        self.client.login(
            username=self.user.username,
            password='StrongPass123!',
        )
        response = self.client.get(reverse('preview-contact-messages'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        self.user.is_staff = True
        self.user.save(update_fields=('is_staff',))
        self.assertEqual(
            self.client.get(reverse('preview-contact-messages')).status_code,
            status.HTTP_200_OK,
        )
