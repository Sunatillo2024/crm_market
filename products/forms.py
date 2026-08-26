from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Product


class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "barcode",
            "purchase_price",
            "sale_price",
            "stock_quantity",
            "unit",
            "low_stock_threshold",
        )
        labels = {
            "stock_quantity": "Boshlang‘ich qoldiq",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Masalan: Coca-Cola 1L",
                    "autofocus": True,
                }
            ),
            "barcode": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "4780012345678",
                }
            ),
            "purchase_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "sale_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "stock_quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.001",
                }
            ),
            "unit": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.001",
                }
            ),
        }

    def __init__(self, *args, store=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = store

    def clean_barcode(self):
        barcode = self.cleaned_data.get("barcode")

        if not barcode:
            return None

        barcode = barcode.strip()

        products = Product.objects.filter(
            store=self.store,
            barcode=barcode,
            is_active=True,
        )

        if self.instance.pk:
            products = products.exclude(pk=self.instance.pk)

        if products.exists():
            raise ValidationError(
                "Bu barkodli faol mahsulot marketda mavjud."
            )

        return barcode

    def clean(self):
        cleaned_data = super().clean()

        unit = cleaned_data.get("unit")
        stock_quantity = cleaned_data.get("stock_quantity")
        threshold = cleaned_data.get("low_stock_threshold")

        if stock_quantity is None and self.instance.pk:
            stock_quantity = self.instance.stock_quantity

        if unit == Product.Unit.PIECE:
            if (
                stock_quantity is not None
                and stock_quantity % Decimal("1") != 0
            ):
                field_name = (
                    "stock_quantity"
                    if "stock_quantity" in self.fields
                    else "unit"
                )

                self.add_error(
                    field_name,
                    "Dona mahsulot qoldig‘i butun son bo‘lishi kerak.",
                )

            if (
                threshold is not None
                and threshold % Decimal("1") != 0
            ):
                self.add_error(
                    "low_stock_threshold",
                    "Dona mahsulot chegarasi butun son bo‘lishi kerak.",
                )

        return cleaned_data


class ProductUpdateForm(ProductCreateForm):
    class Meta(ProductCreateForm.Meta):
        fields = (
            "name",
            "barcode",
            "purchase_price",
            "sale_price",
            "unit",
            "low_stock_threshold",
        )