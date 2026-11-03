from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from .models import UserAccount, UserProfile


class UserProfileController:
    @staticmethod
    def list_profiles(search_term=""):
        profiles = UserProfile.objects.all()
        search_term = (search_term or "").strip()

        if search_term:
            profiles = profiles.filter(name__icontains=search_term)

        return profiles.order_by("name")

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
    @transaction.atomic
    def create_account(*, username, password, email, profile, first_name="", last_name=""):
        user = get_user_model().objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        return UserAccount.objects.create(user=user, profile=profile)

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
    def can_access_profile(cls, user, profile_name):
        return cls._active_accounts(user).filter(
            profile__name=profile_name,
        ).exists()

    @classmethod
    def can_manage_users(cls, user):
        return cls.can_access_profile(user, cls.USER_ADMIN_PROFILE)
