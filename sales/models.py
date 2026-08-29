from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from products.models import Product


MONEY_STEP = Decimal("0.01")


class Sale(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Naqd pul"
        CARD = "card", "Karta"

    class Status(models.TextChoices):
        COMPLETED = "completed", "Yakunlangan"
        CANCELLED = "cancelled", "Bekor qilingan"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="Market",
    )

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sales",
        verbose_name="Kassir",
    )

    sale_number = models.CharField(
        max_length=32,
        unique=True,
        verbose_name="Savdo raqami",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        verbose_name="Holati",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name="To‘lov turi",
    )

    total = models.DecimalField(
        max_digits=28,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01"),
            ),
        ],
        verbose_name="Jami summa",
    )

    amount_received = models.DecimalField(
        max_digits=28,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Mijoz bergan summa",
    )

    change_amount = models.DecimalField(
        max_digits=28,
        decimal_places=2,
        default=Decimal("0"),
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Qaytim",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Savdo vaqti",
    )

    class Meta:
        ordering = [
            "-created_at",
            "-pk",
        ]

        verbose_name = "Savdo"
        verbose_name_plural = "Savdolar"

        constraints = [
            models.CheckConstraint(
                condition=Q(total__gt=0),
                name="sales_total_positive",
            ),
            models.CheckConstraint(
                condition=Q(amount_received__gte=0),
                name="sales_received_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(change_amount__gte=0),
                name="sales_change_non_negative",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "store",
                    "-created_at",
                ],
                name="sales_store_created_idx",
            ),
            models.Index(
                fields=[
                    "store",
                    "status",
                ],
                name="sales_store_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if (
            self.cashier_id
            and self.store_id
            and self.cashier.store_id != self.store_id
        ):
            errors["cashier"] = (
                "Kassir ushbu marketga tegishli emas."
            )

        if (
            self.total is None
            or self.amount_received is None
            or self.change_amount is None
        ):
            if errors:
                raise ValidationError(errors)

            return

        if self.payment_method == self.PaymentMethod.CASH:
            if self.amount_received < self.total:
                errors["amount_received"] = (
                    "Mijoz bergan pul jami summadan kam."
                )

            expected_change = (
                self.amount_received
                - self.total
            ).quantize(
                MONEY_STEP,
                rounding=ROUND_HALF_UP,
            )

            if (
                expected_change >= 0
                and self.change_amount != expected_change
            ):
                errors["change_amount"] = (
                    "Qaytim noto‘g‘ri hisoblangan."
                )

        elif self.payment_method == self.PaymentMethod.CARD:
            if self.amount_received != self.total:
                errors["amount_received"] = (
                    "Karta to‘lovida olingan summa jami summaga teng bo‘lishi kerak."
                )

            if self.change_amount != 0:
                errors["change_amount"] = (
                    "Karta to‘lovida qaytim bo‘lmaydi."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.sale_number} — "
            f"{self.total} som"
        )


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="Savdo",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="sale_items",
        verbose_name="Mahsulot",
    )

    product_name = models.CharField(
        max_length=200,
        verbose_name="Mahsulot nomi",
    )

    barcode = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Barkod",
    )

    unit = models.CharField(
        max_length=10,
        choices=Product.Unit.choices,
        verbose_name="O‘lchov birligi",
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[
            MinValueValidator(
                Decimal("0.001"),
            ),
        ],
        verbose_name="Miqdor",
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Sotuv narxi",
    )

    purchase_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Kelish narxi",
    )

    line_total = models.DecimalField(
        max_digits=28,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Qator summasi",
    )

    class Meta:
        ordering = [
            "pk",
        ]

        verbose_name = "Sotilgan mahsulot"
        verbose_name_plural = "Sotilgan mahsulotlar"

        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="sale_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="sale_item_price_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(purchase_price__gte=0),
                name="sale_item_purchase_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0),
                name="sale_item_total_non_negative",
            ),
            models.UniqueConstraint(
                fields=[
                    "sale",
                    "product",
                ],
                name="sales_unique_product_per_sale",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "sale",
                    "product",
                ],
                name="sale_item_sale_product_idx",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.sale_id and self.product_id:
            if self.product.store_id != self.sale.store_id:
                errors["product"] = (
                    "Mahsulot savdo marketiga tegishli emas."
                )

        if (
            self.product_id
            and self.product.unit == Product.Unit.PIECE
            and self.quantity is not None
            and self.quantity % Decimal("1") != 0
        ):
            errors["quantity"] = (
                "Dona mahsulot miqdori butun son bo‘lishi kerak."
            )

        if (
            self.quantity is not None
            and self.unit_price is not None
            and self.line_total is not None
        ):
            expected_total = (
                self.quantity
                * self.unit_price
            ).quantize(
                MONEY_STEP,
                rounding=ROUND_HALF_UP,
            )

            if self.line_total != expected_total:
                errors["line_total"] = (
                    "Mahsulotning jami summasi noto‘g‘ri hisoblangan."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def profit(self):
        return (
            (
                self.unit_price
                - self.purchase_price
            )
            * self.quantity
        ).quantize(
            MONEY_STEP,
            rounding=ROUND_HALF_UP,
        )

    def __str__(self):
        return (
            f"{self.product_name} × "
            f"{self.quantity}"
        )


    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_sales",
        verbose_name="Bekor qilgan foydalanuvchi",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bekor qilingan vaqt",
    )

    cancellation_reason = models.TextField(
        blank=True,
        verbose_name="Bekor qilish sababi",
    )