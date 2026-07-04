from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """Restricts a view to users with role == ADMIN. Stacks with @login_required."""
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("This area is restricted to Admin users.")
        return view_func(request, *args, **kwargs)
    return _wrapped
