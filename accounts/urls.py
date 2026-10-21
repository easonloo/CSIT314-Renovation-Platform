from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views
from .forms import AccountLoginForm


urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=AccountLoginForm,
        ),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(
            http_method_names=["post", "options"],
        ),
        name="logout",
    ),
    path("", views.dashboard, name="dashboard"),
    path("profiles/", views.profile_list, name="profile_list"),
    path(
        "profiles/create/",
        views.profile_create,
        name="profile_create",
    ),
    path(
        "profiles/<int:pk>/",
        views.profile_detail,
        name="profile_detail",
    ),

        path(
        "profiles/<int:pk>/update/",
        views.profile_update,
        name="profile_update",
    ),

        path(
        "profiles/<int:pk>/suspend/",
        views.profile_suspend,
        name="profile_suspend",
    ),


        path(
        "profiles/<int:pk>/reactivate/",
        views.profile_reactivate,
        name="profile_reactivate",
    ),


        path(
        "accounts/",
        views.account_list,
        name="account_list",
    ),
    path(
        "accounts/create/",
        views.account_create,
        name="account_create",
    ),


        path(
        "accounts/<int:pk>/",
        views.account_detail,
        name="account_detail",
    ),


        path(
        "accounts/<int:pk>/update/",
        views.account_update,
        name="account_update",
    ),

        path(
        "accounts/<int:pk>/suspend/",
        views.account_suspend,
        name="account_suspend",
    ),
    path(
        "accounts/<int:pk>/reactivate/",
        views.account_reactivate,
        name="account_reactivate",
    ),
]
