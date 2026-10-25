from django.urls import path

from . import views

urlpatterns = [
    path("reports/<str:period>/", views.report, name="report"),
]
