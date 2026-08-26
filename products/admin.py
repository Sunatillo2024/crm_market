from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "store",
        "barcode",
        "purchase_price",
        "sale_price",
        "stock_quantity",
        "unit",
        "is_active",
    )
    list_filter = (
        "store",
        "unit",
        "is_active",
    )
    search_fields = (
        "name",
        "barcode",
        "store__name",
    )
    autocomplete_fields = ("store",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "store",
        "name",
    )