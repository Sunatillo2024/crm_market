from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("create/", views.product_create, name="create"),
    path("<int:pk>/edit/", views.product_edit, name="edit"),
    path("<int:pk>/archive/", views.product_archive, name="archive"),
]