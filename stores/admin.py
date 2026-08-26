from django.contrib import admin

from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "phone",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "address", "phone")
    readonly_fields = ("created_at", "updated_at")