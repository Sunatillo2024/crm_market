from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Product(models.Model):
    class Unit(models.TextChoices):
        PIECE = "piece", "Dona"
        KG = "kg", "Kilogramm"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Market",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Mahsulot nomi",
    )
    barcode = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Barkod",
    )
    purchase_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Kelish narxi",
    )
    sale_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Sotuv narxi",
    )
    stock_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Qoldiq",
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.PIECE,
        verbose_name="O‘lchov birligi",
    )
    low_stock_threshold = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("5"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Kam qoldiq chegarasi",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqt",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        constraints = [
            models.CheckConstraint(
                condition=Q(purchase_price__gte=0),
                name="product_purchase_price_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(sale_price__gte=0),
                name="product_sale_price_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="product_stock_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(low_stock_threshold__gte=0),
                name="product_low_threshold_non_negative",
            ),
            models.UniqueConstraint(
                fields=["store", "barcode"],
                condition=(
                    Q(is_active=True)
                    & Q(barcode__isnull=False)
                    & ~Q(barcode="")
                ),
                name="unique_active_barcode_per_store",
            ),
        ]
        indexes = [
            models.Index(
                fields=["store", "name"],
                name="product_store_name_idx",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.name:
            self.name = self.name.strip()

        if self.barcode:
            self.barcode = self.barcode.strip() or None
        else:
            self.barcode = None

        if self.unit == self.Unit.PIECE:
            if (
                self.stock_quantity is not None
                and self.stock_quantity % Decimal("1") != 0
            ):
                errors["stock_quantity"] = (
                    "Dona mahsulot qoldig‘i butun son bo‘lishi kerak."
                )

            if (
                self.low_stock_threshold is not None
                and self.low_stock_threshold % Decimal("1") != 0
            ):
                errors["low_stock_threshold"] = (
                    "Dona mahsulot chegarasi butun son bo‘lishi kerak."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = self.name.strip()

        if self.barcode:
            self.barcode = self.barcode.strip() or None
        else:
            self.barcode = None

        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return (
            self.is_active
            and self.stock_quantity <= self.low_stock_threshold
        )

    def __str__(self):
        return f"{self.name} — {self.store.name}"