from django.urls import path
from . import employee_views

app_name = "employees"

urlpatterns = [
    path("", employee_views.cashier_list, name="list"),
    path("create/", employee_views.cashier_create, name="create"),
    path("<int:pk>/update/", employee_views.cashier_update, name="update"),
    path("<int:pk>/password/", employee_views.cashier_password_reset, name="password"),
    path("<int:pk>/toggle-status/", employee_views.cashier_toggle_status, name="toggle_status"),
]