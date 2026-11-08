"""Use-case controls coordinate entities; persistence belongs to models.py."""

from django.core.exceptions import PermissionDenied, ValidationError

from .models import UserAccount, UserProfile


class CreateUserProfileController:
    def create_profile(self, *, name, description):
        return UserProfile.create_profile(name=name, description=description)


class ViewUserProfileController:
    def get_profile(self, pk):
        return UserProfile.get_profile(pk)


class UpdateUserProfileController:
    def update_profile(self, profile, *, name, description):
        return profile.update_details(name=name, description=description)


class SuspendUserProfileController:
    def suspend_profile(self, profile):
        return profile.suspend()


class ReactivateUserProfileController:
    def reactivate_profile(self, profile):
        return profile.reactivate()


class DeleteUserProfileController:
    def get_deletion_data(self, profile, *, actor):
        if not AccountAccessController.can_manage_users(actor):
            raise PermissionDenied
        assigned_count = profile.assigned_account_count()
        return {
            "profile": profile,
            "assigned_count": assigned_count,
            "can_delete": assigned_count == 0,
        }

    def delete_profile(self, profile, *, actor):
        if not AccountAccessController.can_manage_users(actor):
            raise PermissionDenied
        return profile.delete_profile()


class SearchUserProfilesController:
    def get_list_data(self, *, search_term="", status_filter="all"):
        return UserProfile.search_profiles(
            search_term=search_term, status_filter=status_filter,
        )


class AssignUserProfileController:
    def available_for_assignment(self, current_profile_id=None):
        return UserProfile.available_for_assignment(current_profile_id)


class CreateUserAccountController:
    def create_account(
        self, *, username, password, email, profile, first_name="", last_name="",
    ):
        return UserAccount.create_account(
            username=username, password=password, email=email, profile=profile,
            first_name=first_name, last_name=last_name,
        )


class ViewUserAccountController:
    def get_account(self, pk):
        return UserAccount.get_account(pk)


class UpdateUserAccountController:
    def update_account(self, account, *, username, first_name, last_name, email, profile):
        return account.update_details(
            username=username, first_name=first_name, last_name=last_name,
            email=email, profile=profile,
        )

    def username_exists(self, username, *, exclude_user_id=None):
        return UserAccount.username_exists(username, exclude_user_id=exclude_user_id)


class SuspendUserAccountController:
    def suspend_account(self, account):
        return account.suspend()


class ReactivateUserAccountController:
    def reactivate_account(self, account):
        return account.reactivate()


class DeleteUserAccountController:
    def get_deletion_data(self, account, *, actor):
        if not AccountAccessController.can_manage_users(actor):
            raise PermissionDenied
        return {"account": account, "can_delete": account.user_id != actor.pk}

    def delete_account(self, account, *, actor):
        if not AccountAccessController.can_manage_users(actor):
            raise PermissionDenied
        if account.user_id == actor.pk:
            raise ValidationError(
                "You cannot delete your own user account.", code="self_deletion",
            )
        return account.delete_account()


class SearchUserAccountsController:
    def get_list_data(self, *, search_term="", status_filter="all", profile_filter=""):
        return UserAccount.search_accounts(
            search_term=search_term, status_filter=status_filter,
            profile_filter=profile_filter,
        )


class AccountAccessController:
    USER_ADMIN_PROFILE = "User Admin"

    @staticmethod
    def can_access_platform(user):
        return UserAccount.has_platform_access(user)

    @staticmethod
    def get_active_account(user):
        return UserAccount.active_account_for(user)

    @staticmethod
    def can_access_profile(user, profile_name):
        return UserAccount.has_profile_access(user, profile_name)

    @classmethod
    def can_manage_users(cls, user):
        return cls.can_access_profile(user, cls.USER_ADMIN_PROFILE)


class _RoleLoginController:
    profile_name = None

    def can_login(self, user):
        return AccountAccessController.can_access_profile(user, self.profile_name)


class UserAdminLoginController(_RoleLoginController):
    profile_name = "User Admin"


class InteriorDesignerLoginController(_RoleLoginController):
    profile_name = "Interior Designer"


class CustomerLoginController(_RoleLoginController):
    profile_name = "Customer"


