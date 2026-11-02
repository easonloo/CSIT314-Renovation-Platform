from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .controllers import UserAccountController, UserProfileController
from .decorators import user_admin_required
from .forms import AccountCreationForm, AccountUpdateForm, UserProfileForm
from .models import UserAccount, UserProfile
from favourites.models import Favourite
from projects.models import InteriorDesignProject
from reviews.models import ProjectReview


@user_admin_required
@require_http_methods(["GET"])
def profile_list(request):
    search_term = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all").strip()
    if status_filter not in {"all", "active", "suspended"}:
        status_filter = "all"

    profiles = UserProfileController.list_profiles(search_term=search_term)
    if status_filter == "active":
        profiles = profiles.filter(is_active=True)
    elif status_filter == "suspended":
        profiles = profiles.filter(is_active=False)
    profiles = profiles.annotate(user_count=Count("accounts"))

    profile_counts = UserProfile.objects.aggregate(
        total=Count("pk"),
        active=Count("pk", filter=Q(is_active=True)),
        suspended=Count("pk", filter=Q(is_active=False)),
    )

    return render(
        request,
        "accounts/profile_list.html",
        {
            "profiles": profiles,
            "q": search_term,
            "status_filter": status_filter,
            "profile_counts": profile_counts,
            "filtered_count": profiles.count(),
        },
    )


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_create(request):
    form = UserProfileForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        UserProfileController.create_profile(**form.cleaned_data)
        messages.success(request, "User profile created successfully.")
        return redirect("profile_list")

    return render(request, "accounts/profile_form.html", {"form": form})


@login_required
def dashboard(request):
    account = UserAccount.objects.select_related("profile").filter(
        user=request.user,
        profile__is_active=True,
    ).first()

    if account is None:
        logout(request)
        return redirect("login")

    customer_reviews = ProjectReview.objects.none()
    favourite_count = 0
    recommended_projects = InteriorDesignProject.objects.none()
    if account.profile.name == "Customer":
        customer_reviews = ProjectReview.objects.filter(
        ).select_related("customer", "project", "project__company")
        favourite_count = Favourite.objects.filter(user=request.user).count()
        recommended_projects = InteriorDesignProject.objects.filter(
            status=InteriorDesignProject.STATUS_CURRENT,
        ).select_related("company", "category")[:3]

    return render(
        request,
        "dashboard.html",
        {
            "customer_reviews": customer_reviews,
            "favourite_count": favourite_count,
            "review_count": customer_reviews.count(),
            "recommended_projects": recommended_projects,
        },
    )


@user_admin_required
@require_http_methods(["GET"])
def profile_detail(request, pk):
    profile = UserProfileController.get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    return render(request, "accounts/profile_detail.html", {"profile": profile})


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_update(request, pk):
    profile = UserProfileController.get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    form = UserProfileForm(
        request.POST if request.method == "POST" else None,
        instance=profile,
    )

    if request.method == "POST" and form.is_valid():
        UserProfileController.update_profile(profile, **form.cleaned_data)
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
    profile = UserProfileController.get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    if request.method == "POST":
        UserProfileController.suspend_profile(profile)
        messages.success(request, "User profile suspended successfully.")

        if request.user.account.profile_id == profile.pk:
            logout(request)
            return redirect("login")

        return redirect("profile_detail", pk=profile.pk)

    return render(request, "accounts/profile_confirm_suspend.html", {"profile": profile})


@user_admin_required
@require_http_methods(["GET", "POST"])
def profile_reactivate(request, pk):
    profile = UserProfileController.get_profile(pk)

    if profile is None:
        raise Http404("User profile not found.")

    if request.method == "POST":
        UserProfileController.reactivate_profile(profile)
        messages.success(request, "User profile reactivated successfully.")
        return redirect("profile_detail", pk=profile.pk)

    return render(
        request,
        "accounts/profile_confirm_reactivate.html",
        {"profile": profile},
    )


@user_admin_required
@require_http_methods(["GET"])
def account_list(request):
    search_term = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all").strip()
    if status_filter not in {"all", "active", "suspended"}:
        status_filter = "all"
    profile_filter = request.GET.get("profile", "").strip()

    accounts = UserAccountController.list_accounts()
    if search_term:
        accounts = accounts.filter(
            Q(user__username__icontains=search_term)
            | Q(user__first_name__icontains=search_term)
            | Q(user__last_name__icontains=search_term)
            | Q(user__email__icontains=search_term)
        )
    if status_filter == "active":
        accounts = accounts.filter(user__is_active=True)
    elif status_filter == "suspended":
        accounts = accounts.filter(user__is_active=False)
    if profile_filter.isdigit():
        accounts = accounts.filter(profile_id=int(profile_filter))

    account_counts = UserAccount.objects.aggregate(
        total=Count("pk"),
        active=Count("pk", filter=Q(user__is_active=True)),
        suspended=Count("pk", filter=Q(user__is_active=False)),
    )
    profiles = UserProfile.objects.order_by("name")

    return render(
        request,
        "accounts/account_list.html",
        {
            "accounts": accounts,
            "q": search_term,
            "status_filter": status_filter,
            "profile_filter": profile_filter,
            "profiles": profiles,
            "account_counts": account_counts,
            "filtered_count": accounts.count(),
        },
    )


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_create(request):
    form = AccountCreationForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        UserAccountController.create_account(
            username=data["username"],
            password=data["password1"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            profile=data["profile"],
        )
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
    account = UserAccountController.get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    return render(request, "accounts/account_detail.html", {"account": account})


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_update(request, pk):
    account = UserAccountController.get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    form = AccountUpdateForm(request.POST if request.method == "POST" else None, account=account)

    if request.method == "POST" and form.is_valid():
        UserAccountController.update_account(account, **form.cleaned_data)
        messages.success(request, "User account updated successfully.")

        if account.user_id == request.user.pk and account.profile.name != "User Admin":
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
    account = UserAccountController.get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    if request.method == "POST":
        UserAccountController.suspend_account(account)
        messages.success(request, "User account suspended successfully.")

        if account.user_id == request.user.pk:
            logout(request)
            return redirect("login")

        return redirect("account_detail", pk=account.pk)

    return render(request, "accounts/account_confirm_suspend.html", {"account": account})


@user_admin_required
@require_http_methods(["GET", "POST"])
def account_reactivate(request, pk):
    account = UserAccountController.get_account(pk)

    if account is None:
        raise Http404("User account not found.")

    if request.method == "POST":
        UserAccountController.reactivate_account(account)
        messages.success(request, "User account reactivated successfully.")
        return redirect("account_detail", pk=account.pk)

    return render(request, "accounts/account_confirm_reactivate.html", {"account": account})
