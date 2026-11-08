from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db import models
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Greatest


class UserProfile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    @classmethod
    def list_profiles(cls, search_term=""):
        profiles = cls.objects.all()
        term = (search_term or "").strip()
        if term:
            profiles = profiles.filter(name__icontains=term)
        return profiles.order_by("name")

    @classmethod
    def search_profiles(cls, *, search_term="", status_filter="all"):
        search_term = (search_term or "").strip()
        status_filter = (status_filter or "all").strip()
        if status_filter not in {"all", "active", "suspended"}:
            status_filter = "all"
        profiles = cls.list_profiles(search_term)
        if status_filter != "all":
            profiles = profiles.filter(is_active=status_filter == "active")
        profiles = profiles.annotate(user_count=Count("accounts"))
        return {
            "profiles": profiles,
            "q": search_term,
            "status_filter": status_filter,
            "profile_counts": cls.objects.aggregate(
                total=Count("pk"),
                active=Count("pk", filter=Q(is_active=True)),
                suspended=Count("pk", filter=Q(is_active=False)),
            ),
            "filtered_count": profiles.count(),
        }

    @classmethod
    def available_for_assignment(cls, current_profile_id=None):
        eligible = Q(is_active=True)
        if current_profile_id is not None:
            eligible |= Q(pk=current_profile_id)
        return cls.objects.filter(eligible).order_by("name")

    @classmethod
    def get_profile(cls, pk):
        return cls.objects.filter(pk=pk).first()

    @classmethod
    def create_profile(cls, *, name, description):
        return cls.objects.create(name=name, description=description)

    def update_details(self, *, name, description):
        self.name = name
        self.description = description
        self.save(update_fields=["name", "description"])
        return self

    def suspend(self):
        self.is_active = False
        self.save(update_fields=["is_active"])
        return self

    def reactivate(self):
        self.is_active = True
        self.save(update_fields=["is_active"])
        return self

    def assigned_account_count(self):
        return self.accounts.count()

    def delete_profile(self):
        try:
            self.delete()
        except ProtectedError as error:
            raise ValidationError(
                "This profile is assigned to user accounts. "
                "Reassign or delete those accounts first.",
                code="profile_in_use",
            ) from error

    def __str__(self):
        return self.name


class UserAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account",
    )
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name="accounts",
    )

    @classmethod
    def list_accounts(cls, search_term=""):
        accounts = cls.objects.select_related("user", "profile")
        term = (search_term or "").strip()
        if term:
            accounts = accounts.filter(
                Q(user__username__icontains=term)
                | Q(user__first_name__icontains=term)
                | Q(user__last_name__icontains=term)
                | Q(user__email__icontains=term)
            )
        return accounts.order_by("user__username")

    @classmethod
    def search_accounts(cls, *, search_term="", status_filter="all", profile_filter=""):
        search_term = (search_term or "").strip()
        status_filter = (status_filter or "all").strip()
        if status_filter not in {"all", "active", "suspended"}:
            status_filter = "all"
        profile_filter = str(profile_filter or "").strip()
        accounts = cls.list_accounts(search_term)
        if status_filter != "all":
            accounts = accounts.filter(user__is_active=status_filter == "active")
        if profile_filter.isdecimal():
            accounts = accounts.filter(profile_id=int(profile_filter))
        return {
            "accounts": accounts,
            "q": search_term,
            "status_filter": status_filter,
            "profile_filter": profile_filter,
            "profiles": UserProfile.list_profiles(),
            "account_counts": cls.objects.aggregate(
                total=Count("pk"),
                active=Count("pk", filter=Q(user__is_active=True)),
                suspended=Count("pk", filter=Q(user__is_active=False)),
            ),
            "filtered_count": accounts.count(),
        }

    @classmethod
    def get_account(cls, pk):
        return cls.objects.select_related("user", "profile").filter(pk=pk).first()

    @classmethod
    def for_user(cls, user):
        if user is None or not user.is_authenticated or user.pk is None:
            return None
        return cls.objects.select_related("user", "profile").filter(user_id=user.pk).first()

    @staticmethod
    def username_exists(username, *, exclude_user_id=None):
        users = get_user_model().objects.filter(username__iexact=username)
        if exclude_user_id is not None:
            users = users.exclude(pk=exclude_user_id)
        return users.exists()

    @classmethod
    def create_account(cls, *, username, password, email, profile, first_name="", last_name=""):
        User = get_user_model()
        username = User.normalize_username(username)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username, password=password, email=email,
                    first_name=first_name, last_name=last_name,
                )
                return cls.objects.create(user=user, profile=profile)
        except IntegrityError as error:
            # Check after rollback so an unrelated link failure is not hidden.
            if not User.objects.filter(username__iexact=username).exists():
                raise
            duplicate_error = User(username=username).unique_error_message(User, ["username"])
            raise ValidationError({"username": duplicate_error}) from error

    @transaction.atomic
    def update_details(self, *, username, first_name, last_name, email, profile):
        self.user.username = username
        self.user.first_name = first_name
        self.user.last_name = last_name
        self.user.email = email
        self.user.save(update_fields=["username", "first_name", "last_name", "email"])
        self.profile = profile
        self.save(update_fields=["profile"])
        return self

    def suspend(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        return self

    def reactivate(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        return self

    @transaction.atomic
    def delete_account(self):
        """Remove the login and its account, keeping surviving shortlist counts accurate."""
        from favourites.models import Favourite
        from projects.models import InteriorDesignProject

        # Serialize changes to surviving projects with favourite toggles. Projects
        # owned by this user are deleted with their company and need no adjustment.
        project_ids = list(
            InteriorDesignProject.objects.select_for_update()
            .filter(favourited_by__user_id=self.user_id)
            .exclude(company__user_id=self.user_id)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        # Recheck after acquiring the project locks in case a toggle removed a
        # favourite while this operation was waiting for the lock.
        saved_project_ids = list(
            Favourite.objects.filter(
                user_id=self.user_id, project_id__in=project_ids,
            ).values_list("project_id", flat=True)
        )
        InteriorDesignProject.objects.filter(pk__in=saved_project_ids).update(
            shortlist_count=Greatest(F("shortlist_count") - 1, 0),
        )
        # Deleting only the UserAccount would leave the authentication user behind.
        # Django cascades their company/projects, favourites, reviews and view logs.
        self.user.delete()

    @classmethod
    def _active_accounts(cls, user):
        if user is None or not user.is_authenticated or user.pk is None:
            return cls.objects.none()
        # Query fresh state, including when request.user has cached relationships.
        return cls.objects.filter(
            user_id=user.pk, user__is_active=True, profile__is_active=True,
        )

    @classmethod
    def has_platform_access(cls, user):
        return cls._active_accounts(user).exists()

    @classmethod
    def active_account_for(cls, user):
        return cls._active_accounts(user).select_related("profile").first()

    @classmethod
    def has_profile_access(cls, user, profile_name):
        return cls._active_accounts(user).filter(profile__name=profile_name).exists()

    @staticmethod
    def authenticate_credentials(*, request=None, username, password):
        """Use Django's configured password/authentication backend at the entity edge."""
        return authenticate(request, username=username, password=password)

    def __str__(self):
        return self.user.get_username()
