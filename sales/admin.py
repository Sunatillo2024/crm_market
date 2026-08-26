from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    can_delete = False

    fields = (
        "product_name",
        "barcode",
        "quantity",
        "unit",
        "unit_price",
        "purchase_price",
        "line_total",
    )

    readonly_fields = fields

    def has_add_permission(
        self,
        request,
        obj=None,
    ):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "sale_number",
        "store",
        "cashier",
        "payment_method",
        "total",
        "amount_received",
        "change_amount",
        "status",
        "created_at",
    )

    list_filter = (
        "store",
        "payment_method",
        "status",
        "created_at",
    )

    search_fields = (
        "sale_number",
        "cashier__email",
        "items__product_name",
        "items__barcode",
    )

    list_select_related = (
        "store",
        "cashier",
    )

    readonly_fields = (
        "sale_number",
        "store",
        "cashier",
        "payment_method",
        "total",
        "amount_received",
        "change_amount",
        "status",
        "created_at",
    )

    inlines = (
        SaleItemInline,
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