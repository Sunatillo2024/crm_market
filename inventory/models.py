from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        OPENING = "opening", "Boshlang‘ich qoldiq"
        IN = "in", "Kirim"
        OUT = "out", "Chiqim"
        SALE = "sale", "Savdo"
        ADJUSTMENT = "adjustment", "Qoldiqni to‘g‘rilash"
        SALE_CANCEL = "sale_cancel", "Savdo bekori"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="Market",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="Mahsulot",
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        verbose_name="Harakat turi",
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[
            MinValueValidator(
                Decimal("0.001"),
            ),
        ],
        verbose_name="O‘zgargan miqdor",
    )

    quantity_before = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Oldingi qoldiq",
    )

    quantity_after = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[
            MinValueValidator(
                Decimal("0"),
            ),
        ],
        verbose_name="Keyingi qoldiq",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="Bajargan foydalanuvchi",
    )

    note = models.TextField(
        blank=True,
        verbose_name="Izoh",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt",
    )

    class Meta:
        ordering = [
            "-created_at",
            "-pk",
        ]

        verbose_name = "Ombor harakati"
        verbose_name_plural = "Ombor harakatlari"

        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="inventory_movement_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(quantity_before__gte=0),
                name="inventory_movement_before_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_after__gte=0),
                name="inventory_movement_after_non_negative",
            ),
            models.UniqueConstraint(
                fields=[
                    "product",
                ],
                condition=Q(
                    movement_type="opening",
                ),
                name="inventory_one_opening_per_product",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "store",
                    "-created_at",
                ],
                name="inventory_store_created_idx",
            ),
            models.Index(
                fields=[
                    "store",
                    "product",
                    "-created_at",
                ],
                name="inventory_product_date_idx",
            ),
            models.Index(
                fields=[
                    "store",
                    "movement_type",
                ],
                name="inventory_store_type_idx",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.product_id and self.store_id:
            if self.product.store_id != self.store_id:
                errors["product"] = (
                    "Mahsulot tanlangan marketga tegishli emas."
                )

        if self.created_by_id and self.store_id:
            if self.created_by.store_id != self.store_id:
                errors["created_by"] = (
                    "Foydalanuvchi tanlangan marketga tegishli emas."
                )

        quantities = (
            self.quantity,
            self.quantity_before,
            self.quantity_after,
        )

        if all(value is not None for value in quantities):
            if self.movement_type == self.MovementType.OPENING:
                if self.quantity_before != Decimal("0"):
                    errors["quantity_before"] = (
                        "Boshlang‘ich harakatdan oldingi qoldiq 0 bo‘lishi kerak."
                    )

                if self.quantity_after != self.quantity:
                    errors["quantity_after"] = (
                        "Boshlang‘ich qoldiq miqdorga teng bo‘lishi kerak."
                    )

            elif self.movement_type in {
                self.MovementType.IN,
                self.MovementType.SALE_CANCEL,
            }:
                expected_quantity = (
                    self.quantity_before
                    + self.quantity
                )

                if self.quantity_after != expected_quantity:
                    errors["quantity_after"] = (
                        "Kirimdan keyingi qoldiq noto‘g‘ri hisoblangan."
                    )

            elif self.movement_type in {
                self.MovementType.OUT,
                self.MovementType.SALE,
            }:
                expected_quantity = (
                    self.quantity_before
                    - self.quantity
                )

                if self.quantity_after != expected_quantity:
                    errors["quantity_after"] = (
                        "Chiqimdan keyingi qoldiq noto‘g‘ri hisoblangan."
                    )

            elif self.movement_type == self.MovementType.ADJUSTMENT:
                actual_difference = abs(
                    self.quantity_after
                    - self.quantity_before
                )

                if actual_difference != self.quantity:
                    errors["quantity"] = (
                        "To‘g‘rilash miqdori qoldiqlar farqiga teng bo‘lishi kerak."
                    )

                if self.quantity_before == self.quantity_after:
                    errors["quantity_after"] = (
                        "Yangi qoldiq oldingi qoldiqdan farq qilishi kerak."
                    )

        if self.product_id:
            if self.product.unit == self.product.Unit.PIECE:
                for field_name in (
                    "quantity",
                    "quantity_before",
                    "quantity_after",
                ):
                    value = getattr(
                        self,
                        field_name,
                    )

                    if value is None:
                        continue

                    if value % Decimal("1") != 0:
                        errors[field_name] = (
                            "Dona mahsulot miqdori butun son bo‘lishi kerak."
                        )

        if errors:
            raise ValidationError(
                errors,
            )

    @property
    def quantity_difference(self):
        return (
            self.quantity_after
            - self.quantity_before
        )

    @property
    def is_increase(self):
        return (
            self.quantity_after
            > self.quantity_before
        )

    def __str__(self):
        return (
            f"{self.product.name} — "
            f"{self.get_movement_type_display()}"
        )