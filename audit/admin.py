from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "store",
        "action",
        "actor",
        "target_user",
        "description",
    )

    list_filter = (
        "store",
        "action",
        "created_at",
    )

    search_fields = (
        "description",
        "actor__username",
        "target_user__username",
        "sale__sale_number",
    )

    list_select_related = (
        "store",
        "actor",
        "target_user",
        "sale",
    )

    readonly_fields = (
        "store",
        "actor",
        "target_user",
        "sale",
        "action",
        "description",
        "metadata",
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
