from django.urls import path

from . import views

urlpatterns = [
    path("idps/", views.idp_list, name="idp_list"),
    path("idps/create/", views.idp_create, name="idp_create"),
    path("idps/<int:pk>/", views.idp_detail, name="idp_detail"),
    path("idps/<int:pk>/update/", views.idp_update, name="idp_update"),
    path("idps/<int:pk>/delete/", views.idp_delete, name="idp_delete"),
    path("search/idps/", views.customer_idp_search, name="customer_idp_search"),
]
