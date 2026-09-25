from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CASHIER_CREATED = "cashier_created", "Kassir yaratildi"
        CASHIER_UPDATED = "cashier_updated", "Kassir ma’lumotlari yangilandi"
        CASHIER_PASSWORD_CHANGED = (
            "cashier_password_changed",
            "Kassir paroli yangilandi",
        )
        CASHIER_ACTIVATED = "cashier_activated", "Kassir faollashtirildi"
        CASHIER_BLOCKED = "cashier_blocked", "Kassir bloklandi"
        SALE_CANCELLED = "sale_cancelled", "Savdo bekor qilindi"
        STOCK_MOVEMENT = "stock_movement", "Ombor harakati"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="audit_logs",
        verbose_name="Market",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Bajargan foydalanuvchi",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="targeted_audit_logs",
        verbose_name="Nishon foydalanuvchi",
    )
    sale = models.ForeignKey(
        "sales.Sale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Savdo",
    )
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        verbose_name="Harakat turi",
    )
    description = models.TextField(
        verbose_name="Tavsif",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Qo‘shimcha ma’lumot",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vaqt",
    )

    class Meta:
        ordering = [
            "-created_at",
            "-pk",
        ]

        verbose_name = "Faoliyat yozuvi"
        verbose_name_plural = "Faoliyat tarixi"

        indexes = [
            models.Index(
                fields=[
                    "store",
                    "action",
                ],
                name="audit_store_action_idx",
            ),
            models.Index(
                fields=[
                    "store",
                    "-created_at",
                ],
                name="audit_store_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.actor_id and self.store_id:
            if self.actor.store_id != self.store_id:
                errors["actor"] = (
                    "Foydalanuvchi tanlangan marketga tegishli emas."
                )

        if self.target_user_id and self.store_id:
            if self.target_user.store_id != self.store_id:
                errors["target_user"] = (
                    "Nishon foydalanuvchi tanlangan marketga tegishli emas."
                )

        if self.sale_id and self.store_id:
            if self.sale.store_id != self.store_id:
                errors["sale"] = "Savdo tanlangan marketga tegishli emas."

        if self.description is not None:
            self.description = str(self.description).strip()

            if not self.description:
                errors["description"] = "Tavsifni kiriting."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.description is not None:
            self.description = str(self.description).strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_action_display()} — "
            f"{self.created_at:%d.%m.%Y %H:%M}"
        )
