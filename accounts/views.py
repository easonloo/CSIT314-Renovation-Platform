from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .controllers import (
    AccountAccessController,
    CreateUserAccountController,
    CreateUserProfileController,
    DashboardController,
    DeleteUserAccountController,
    DeleteUserProfileController,
    LogoutController,
    ReactivateUserAccountController,
    ReactivateUserProfileController,
    SearchUserAccountsController,
    SearchUserProfilesController,
    SuspendUserAccountController,
    SuspendUserProfileController,
    UpdateUserAccountController,
    UpdateUserProfileController,
    ViewUserAccountController,
    ViewUserProfileController,
)
from .decorators import user_admin_required
from .forms import AccountCreationForm, AccountUpdateForm, UserProfileForm


class AccountLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        self.next_page = LogoutController().get_logout_redirect(request.user)
        return super().post(request, *args, **kwargs)


@user_admin_required
@require_http_methods(["GET"])
def profile_list(request):
    context = SearchUserProfilesController().get_list_data(
        search_term=request.GET.get("q", ""),
        status_filter=request.GET.get("status", "all"),
    )
    return render(request, "accounts/profile_list.html", context)


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_create(request):
    form = UserProfileForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        CreateUserProfileController().create_profile(**form.cleaned_data)
        messages.success(request, "User profile created successfully.")
        return redirect("profile_list")

    return render(request, "accounts/profile_form.html", {"form": form})


@login_required
def dashboard(request):
    context = DashboardController.get_dashboard_data(request.user)
    if context is None:
        logout(request)
        return redirect("login")
    return render(request, "dashboard.html", context)


@user_admin_required
@require_http_methods(["GET"])
def profile_detail(request, pk):
    profile = ViewUserProfileController().get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    return render(request, "accounts/profile_detail.html", {"profile": profile})


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_update(request, pk):
    profile = ViewUserProfileController().get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    form = UserProfileForm(
        request.POST if request.method == "POST" else None,
        instance=profile,
    )

    if request.method == "POST" and form.is_valid():
        UpdateUserProfileController().update_profile(profile, **form.cleaned_data)
        messages.success(request, "User profile updated successfully.")
        return redirect("profile_detail", pk=profile.pk)

    return render(
        request,
        "accounts/profile_form.html",
        {"form": form, "profile": profile, "action": "Update"},
    )


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_suspend(request, pk):
    profile = ViewUserProfileController().get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    if request.method == "POST":
        SuspendUserProfileController().suspend_profile(profile)
        messages.success(request, "User profile suspended successfully.")

        if not AccountAccessController.can_access_platform(request.user):
            logout(request)
            return redirect("login")

        return redirect("profile_detail", pk=profile.pk)

    return render(request, "accounts/profile_confirm_suspend.html", {"profile": profile})


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_reactivate(request, pk):
    profile = ViewUserProfileController().get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    if request.method == "POST":
        ReactivateUserProfileController().reactivate_profile(profile)
        messages.success(request, "User profile reactivated successfully.")
        return redirect("profile_detail", pk=profile.pk)

    return render(
        request,
        "accounts/profile_confirm_reactivate.html",
        {"profile": profile},
    )


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_delete(request, pk):
    profile = ViewUserProfileController().get_profile(pk)
    if profile is None:
        raise Http404("User profile not found.")

    controller = DeleteUserProfileController()
    context = controller.get_deletion_data(profile, actor=request.user)
    if request.method == "POST":
        try:
            controller.delete_profile(profile, actor=request.user)
        except ValidationError as error:
            context = controller.get_deletion_data(profile, actor=request.user)
            context["error"] = " ".join(error.messages)
        else:
            messages.success(request, "User profile deleted successfully.")
            return redirect("profile_list")

    return render(request, "accounts/profile_confirm_delete.html", context)


@user_admin_required
@require_http_methods(["GET"])
def account_list(request):
    context = SearchUserAccountsController().get_list_data(
        search_term=request.GET.get("q", ""),
        status_filter=request.GET.get("status", "all"),
        profile_filter=request.GET.get("profile", ""),
    )
    return render(request, "accounts/account_list.html", context)


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_create(request):
    form = AccountCreationForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            CreateUserAccountController().create_account(
                username=data["username"],
                password=data["password1"],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                profile=data["profile"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "User account created successfully.")
            return redirect("account_list")

    return render(
        request,
        "accounts/account_form.html",
        {"form": form, "action": "Create"},
    )


@user_admin_required
@require_http_methods(["GET"])
def account_detail(request, pk):
    account = ViewUserAccountController().get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    return render(request, "accounts/account_detail.html", {"account": account})


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_update(request, pk):
    account = ViewUserAccountController().get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    form = AccountUpdateForm(request.POST if request.method == "POST" else None, account=account)

    if request.method == "POST" and form.is_valid():
        UpdateUserAccountController().update_account(account, **form.cleaned_data)
        messages.success(request, "User account updated successfully.")

        if (
            account.user_id == request.user.pk
            and not AccountAccessController.can_manage_users(request.user)
        ):
            return redirect("dashboard")

        return redirect("account_detail", pk=account.pk)

    return render(
        request,
        "accounts/account_form.html",
        {"form": form, "account": account, "action": "Update"},
    )


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_suspend(request, pk):
    account = ViewUserAccountController().get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    if request.method == "POST":
        SuspendUserAccountController().suspend_account(account)
        messages.success(request, "User account suspended successfully.")

        if account.user_id == request.user.pk:
            logout(request)
            return redirect("login")

        return redirect("account_detail", pk=account.pk)

    return render(request, "accounts/account_confirm_suspend.html", {"account": account})


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_reactivate(request, pk):
    account = ViewUserAccountController().get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    if request.method == "POST":
        ReactivateUserAccountController().reactivate_account(account)
        messages.success(request, "User account reactivated successfully.")
        return redirect("account_detail", pk=account.pk)

    return render(request, "accounts/account_confirm_reactivate.html", {"account": account})


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_delete(request, pk):
    account = ViewUserAccountController().get_account(pk)
    if account is None:
        raise Http404("User account not found.")

    controller = DeleteUserAccountController()
    context = controller.get_deletion_data(account, actor=request.user)
    if request.method == "POST":
        try:
            controller.delete_account(account, actor=request.user)
        except ValidationError as error:
            context = controller.get_deletion_data(account, actor=request.user)
            context["error"] = " ".join(error.messages)
        else:
            messages.success(request, "User account deleted successfully.")
            return redirect("account_list")

    return render(request, "accounts/account_confirm_delete.html", context)
