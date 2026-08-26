from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = (
        "username",
        "full_name",
        "role",
        "store",
        "is_active",
        "is_staff",
    )
    list_filter = (
        "role",
        "store",
        "is_active",
        "is_staff",
    )
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "phone",
        "store__name",
    )
    ordering = ("username",)
    autocomplete_fields = ("store",)
    list_select_related = ("store",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Market ma’lumotlari",
            {
                "fields": (
                    "role",
                    "store",
                    "phone",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Market ma’lumotlari",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                    "role",
                    "store",
                )
            },
        ),
    )

    @admin.display(description="Ism")
    def full_name(self, obj):
        return obj.get_full_name() or "—"