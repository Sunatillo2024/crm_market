from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def roles_required(*allowed_roles):
    def decorator(view_function):
        @login_required(login_url="accounts:login")
        @wraps(view_function)
        def wrapped_view(request, *args, **kwargs):
            user = request.user

            if user.role not in allowed_roles:
                raise PermissionDenied(
                    "Bu sahifaga kirish huquqingiz yo‘q."
                )

            if not user.store_id:
                raise PermissionDenied(
                    "Foydalanuvchiga market biriktirilmagan."
                )

            if not user.store.is_active:
                raise PermissionDenied(
                    "Market faol emas."
                )

            return view_function(request, *args, **kwargs)

        return wrapped_view

    return decorator