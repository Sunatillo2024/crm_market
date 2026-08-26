from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "owner", "Market egasi"
        CASHIER = "cashier", "Kassir"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True,
        verbose_name="Lavozim",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
        verbose_name="Market",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefon",
    )

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_superuser=True)
                    | (
                        Q(role__in=["owner", "cashier"])
                        & Q(store__isnull=False)
                        & Q(is_staff=False)
                    )
                ),
                name="market_user_has_role_and_store",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if not self.is_superuser:
            if not self.role:
                errors["role"] = "Foydalanuvchi rolini tanlang."

            if not self.store_id:
                errors["store"] = "Foydalanuvchi marketini tanlang."

            if self.is_staff:
                errors["is_staff"] = (
                    "Owner va kassir Django Admin xodimi bo‘la olmaydi."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_cashier(self):
        return self.role == self.Role.CASHIER

    def __str__(self):
        full_name = self.get_full_name()

        if full_name:
            return f"{full_name} ({self.username})"

        return self.username