class PlatformManagerLoginController(_RoleLoginController):
    profile_name = "Platform Management"


class LoginController:
    """The shared login form dispatches the authenticated user's role use case."""

    role_controllers = {
        "User Admin": UserAdminLoginController,
        "Interior Designer": InteriorDesignerLoginController,
        "Customer": CustomerLoginController,
        "Platform Management": PlatformManagerLoginController,
    }

    def authenticate(self, *, request=None, username, password):
        return UserAccount.authenticate_credentials(
            request=request, username=username, password=password,
        )

    def can_login(self, user):
        account = AccountAccessController.get_active_account(user)
        if account is None:
            return False
        controller_class = self.role_controllers.get(account.profile.name)
        if controller_class is not None:
            return controller_class().can_login(user)
        # User Admin may create other profiles; keep their existing login behaviour.
        return AccountAccessController.can_access_platform(user)


class _RoleLogoutController:
    def logout_account(self, user):
        # Session invalidation is HTTP infrastructure handled by LogoutView.
        return "login"


class UserAdminLogoutController(_RoleLogoutController):
    pass


class InteriorDesignerLogoutController(_RoleLogoutController):
    pass


class CustomerLogoutController(_RoleLogoutController):
    pass


class PlatformManagerLogoutController(_RoleLogoutController):
    pass


class LogoutController:
    role_controllers = {
        "User Admin": UserAdminLogoutController,
        "Interior Designer": InteriorDesignerLogoutController,
        "Customer": CustomerLogoutController,
        "Platform Management": PlatformManagerLogoutController,
    }

    def get_logout_redirect(self, user):
        account = UserAccount.for_user(user)
        controller_class = (
            self.role_controllers.get(account.profile.name)
            if account is not None else None
        )
        # An unavailable/unassigned session must still be able to log out.
        controller = (controller_class or _RoleLogoutController)()
        return controller.logout_account(user)


class DashboardController:
    @staticmethod
    def get_dashboard_data(user):
        account = AccountAccessController.get_active_account(user)
        if account is None:
            return None

        from favourites.models import Favourite
        from projects.models import InteriorDesignProject
        from reviews.models import ProjectReview

        is_customer = account.profile.name == "Customer"
        return {
            "customer_reviews": (
                ProjectReview.public_reviews() if is_customer else ProjectReview.empty()
            ),
            "favourite_count": Favourite.count_for(user) if is_customer else 0,
            "review_count": ProjectReview.public_review_count() if is_customer else 0,
            "recommended_projects": (
                InteriorDesignProject.recommended(limit=3)
                if is_customer else InteriorDesignProject.empty()
            ),
        }


class UserProfileController:
    """Compatibility facade for existing imports; boundaries use the controls above."""

    get_list_data = staticmethod(SearchUserProfilesController().get_list_data)
    list_profiles = staticmethod(UserProfile.list_profiles)
    available_for_assignment = staticmethod(AssignUserProfileController().available_for_assignment)
    get_profile = staticmethod(ViewUserProfileController().get_profile)
    create_profile = staticmethod(CreateUserProfileController().create_profile)
    update_profile = staticmethod(UpdateUserProfileController().update_profile)
    suspend_profile = staticmethod(SuspendUserProfileController().suspend_profile)
    reactivate_profile = staticmethod(ReactivateUserProfileController().reactivate_profile)
    delete_profile = staticmethod(DeleteUserProfileController().delete_profile)


class UserAccountController:
    """Compatibility facade for existing tests and integration callers."""

    get_list_data = staticmethod(SearchUserAccountsController().get_list_data)
    list_accounts = staticmethod(UserAccount.list_accounts)
    username_exists = staticmethod(UpdateUserAccountController().username_exists)
    get_account = staticmethod(ViewUserAccountController().get_account)
    create_account = staticmethod(CreateUserAccountController().create_account)
    update_account = staticmethod(UpdateUserAccountController().update_account)
    suspend_account = staticmethod(SuspendUserAccountController().suspend_account)
    reactivate_account = staticmethod(ReactivateUserAccountController().reactivate_account)
    delete_account = staticmethod(DeleteUserAccountController().delete_account)
