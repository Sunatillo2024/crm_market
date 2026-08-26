from decimal import Decimal

from django import forms

from products.models import Product

from .models import StockMovement


class ProductChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, product):
        return (
            f"{product.name} — "
            f"qoldiq: {product.stock_quantity} "
            f"{product.get_unit_display()}"
        )


class StockMovementForm(forms.Form):
    product = ProductChoiceField(
        queryset=Product.objects.none(),
        label="Mahsulot",
        empty_label="Mahsulotni tanlang",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    movement_type = forms.ChoiceField(
        label="Harakat turi",
        choices=[
            (
                StockMovement.MovementType.IN,
                "Kirim — qoldiqni oshirish",
            ),
            (
                StockMovement.MovementType.OUT,
                "Chiqim — qoldiqni kamaytirish",
            ),
            (
                StockMovement.MovementType.ADJUSTMENT,
                "To‘g‘rilash — yangi haqiqiy qoldiq",
            ),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    quantity = forms.DecimalField(
        label="Miqdor",
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.001",
                "placeholder": "Masalan: 10",
            }
        ),
    )

    note = forms.CharField(
        label="Izoh",
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Masalan: yetkazib beruvchidan yangi mahsulot keldi."
                ),
            }
        ),
    )

    def __init__(
        self,
        *args,
        store,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.store = store

        self.fields["product"].queryset = (
            Product.objects.filter(
                store=store,
                is_active=True,
            )
            .order_by(
                "name",
                "pk",
            )
        )

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get(
            "product",
        )

        movement_type = cleaned_data.get(
            "movement_type",
        )

        quantity = cleaned_data.get(
            "quantity",
        )

        if not product or quantity is None:
            return cleaned_data

        if product.unit == Product.Unit.PIECE:
            if quantity % Decimal("1") != 0:
                self.add_error(
                    "quantity",
                    "Dona mahsulot uchun butun son kiriting.",
                )

                return cleaned_data

        if movement_type in {
            StockMovement.MovementType.IN,
            StockMovement.MovementType.OUT,
        }:
            if quantity <= 0:
                self.add_error(
                    "quantity",
                    "Miqdor 0 dan katta bo‘lishi kerak.",
                )

                return cleaned_data

        if movement_type == StockMovement.MovementType.OUT:
            if quantity > product.stock_quantity:
                self.add_error(
                    "quantity",
                    (
                        f"Omborda faqat "
                        f"{product.stock_quantity} "
                        f"{product.get_unit_display()} "
                        f"mavjud."
                    ),
                )

        if movement_type == StockMovement.MovementType.ADJUSTMENT:
            if quantity == product.stock_quantity:
                self.add_error(
                    "quantity",
                    "Yangi qoldiq hozirgi qoldiqdan farq qilishi kerak.",
                )

        return cleaned_data