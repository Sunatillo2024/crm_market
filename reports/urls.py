from django.urls import path

from . import views


app_name = "reports"


urlpatterns = [
    path(
        "reports/",
        views.report_index,
        name="index",
    ),
    path(
        "reports/export/csv/",
        views.report_export_csv,
        name="export_csv",
    ),
    path(
        "reports/export/excel/",
        views.report_export_excel,
        name="export_excel",
    ),
]