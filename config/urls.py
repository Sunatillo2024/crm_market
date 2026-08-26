from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "",
        include(
            "accounts.urls",
        ),
    ),
    path(
        "",
        include(
            "stores.urls",
        ),
    ),
    path(
        "",
        include(
            "sales.urls",
        ),
    ),
    path(
        "products/",
        include(
            "products.urls",
        ),
    ),
    path(
        "inventory/",
        include(
            "inventory.urls",
        ),
    ),
]