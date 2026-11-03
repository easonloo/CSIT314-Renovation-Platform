from django.urls import path

from . import views


urlpatterns = [
    path(
        "idps/<int:project_id>/reviews/create/",
        views.review_create,
        name="review_create",
    ),
    path(
        "reviews/<int:pk>/update/",
        views.review_update,
        name="review_update",
    ),
    path(
        "reviews/<int:pk>/delete/",
        views.review_delete,
        name="review_delete",
    ),
]
