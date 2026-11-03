from django.urls import path

from . import views

urlpatterns = [
    path(
        "reports/<str:period>/download/",
        views.report_download,
        name="report_download",
    ),
    path("reports/<str:period>/", views.report, name="report"),
]