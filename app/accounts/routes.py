import hashlib
import hmac
from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import delete, func, or_, select

from app.accounts.models import LoginAttempt, User
from app.extensions import db
from app.utils import admin_required, paginate, safe_next, utcnow

accounts = Blueprint("accounts", __name__)


def _login_keys(email):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    remote_addr = request.remote_addr or "unknown"
    identity = hmac.new(secret, f"email:{email}".encode("utf-8"), hashlib.sha256).hexdigest()
    ip_address = hmac.new(secret, f"ip:{remote_addr}".encode("utf-8"), hashlib.sha256).hexdigest()
    return identity, ip_address


def _login_rate_limited(identity_hash, ip_hash):
    if current_app.config["LOGIN_THROTTLE_DISABLED"]:
        return False
    cutoff = utcnow() - timedelta(seconds=current_app.config["LOGIN_THROTTLE_WINDOW_SECONDS"])
    db.session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
    recent_failures = db.session.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.created_at >= cutoff,
            or_(
                LoginAttempt.identity_hash == identity_hash,
                LoginAttempt.ip_hash == ip_hash,
            ),
        )
    )
    return recent_failures >= current_app.config["LOGIN_THROTTLE_MAX_ATTEMPTS"]


@accounts.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("password_confirmation", "")
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            flash("Enter a valid email address.", "error")
        else:
            if not name or len(name) > 100:
                flash("Enter your full name (up to 100 characters).", "error")
            elif len(email) > 150:
                flash("Email addresses must be 150 characters or shorter.", "error")
            elif not 10 <= len(password) <= 1024:
                flash("Use a password between 10 and 1,024 characters.", "error")
            elif password != confirmation:
                flash("The passwords do not match.", "error")
            elif db.session.scalar(select(User).where(User.email == email)):
                flash("An account already exists for that email.", "error")
            else:
                user = User(full_name=name, email=email, role="user", status="active")
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Your account is ready. Sign in to continue.", "success")
                return redirect(url_for("accounts.login"))
    return render_template("auth.html", title="Create an account", mode="register")


@accounts.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        identity_hash, ip_hash = _login_keys(email)
        if _login_rate_limited(identity_hash, ip_hash):
            flash("Too many sign-in attempts. Wait a few minutes and try again.", "error")
            return render_template("auth.html", title="Sign in", mode="login"), 429
        user = db.session.scalar(select(User).where(User.email == email))
        if not user or not user.check_password(password) or user.status != "active":
            db.session.add(LoginAttempt(identity_hash=identity_hash, ip_hash=ip_hash))
            db.session.commit()
            flash("Email or password is incorrect, or the account is inactive.", "error")
        else:
            db.session.execute(
                delete(LoginAttempt).where(
                    or_(
                        LoginAttempt.identity_hash == identity_hash,
                        LoginAttempt.ip_hash == ip_hash,
                    )
                )
            )
            db.session.commit()
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(safe_next(request.args.get("next")) or url_for("main.dashboard"))
    return render_template("auth.html", title="Sign in", mode="login")


@accounts.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("main.index"))


@accounts.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        if not name or len(name) > 100 or len(mobile) > 15:
            flash("Enter a name (up to 100 characters) and a phone number (up to 15 characters).", "error")
        else:
            current_user.full_name = name
            current_user.mobile = mobile or None
            current_user.updated_at = utcnow()
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("accounts.profile"))
    return render_template("profile.html")


@accounts.get("/admin/users")
@admin_required
def manage_users():
    users = paginate(select(User).order_by(User.created_at.desc()))
    return render_template("users.html", users=users, pagination=users)


@accounts.post("/admin/users/<int:user_id>/status")
@admin_required
def change_user_status(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.user_id == current_user.user_id:
        flash("You cannot change your own account status.", "error")
    else:
        user.status = "inactive" if user.status == "active" else "active"
        user.updated_at = utcnow()
        db.session.commit()
        flash(f"Account marked {user.status}.", "success")
    return redirect(url_for("accounts.manage_users"))
