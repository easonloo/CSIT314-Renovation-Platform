from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .controllers import AccountAccessController


def _require_profile(profile_name):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not AccountAccessController.can_access_profile(
                request.user, profile_name,
            ):
                raise PermissionDenied

            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def user_admin_required(view):
    return _require_profile(AccountAccessController.USER_ADMIN_PROFILE)(view)


def interior_designer_required(view):
    return _require_profile("Interior Designer")(view)


def customer_required(view):
    return _require_profile("Customer")(view)


def platform_manager_required(view):
    return _require_profile("Platform Management")(view)
