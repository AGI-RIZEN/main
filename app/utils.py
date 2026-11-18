import math
from datetime import datetime, timezone

from flask import request, url_for
from flask_login import current_user

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PortalError(Exception):
    """A message that is safe to show to the user."""


class AIValidationError(PortalError):
    pass


class AIUnavailable(PortalError):
    pass


def admin_required(view):
    from functools import wraps

    from flask import abort
    from flask_login import login_required

    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.role != "admin" or current_user.status != "active":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def log_admin(action, module_name, description=""):
    from app.reports.models import AdminActivityLog

    db.session.add(
        AdminActivityLog(
            admin_id=current_user.user_id,
            action=action[:200],
            module_name=module_name[:100],
            description=description or None,
        )
    )


def paginate(statement, per_page=8):
    page = request.args.get("page", 1, type=int)
    if not page or page < 1:
        page = 1
    return db.paginate(statement, page=page, per_page=per_page, error_out=False)


def page_url(page_number):
    args = request.args.to_dict(flat=True)
    args["page"] = page_number
    return url_for(request.endpoint, **(request.view_args or {}), **args)


def safe_next(target):
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    return target


def valid_rect(x_position, y_position, width, height):
    try:
        x_position = float(x_position)
        y_position = float(y_position)
        width = float(width)
        height = float(height)
    except (TypeError, ValueError):
        return False
    numbers = (x_position, y_position, width, height)
    if not all(math.isfinite(number) for number in numbers):
        return False
    return (
        x_position >= 0
        and y_position >= 0
        and width > 0
        and height > 0
        and x_position + width <= 100
        and y_position + height <= 100
    )
