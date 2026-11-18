from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.accounts.models import User
from app.certificates.models import Certificate
from app.extensions import db
from app.learning.models import AwarenessFilm, Category, CyberNews, FilmProgress
from app.phishing.models import PhishingAttempt, PhishingScenario
from app.quizzes.models import Quiz, QuizAttempt
from app.reports.models import AdminActivityLog
from app.utils import admin_required, log_admin

main = Blueprint("main", __name__)


@main.get("/media/<path:filename>")
def media_file(filename):
    if filename.split("/", 1)[0] not in {"phishing", "films"}:
        abort(404)
    return send_from_directory(current_app.config["MEDIA_ROOT"], filename)


@main.get("/")
def index():
    news = db.session.scalars(
        select(CyberNews)
        .where(CyberNews.status == "published", CyberNews.is_demo.is_(False))
        .order_by(CyberNews.published_at.desc(), CyberNews.created_at.desc())
        .limit(3)
    ).all()
    return render_template("home.html", news=news)


@main.get("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        counts = {
            "users": db.session.scalar(select(func.count()).select_from(User).where(User.role == "user")) or 0,
            "quizzes": db.session.scalar(select(func.count()).select_from(Quiz)) or 0,
            "published_quizzes": db.session.scalar(
                select(func.count()).select_from(Quiz).where(Quiz.status == "published")
            ) or 0,
            "attempts": db.session.scalar(select(func.count()).select_from(QuizAttempt)) or 0,
            "certificates": db.session.scalar(select(func.count()).select_from(Certificate)) or 0,
            "phishing_scenarios": db.session.scalar(
                select(func.count()).select_from(PhishingScenario)
            ) or 0,
            "phishing_attempts": db.session.scalar(
                select(func.count()).select_from(PhishingAttempt)
            ) or 0,
            "films": db.session.scalar(select(func.count()).select_from(AwarenessFilm)) or 0,
            "completed_films": db.session.scalar(
                select(func.count()).select_from(FilmProgress).where(FilmProgress.is_completed.is_(True))
            ) or 0,
            "news": db.session.scalar(select(func.count()).select_from(CyberNews)) or 0,
            "draft_news": db.session.scalar(
                select(func.count()).select_from(CyberNews).where(CyberNews.status == "draft")
            ) or 0,
        }
        recent_activity = db.session.scalars(
            select(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(8)
        ).all()
        return render_template(
            "dashboard.html",
            is_admin=True,
            counts=counts,
            recent_activity=recent_activity,
        )
    quiz_attempts = db.session.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == current_user.user_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(5)
    ).all()
    phishing_attempts = db.session.scalars(
        select(PhishingAttempt)
        .where(PhishingAttempt.user_id == current_user.user_id)
        .order_by(PhishingAttempt.created_at.desc())
        .limit(5)
    ).all()
    learning_stats = {
        "quiz_attempts": db.session.scalar(
            select(func.count()).select_from(QuizAttempt).where(QuizAttempt.user_id == current_user.user_id)
        ) or 0,
        "certificates": db.session.scalar(
            select(func.count()).select_from(Certificate).where(Certificate.user_id == current_user.user_id)
        ) or 0,
        "phishing_attempts": db.session.scalar(
            select(func.count()).select_from(PhishingAttempt).where(PhishingAttempt.user_id == current_user.user_id)
        ) or 0,
        "completed_films": db.session.scalar(
            select(func.count())
            .select_from(FilmProgress)
            .where(FilmProgress.user_id == current_user.user_id, FilmProgress.is_completed.is_(True))
        ) or 0,
    }
    return render_template(
        "dashboard.html",
        is_admin=False,
        quiz_attempts=quiz_attempts,
        phishing_attempts=phishing_attempts,
        learning_stats=learning_stats,
    )


@main.get("/admin/reports")
@admin_required
def admin_reports():
    quiz_performance = db.session.execute(
        select(
            Quiz.quiz_title,
            func.count(QuizAttempt.attempt_id).label("attempt_count"),
            func.avg(QuizAttempt.percentage).label("average_percentage"),
        )
        .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.quiz_id)
        .group_by(Quiz.quiz_id, Quiz.quiz_title)
        .order_by(Quiz.quiz_title)
    ).all()
    recent_activity = db.session.scalars(
        select(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(50)
    ).all()
    return render_template(
        "reports.html",
        quiz_performance=quiz_performance,
        recent_activity=recent_activity,
    )


@main.get("/admin/categories")
@admin_required
def categories():
    rows = db.session.scalars(select(Category).order_by(Category.category_name)).all()
    return render_template("categories.html", categories=rows)


@main.post("/admin/categories")
@admin_required
def create_category():
    name = request.form.get("category_name", "").strip()
    description = request.form.get("description", "").strip()
    if not name or len(name) > 100 or len(description) > 2000:
        flash("Enter a category name (up to 100 characters) and a description up to 2,000 characters.", "error")
    elif db.session.scalar(select(Category).where(func.lower(Category.category_name) == name.lower())):
        flash("That category already exists.", "error")
    else:
        category = Category(category_name=name, description=description or None)
        db.session.add(category)
        db.session.flush()
        log_admin("created", "categories", f"Created category {name}")
        db.session.commit()
        flash("Category created.", "success")
    return redirect(url_for("main.categories"))


@main.post("/admin/categories/<int:category_id>/status")
@admin_required
def change_category_status(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    category.status = not category.status
    log_admin("updated", "categories", f"Changed category {category.category_name} status")
    db.session.commit()
    flash("Category status updated.", "success")
    return redirect(url_for("main.categories"))
