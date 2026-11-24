import json

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.accounts.models import User
from app.ai_client import call_groq
from app.certificates.models import Certificate
from app.extensions import db
from app.learning.models import (
    AwarenessFilm,
    Category,
    CyberNews,
    DecisionScenario,
    EventMedia,
    FilmProgress,
    Infographic,
    Poster,
)
from app.phishing.models import PhishingAttempt, PhishingScenario
from app.quizzes.models import Quiz, QuizAttempt
from app.reports.models import AdminActivityLog
from app.utils import AIValidationError, PortalError, admin_required, log_admin

main = Blueprint("main", __name__)


@main.get("/media/<path:filename>")
def media_file(filename):
    if filename.split("/", 1)[0] not in {"phishing", "films", "events"}:
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
    event_media = db.session.scalars(
        select(EventMedia)
        .where(EventMedia.status == "published")
        .order_by(EventMedia.created_at.desc())
        .limit(10)
    ).all()
    return render_template("home.html", news=news, event_media=event_media)


@main.get("/posters")
def posters():
    rows = db.session.scalars(
        select(Poster).where(Poster.status == "published").order_by(Poster.created_at.desc())
    ).all()
    return render_template("posters.html", posters=rows)


@main.get("/infographics")
def infographics():
    rows = db.session.scalars(
        select(Infographic).where(Infographic.status == "published").order_by(Infographic.created_at.desc())
    ).all()
    return render_template("infographics.html", infographics=rows)


@main.get("/decision-scenarios")
@login_required
def decision_scenarios():
    rows = db.session.scalars(
        select(DecisionScenario)
        .where(DecisionScenario.status == "published")
        .order_by(DecisionScenario.created_at.desc())
    ).all()
    return render_template("decision_scenarios.html", scenarios=rows)


@main.get("/decision-scenarios/<int:scenario_id>")
@login_required
def play_decision_scenario(scenario_id):
    scenario = db.session.get(DecisionScenario, scenario_id)
    if scenario is None or scenario.status != "published":
        abort(404)
    return render_template(
        "decision_scenario_play.html",
        scenario=scenario,
        scenario_dict=json.loads(scenario.scenario_data),
    )


LINK_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["likely_safe", "suspicious", "likely_dangerous"]},
        "risk_score": {"type": "integer"},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "recommended_action": {"type": "string"},
    },
    "required": ["verdict", "risk_score", "reasons", "recommended_action"],
    "additionalProperties": False,
}


@main.route("/tools/link-checker", methods=["GET", "POST"])
@login_required
def link_checker():
    result = None
    submitted_text = ""
    if request.method == "POST":
        submitted_text = request.form.get("content", "").strip()
        if not submitted_text:
            flash("Paste a link, SMS, or email message to check.", "error")
        elif len(submitted_text) > 2000:
            flash("That's too long — paste up to 2,000 characters.", "error")
        else:
            prompt = (
                "You are a cyber-safety assistant. You are given a raw link, SMS, or email "
                "message exactly as received. Do not visit or fetch any URL in it — judge it "
                "only from its text, structure, and known phishing/scam patterns (lookalike "
                "domains, urgency, requests for OTP/payment, mismatched sender, shortened "
                "links, spoofed brand names, etc.). Return a JSON object with: verdict "
                '(one of "likely_safe", "suspicious", "likely_dangerous"), risk_score '
                "(0-100, higher is riskier), reasons (2-5 short bullet strings explaining the "
                "verdict), and recommended_action (one short sentence telling the user what to "
                "do next).\n\nMessage to analyze:\n" + submitted_text
            )
            try:
                data = json.loads(call_groq(prompt, LINK_CHECK_SCHEMA))
                if (
                    data.get("verdict") not in {"likely_safe", "suspicious", "likely_dangerous"}
                    or not isinstance(data.get("risk_score"), int)
                    or not 0 <= data["risk_score"] <= 100
                    or not isinstance(data.get("reasons"), list)
                    or not data["reasons"]
                    or not data.get("recommended_action")
                ):
                    raise AIValidationError("The AI response did not match the required format.")
                result = data
            except json.JSONDecodeError:
                flash("The AI returned malformed output. Please try again.", "error")
            except PortalError as exc:
                flash(str(exc), "error")
    return render_template("link_checker.html", result=result, submitted_text=submitted_text)


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
            "posters": db.session.scalar(select(func.count()).select_from(Poster)) or 0,
            "infographics": db.session.scalar(select(func.count()).select_from(Infographic)) or 0,
            "event_media": db.session.scalar(select(func.count()).select_from(EventMedia)) or 0,
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
