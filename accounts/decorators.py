from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .controllers import AccountAccessController


def user_admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not AccountAccessController.can_manage_users(request.user):
            raise PermissionDenied

        return view(request, *args, **kwargs)

    return wrapped
