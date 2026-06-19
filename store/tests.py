from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Cart, Product

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
