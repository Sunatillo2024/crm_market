from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "store",
        "product",
        "movement_type",
        "quantity",
        "quantity_before",
        "quantity_after",
        "created_by",
    )

    list_filter = (
        "store",
        "movement_type",
        "created_at",
    )

    search_fields = (
        "product__name",
        "product__barcode",
        "note",
    )

    list_select_related = (
        "store",
        "product",
        "created_by",
    )

    readonly_fields = (
        "store",
        "product",
        "movement_type",
        "quantity",
        "quantity_before",
        "quantity_after",
        "created_by",
        "note",
        "created_at",
    )

    ordering = (
        "-created_at",
        "-pk",
    )

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False