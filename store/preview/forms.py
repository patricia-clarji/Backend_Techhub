from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Q

from ..models import Cart, CustomerProfile, Product

User = get_user_model()


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            'slug', 'name', 'category', 'brand', 'price', 'description',
            'primary_image', 'images', 'colors', 'specifications', 'features',
            'stock', 'is_active', 'is_featured', 'is_on_sale',
            'discount_percent',
        )


class RegistrationForm(UserCreationForm):
    name = forms.CharField(max_length=200)
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        name = self.cleaned_data['name'].strip().split(maxsplit=1)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = name[0] if name else ''
        user.last_name = name[1] if len(name) > 1 else ''
        if commit:
            user.save()
            CustomerProfile.objects.get_or_create(user=user)
            Cart.objects.get_or_create(user=user)
        return user
