from django.urls import path

from . import views


app_name = "inventory"


urlpatterns = [
    path(
        "",
        views.inventory_list,
        name="list",
    ),
    path(
        "movements/create/",
        views.movement_create,
        name="movement_create",
    ),
    path(
        "history/",
        views.movement_history,
        name="history",
    ),
]