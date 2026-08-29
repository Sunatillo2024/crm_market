from django.urls import path

from . import views


app_name = "audit"


urlpatterns = [
    path(
        "activity/",
        views.audit_list,
        name="list",
    ),
]