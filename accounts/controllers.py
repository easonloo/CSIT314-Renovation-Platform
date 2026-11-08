from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q

from .models import UserAccount, UserProfile


class UserProfileController:
    @classmethod
    def get_list_data(cls, *, search_term="", status_filter="all"):
        search_term = (search_term or "").strip()
        status_filter = (status_filter or "all").strip()
        if status_filter not in {"all", "active", "suspended"}:
            status_filter = "all"

        profiles = cls.list_profiles(search_term=search_term)
        if status_filter == "active":
            profiles = profiles.filter(is_active=True)
        elif status_filter == "suspended":
            profiles = profiles.filter(is_active=False)
        profiles = profiles.annotate(user_count=Count("accounts"))

        return {
            "profiles": profiles,
            "q": search_term,
            "status_filter": status_filter,
            "profile_counts": UserProfile.objects.aggregate(
                total=Count("pk"),
                active=Count("pk", filter=Q(is_active=True)),
                suspended=Count("pk", filter=Q(is_active=False)),
            ),
            "filtered_count": profiles.count(),
        }

    @staticmethod
    def list_profiles(search_term=""):
        profiles = UserProfile.objects.all()
        search_term = (search_term or "").strip()

        if search_term:
            profiles = profiles.filter(name__icontains=search_term)

        return profiles.order_by("name")

    @staticmethod
    def available_for_assignment(current_profile_id=None):
        eligible = Q(is_active=True)
        if current_profile_id is not None:
            eligible |= Q(pk=current_profile_id)
        return UserProfile.objects.filter(eligible).order_by("name")

    @staticmethod
    def get_profile(pk):
        return UserProfile.objects.filter(pk=pk).first()

    @staticmethod
    def create_profile(*, name, description):
        return UserProfile.objects.create(name=name, description=description)

    @staticmethod
    def update_profile(profile, *, name, description):
        profile.name = name
        profile.description = description
        profile.save(update_fields=["name", "description"])
        return profile

    @staticmethod
    def suspend_profile(profile):
        profile.is_active = False
        profile.save(update_fields=["is_active"])
        return profile

    @staticmethod
    def reactivate_profile(profile):
        profile.is_active = True
        profile.save(update_fields=["is_active"])
        return profile


class UserAccountController:
    @classmethod
    def get_list_data(cls, *, search_term="", status_filter="all", profile_filter=""):
        search_term = (search_term or "").strip()
        status_filter = (status_filter or "all").strip()
        if status_filter not in {"all", "active", "suspended"}:
            status_filter = "all"
        profile_filter = str(profile_filter or "").strip()

        accounts = cls.list_accounts(search_term=search_term)
        if status_filter == "active":
            accounts = accounts.filter(user__is_active=True)
        elif status_filter == "suspended":
            accounts = accounts.filter(user__is_active=False)
        if profile_filter.isdecimal():
            accounts = accounts.filter(profile_id=int(profile_filter))

        return {
            "accounts": accounts,
            "q": search_term,
            "status_filter": status_filter,
            "profile_filter": profile_filter,
            "profiles": UserProfile.objects.order_by("name"),
            "account_counts": UserAccount.objects.aggregate(
                total=Count("pk"),
                active=Count("pk", filter=Q(user__is_active=True)),
                suspended=Count("pk", filter=Q(user__is_active=False)),
            ),
            "filtered_count": accounts.count(),
        }

    @staticmethod
    def list_accounts(search_term=""):
        accounts = UserAccount.objects.select_related("user", "profile")
        search_term = (search_term or "").strip()

        if search_term:
            accounts = accounts.filter(
                Q(user__username__icontains=search_term)
                | Q(user__first_name__icontains=search_term)
                | Q(user__last_name__icontains=search_term)
                | Q(user__email__icontains=search_term)
            )

        return accounts.order_by("user__username")

    @staticmethod
    def username_exists(username, *, exclude_user_id=None):
        users = get_user_model().objects.filter(username__iexact=username)
        if exclude_user_id is not None:
            users = users.exclude(pk=exclude_user_id)
        return users.exists()

    @staticmethod
    def create_account(*, username, password, email, profile, first_name="", last_name=""):
        User = get_user_model()
        username = User.normalize_username(username)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                return UserAccount.objects.create(user=user, profile=profile)
        except IntegrityError as error:
            # Check only after the failed creation transaction has rolled back.
            if not User.objects.filter(username__iexact=username).exists():
                raise

            duplicate_error = User(username=username).unique_error_message(
                User, ["username"],
            )
            raise ValidationError({"username": duplicate_error}) from error

    @staticmethod
    def get_account(pk):
        return UserAccount.objects.select_related("user", "profile").filter(pk=pk).first()

    @staticmethod
    @transaction.atomic
    def update_account(account, *, username, first_name, last_name, email, profile):
        user = account.user
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save(update_fields=["username", "first_name", "last_name", "email"])

        account.profile = profile
        account.save(update_fields=["profile"])
        return account

    @staticmethod
    def suspend_account(account):
        account.user.is_active = False
        account.user.save(update_fields=["is_active"])
        return account

    @staticmethod
    def reactivate_account(account):
        account.user.is_active = True
        account.user.save(update_fields=["is_active"])
        return account


class AccountAccessController:
    USER_ADMIN_PROFILE = "User Admin"

    @staticmethod
    def _active_accounts(user):
        if user is None or not user.is_authenticated or user.pk is None:
            return UserAccount.objects.none()

        return UserAccount.objects.filter(
            user_id=user.pk,
            user__is_active=True,
            profile__is_active=True,
        )

    @classmethod
    def can_access_platform(cls, user):
        return cls._active_accounts(user).exists()

    @classmethod
    def get_active_account(cls, user):
        return cls._active_accounts(user).select_related("profile").first()

    @classmethod
    def can_access_profile(cls, user, profile_name):
        return cls._active_accounts(user).filter(
            profile__name=profile_name,
        ).exists()

    @classmethod
    def can_manage_users(cls, user):
        return cls.can_access_profile(user, cls.USER_ADMIN_PROFILE)


class DashboardController:
    @staticmethod
    def get_dashboard_data(user):
        account = AccountAccessController.get_active_account(user)
        if account is None:
            return None

        # Import entities here so account access rules stay independent of other apps.
        from favourites.models import Favourite
        from projects.models import InteriorDesignProject
        from reviews.models import ProjectReview

        customer_reviews = ProjectReview.objects.none()
        favourite_count = 0
        recommended_projects = InteriorDesignProject.objects.none()
        if account.profile.name == "Customer":
            customer_reviews = ProjectReview.objects.select_related(
                "customer", "project", "project__company",
            )
            favourite_count = Favourite.objects.filter(user=user).count()
            recommended_projects = InteriorDesignProject.objects.filter(
                status=InteriorDesignProject.STATUS_CURRENT,
            ).select_related("company", "category")[:3]

        return {
            "customer_reviews": customer_reviews,
            "favourite_count": favourite_count,
            "review_count": customer_reviews.count(),
            "recommended_projects": recommended_projects,
        }
