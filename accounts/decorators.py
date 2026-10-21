from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import UserAccount


def user_admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        allowed = UserAccount.objects.filter(
            user=request.user,
            user__is_active=True,
            profile__name="User Admin",
            profile__is_active=True,
        ).exists()

        if not allowed:
            raise PermissionDenied

        return view(request, *args, **kwargs)

    return wrapped