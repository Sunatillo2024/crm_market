from django.db import models


class Store(models.Model):
    name = models.CharField(
        max_length=150,
        verbose_name="Market nomi",
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Manzil",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefon",
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
        verbose_name = "Market"
        verbose_name_plural = "Marketlar"

    def __str__(self):
        return self.name