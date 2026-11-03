from django.urls import path

from . import views

urlpatterns = [
    path("favourites/", views.favourite_list, name="favourite_list"),
    path("favourites/<int:project_id>/add/", views.favourite_add, name="favourite_add"),
]
