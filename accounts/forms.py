from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    UserChangeForm
)
from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Login",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Loginni kiriting",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Parol",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Parolni kiriting",
            }
        ),
    )

    error_messages = {
        "invalid_login": "Login yoki parol noto‘g‘ri.",
        "inactive": "Bu akkaunt bloklangan.",
    }


class CustomUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "phone",
            "role",
            "store",
        )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"