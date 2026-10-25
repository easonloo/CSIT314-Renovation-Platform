from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import UserAccount


def _require_profile(profile_name):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            allowed = UserAccount.objects.filter(
                user=request.user,
                user__is_active=True,
                profile__name=profile_name,
                profile__is_active=True,
            ).exists()

            if not allowed:
                raise PermissionDenied

            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def user_admin_required(view):
    return _require_profile("User Admin")(view)


def interior_designer_required(view):
    return _require_profile("Interior Designer")(view)


def customer_required(view):
    return _require_profile("Customer")(view)


def platform_manager_required(view):
    return _require_profile("Platform Management")(view)