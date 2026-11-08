from django.urls import path

from . import views

urlpatterns = [
    path("favourites/", views.favourite_list, name="favourite_list"),
    path("favourites/<int:project_id>/", views.favourite_detail, name="favourite_detail"),
    path("favourites/<int:project_id>/toggle/", views.favourite_toggle, name="favourite_toggle"),
]
