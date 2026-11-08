from django.urls import path

from . import views

urlpatterns = [
    path("company/", views.company_detail, name="company_detail"),
    path("company/search/", views.company_search, name="company_search"),
    path("company/create/", views.company_create, name="company_create"),
    path("company/update/", views.company_update, name="company_update"),
    path("company/delete/", views.company_delete, name="company_delete"),
]
