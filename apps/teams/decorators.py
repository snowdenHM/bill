from functools import wraps
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse

from .roles import is_admin, is_member


def login_and_team_required(login_url=None):
    """Ensure user is authenticated and belongs to a team before accessing the view."""

    def decorator(view_func):
        return _get_decorated_function(view_func, is_member, login_url=login_url)

    return decorator


def team_admin_required(login_url=None):
    """Ensure user is an admin of the team before accessing the view."""

    def decorator(view_func):
        return _get_decorated_function(view_func, is_admin, login_url=login_url)

    return decorator


def _get_decorated_function(view_func, permission_test_function, login_url=None):
    """Internal decorator function that checks authentication and permissions."""

    @wraps(view_func)
    def _inner(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            redirect_url = login_url or "account_login"
            return HttpResponseRedirect("{}?next={}".format(reverse(redirect_url), request.path))

        team = getattr(request, "team", None)  # Ensure request has team attribute set by middleware

        if not team or not permission_test_function(user, team):
            raise Http404  # Avoid leaking information

        return view_func(request, *args, **kwargs)  # Pass all arguments properly

    return _inner
