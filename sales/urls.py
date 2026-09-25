from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("pos/", views.pos, name="pos"),
    path("pos/products/search/", views.product_search, name="product_search"),
    path("pos/checkout/", views.checkout, name="checkout"),
    path("sales/", views.sale_list, name="list"),
    path("sales/<int:pk>/", views.sale_detail, name="detail"),
    path("sales/<int:pk>/receipt/", views.sale_receipt, name="receipt"),
    path("sales/<int:pk>/cancel/", views.sale_cancel, name="cancel"),
]
