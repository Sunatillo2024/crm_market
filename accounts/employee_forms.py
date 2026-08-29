from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class CashierCreateForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Ism",
        max_length=150,
        required=True,
    )

    last_name = forms.CharField(
        label="Familiya",
        max_length=150,
        required=False,
    )

    username = forms.CharField(
        label="Login",
        min_length=3,
        max_length=150,
        required=True,
    )

    phone = forms.CharField(
        label="Telefon",
        max_length=30,
        required=False,
    )

    password1 = forms.CharField(
        label="Parol",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Parolni tasdiqlash",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "phone",
        ]

    def __init__(self, *args, store=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.store = store

        self.instance.role = User.Role.CASHIER
        self.instance.store = store
        self.instance.is_staff = False
        self.instance.is_superuser = False

        placeholders = {
            "first_name": "Masalan: Aziz",
            "last_name": "Masalan: Karimov",
            "username": "Masalan: aziz_cashier",
            "phone": "Masalan: +996 555 123 456",
            "password1": "Yangi parol",
            "password2": "Parolni qayta kiriting",
        }

        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["placeholder"] = placeholders.get(
                field_name, ""
            )

    def clean_username(self):
        username = User.normalize_username(
            self.cleaned_data["username"]
        ).strip().lower()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "Bu login oldin ro‘yxatdan o‘tgan."
            )

        return username

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Parollar bir xil emas.")

        elif password1:
            password_user = User(
                username=cleaned_data.get("username", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
                role=User.Role.CASHIER,
                store=self.store,
            )

            try:
                validate_password(password1, user=password_user)
            except ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        if self.store is None:
            raise ValueError("Kassir uchun market aniqlanmadi.")

        cashier = super().save(commit=False)
        cashier.store = self.store
        cashier.role = User.Role.CASHIER
        cashier.is_active = True
        cashier.is_staff = False
        cashier.is_superuser = False

        cashier.set_password(self.cleaned_data["password1"])

        if commit:
            cashier.full_clean()
            cashier.save()

        return cashier


class CashierUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "phone",
        ]
        labels = {
            "first_name": "Ism",
            "last_name": "Familiya",
            "username": "Login",
            "phone": "Telefon",
        }

    def __init__(self, *args, store=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.store = store

        if store is not None:
            self.instance.store = store

        self.instance.role = User.Role.CASHIER
        self.instance.is_staff = False
        self.instance.is_superuser = False

        self.fields["first_name"].required = True

        placeholders = {
            "first_name": "Kassir ismi",
            "last_name": "Kassir familiyasi",
            "username": "Tizimga kirish logini",
            "phone": "+996 555 123 456",
        }

        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["placeholder"] = placeholders.get(
                field_name, ""
            )

    def clean_username(self):
        username = User.normalize_username(
            self.cleaned_data["username"]
        ).strip().lower()

        duplicate_user = (
            User.objects.filter(username__iexact=username)
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if duplicate_user:
            raise forms.ValidationError(
                "Bu login boshqa foydalanuvchiga tegishli."
            )

        return username

    def save(self, commit=True):
        if self.store is None:
            raise ValueError("Kassir marketi aniqlanmadi.")

        cashier = super().save(commit=False)
        cashier.store = self.store
        cashier.role = User.Role.CASHIER
        cashier.is_staff = False
        cashier.is_superuser = False

        if commit:
            cashier.full_clean()
            cashier.save()

        return cashier


class CashierPasswordResetForm(forms.Form):
    password1 = forms.CharField(
        label="Yangi parol",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Yangi parol",
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Yangi parolni tasdiqlash",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Parolni qayta kiriting",
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Parollar bir xil emas.")

        elif password1:
            try:
                validate_password(password1, user=self.user)
            except ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def save(self):
        if self.user is None:
            raise ValueError("Kassir aniqlanmadi.")

        self.user.set_password(self.cleaned_data["password1"])
        self.user.save(update_fields=["password"])

        return self.user