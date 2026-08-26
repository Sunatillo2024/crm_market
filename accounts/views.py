from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from .forms import LoginForm
from .models import User


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()

        if user.is_superuser or user.is_staff:
            return super().form_valid(form)

        if user.role not in {
            User.Role.OWNER,
            User.Role.CASHIER,
        }:
            form.add_error(
                None,
                "Foydalanuvchiga to‘g‘ri rol biriktirilmagan.",
            )
            return self.form_invalid(form)

        if not user.store_id:
            form.add_error(
                None,
                "Foydalanuvchiga market biriktirilmagan.",
            )
            return self.form_invalid(form)

        if not user.store.is_active:
            form.add_error(
                None,
                "Bu market bloklangan.",
            )
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user

        if user.is_superuser or user.is_staff:
            return reverse("admin:index")

        if user.role == User.Role.OWNER:
            return reverse("stores:dashboard")

        if user.role == User.Role.CASHIER:
            return reverse("sales:pos")

        raise PermissionDenied(
            "Foydalanuvchiga to‘g‘ri rol biriktirilmagan."
        )


def home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    user = request.user

    if user.is_superuser or user.is_staff:
        return redirect("admin:index")

    if not user.store_id or not user.store.is_active:
        raise PermissionDenied("Market faol emas.")

    if user.role == User.Role.OWNER:
        return redirect("stores:dashboard")

    if user.role == User.Role.CASHIER:
        return redirect("sales:pos")

    raise PermissionDenied(
        "Foydalanuvchiga to‘g‘ri rol biriktirilmagan."
    )