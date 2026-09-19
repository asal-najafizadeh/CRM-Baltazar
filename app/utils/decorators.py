from functools import wraps

from flask import abort, current_app, redirect, url_for
from flask_login import current_user


def role_required(*roles):
  """Restrict route to users with one of the given roles."""

  def decorator(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
      if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
      if current_user.role not in roles:
        abort(403)
      return view(*args, **kwargs)

    return wrapped

  return decorator


def redirect_to_role_dashboard():
  """Send authenticated user to their role dashboard."""
  endpoint = current_app.config["ROLE_DASHBOARD"].get(
    current_user.role, "auth.login"
  )
  return redirect(url_for(endpoint))
