import json
import math

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db
from app.learning.models import Category
from app.phishing.models import (
    PhishingAttempt,
    PhishingAttemptSelection,
    PhishingHotspot,
    PhishingScenario,
)
from app.uploads import load_upload, store_image
from app.utils import admin_required, log_admin, paginate, utcnow, valid_rect

phishing = Blueprint("phishing", __name__)


def _parse_hotspots(raw):
    try:
        hotspots = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Hotspots must be valid JSON.") from exc
    if not isinstance(hotspots, list) or not 1 <= len(hotspots) <= 100:
        raise ValueError("Define between 1 and 100 hotspots.")
    parsed = []
    for index, item in enumerate(hotspots, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Hotspot {index} must be an object.")
        try:
            x = float(item.get("x"))
            y = float(item.get("y"))
            width = float(item.get("width"))
            height = float(item.get("height"))
            points = item.get("points", 10)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Hotspot {index} has invalid coordinates or points.") from exc
        title = item.get("title", "")
        explanation = item.get("explanation", "")
        if (
            not valid_rect(x, y, width, height)
            or isinstance(points, bool)
            or not isinstance(points, int)
            or not 1 <= points <= 100
        ):
            raise ValueError(f"Hotspot {index} must fit inside the image and award 1-100 points.")
        if (
            not isinstance(title, str)
            or not title.strip()
            or len(title) > 150
            or not isinstance(explanation, str)
            or not explanation.strip()
            or len(explanation) > 2000
        ):
            raise ValueError(f"Hotspot {index} needs a title and an explanation.")
        parsed.append((title.strip(), x, y, width, height, explanation.strip(), points))
    return parsed


def _write_hotspots(scenario, hotspots):
    scenario.hotspots.clear()
    for title, x, y, width, height, explanation, points in hotspots:
        scenario.hotspots.append(
            PhishingHotspot(
                hotspot_title=title,
                x_position=x,
                y_position=y,
                width=width,
                height=height,
                explanation=explanation,
                points=points,
            )
        )
    scenario.total_hotspots = len(hotspots)


@phishing.get("/phishing")
@login_required
def list_scenarios():
    scenarios = db.session.scalars(
        select(PhishingScenario)
        .join(Category)
        .where(PhishingScenario.status == "active")
        .where(Category.status.is_(True))
        .order_by(PhishingScenario.created_at.desc())
    ).all()
    return render_template("phishing.html", scenarios=scenarios, attempt=None)


@phishing.get("/admin/phishing")
@admin_required
def admin_scenarios():
    scenarios = db.session.scalars(select(PhishingScenario).order_by(PhishingScenario.created_at.desc())).all()
    return render_template("phishing_admin.html", scenarios=scenarios)


@phishing.route("/admin/phishing/new", methods=["GET", "POST"])
@admin_required
def create_scenario():
    categories = db.session.scalars(select(Category).where(Category.status.is_(True)).order_by(Category.category_name)).all()
    if request.method == "POST":
        try:
            category_id = int(request.form.get("category_id", ""))
            category = db.session.get(Category, category_id)
            title = request.form.get("scenario_title", "").strip()
            description = request.form.get("description", "").strip()
            difficulty = request.form.get("difficulty", "medium")
            hotspots = _parse_hotspots(request.form.get("hotspots_json", ""))
            original = load_upload(request.files.get("original_image"))
            phishing_image = load_upload(request.files.get("phishing_image"))
            if not category or not category.status or not title or len(title) > 200 or len(description) > 5000:
                raise ValueError("Choose an active category and enter a title and description within the limits.")
            if difficulty not in {"easy", "medium", "hard"}:
                raise ValueError("Choose a valid difficulty.")
            scenario = PhishingScenario(
                category_id=category.category_id,
                scenario_title=title,
                description=description or None,
                original_image=store_image(original, "phishing"),
                phishing_image=store_image(phishing_image, "phishing"),
                difficulty=difficulty,
                status="inactive",
                created_by=current_user.user_id,
            )
            _write_hotspots(scenario, hotspots)
            db.session.add(scenario)
            db.session.flush()
            log_admin("created", "phishing", f"Created scenario {title}")
            db.session.commit()
            flash("Scenario saved inactive. Review it and activate it when ready.", "success")
            return redirect(url_for("phishing.edit_scenario", scenario_id=scenario.scenario_id))
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    return render_template("phishing_form.html", scenario=None, categories=categories, hotspots_json="[]")


@phishing.route("/admin/phishing/<int:scenario_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_scenario(scenario_id):
    scenario = db.session.get(PhishingScenario, scenario_id)
    if scenario is None:
        abort(404)
    categories = db.session.scalars(select(Category).where(Category.status.is_(True)).order_by(Category.category_name)).all()
    if request.method == "POST":
        try:
            category_id = int(request.form.get("category_id", ""))
            category = db.session.get(Category, category_id)
            title = request.form.get("scenario_title", "").strip()
            description = request.form.get("description", "").strip()
            difficulty = request.form.get("difficulty", "medium")
            hotspots = _parse_hotspots(request.form.get("hotspots_json", ""))
            if not category or not category.status or not title or len(title) > 200 or len(description) > 5000:
                raise ValueError("Choose an active category and enter a title and description within the limits.")
            if difficulty not in {"easy", "medium", "hard"}:
                raise ValueError("Choose a valid difficulty.")
            scenario.category_id = category.category_id
            scenario.scenario_title = title
            scenario.description = description or None
            scenario.difficulty = difficulty
            original_file = request.files.get("original_image")
            phishing_file = request.files.get("phishing_image")
            if original_file and original_file.filename:
                scenario.original_image = store_image(load_upload(original_file), "phishing")
            if phishing_file and phishing_file.filename:
                scenario.phishing_image = store_image(load_upload(phishing_file), "phishing")
            _write_hotspots(scenario, hotspots)
            log_admin("updated", "phishing", f"Updated scenario {title}")
            db.session.commit()
            flash("Scenario updated.", "success")
            return redirect(url_for("phishing.admin_scenarios"))
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    hotspots_json = json.dumps(
        [
            {
                "title": hotspot.hotspot_title,
                "x": float(hotspot.x_position),
                "y": float(hotspot.y_position),
                "width": float(hotspot.width),
                "height": float(hotspot.height),
                "explanation": hotspot.explanation,
                "points": hotspot.points,
            }
            for hotspot in scenario.hotspots
        ],
        ensure_ascii=False,
        indent=2,
    )
    return render_template("phishing_form.html", scenario=scenario, categories=categories, hotspots_json=hotspots_json)


@phishing.post("/admin/phishing/<int:scenario_id>/status")
@admin_required
def change_scenario_status(scenario_id):
    scenario = db.session.get(PhishingScenario, scenario_id)
    if scenario is None:
        abort(404)
    scenario.status = "inactive" if scenario.status == "active" else "active"
    if scenario.status == "active" and not scenario.category.status:
        scenario.status = "inactive"
        flash("Activate this scenario's category before publishing.", "error")
    elif scenario.status == "active" and not scenario.hotspots:
        scenario.status = "inactive"
        flash("A scenario needs at least one hotspot before it can be activated.", "error")
    else:
        flash(f"Scenario marked {scenario.status}.", "success")
    log_admin("updated", "phishing", f"Changed scenario {scenario.scenario_title} status")
    db.session.commit()
    return redirect(url_for("phishing.admin_scenarios"))


@phishing.get("/phishing/<int:scenario_id>")
@login_required
def play_scenario(scenario_id):
    if current_user.role != "user":
        abort(403)
    scenario = db.session.get(PhishingScenario, scenario_id)
    if scenario is None or scenario.status != "active" or not scenario.category.status:
        abort(404)
    return render_template("phishing_play.html", scenario=scenario)


@phishing.post("/phishing/<int:scenario_id>/attempt")
@login_required
def submit_scenario(scenario_id):
    if current_user.role != "user":
        abort(403)
    scenario = db.session.get(PhishingScenario, scenario_id)
    if scenario is None or scenario.status != "active" or not scenario.category.status:
        abort(404)
    try:
        clicks = json.loads(request.form.get("clicks", "[]"))
    except json.JSONDecodeError:
        abort(400, "Invalid hotspot selections.")
    if not isinstance(clicks, list) or len(clicks) > 200:
        abort(400, "Submit no more than 200 hotspot clicks.")

    hotspots = scenario.hotspots
    total_score = sum(hotspot.points for hotspot in hotspots)
    attempt = PhishingAttempt(
        user_id=current_user.user_id,
        scenario_id=scenario.scenario_id,
        total_score=total_score,
    )
    identified = set()
    correct_count = 0
    incorrect_count = 0
    for point in clicks:
        if not isinstance(point, dict):
            abort(400, "Invalid hotspot coordinates.")
        try:
            x = float(point.get("x"))
            y = float(point.get("y"))
        except (TypeError, ValueError):
            abort(400, "Invalid hotspot coordinates.")
        if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 100 or not 0 <= y <= 100:
            abort(400, "Hotspot coordinates must be between 0 and 100.")
        matched = next(
            (
                hotspot
                for hotspot in hotspots
                if float(hotspot.x_position) <= x <= float(hotspot.x_position + hotspot.width)
                and float(hotspot.y_position) <= y <= float(hotspot.y_position + hotspot.height)
            ),
            None,
        )
        is_correct = bool(matched and matched.hotspot_id not in identified)
        if is_correct:
            identified.add(matched.hotspot_id)
            correct_count += 1
        else:
            incorrect_count += 1
        attempt.selections.append(
            PhishingAttemptSelection(
                hotspot_id=matched.hotspot_id if matched else None,
                x_percent=x,
                y_percent=y,
                is_correct=is_correct,
            )
        )
    attempt.score = sum(hotspot.points for hotspot in hotspots if hotspot.hotspot_id in identified)
    attempt.correct_hotspots = correct_count
    attempt.incorrect_clicks = incorrect_count
    attempt.completed_at = utcnow()
    db.session.add(attempt)
    db.session.commit()
    return render_template(
        "phishing_result.html",
        scenario=scenario,
        attempt=attempt,
        missed_hotspots=[hotspot for hotspot in hotspots if hotspot.hotspot_id not in identified],
        missed_hotspot_ids={
            hotspot.hotspot_id for hotspot in hotspots if hotspot.hotspot_id not in identified
        },
    )


@phishing.get("/phishing-history")
@login_required
def phishing_history():
    attempts = paginate(
        select(PhishingAttempt)
        .where(PhishingAttempt.user_id == current_user.user_id)
        .order_by(PhishingAttempt.created_at.desc())
    )
    return render_template("phishing_history.html", attempts=attempts, pagination=attempts)
