import json
from datetime import timedelta
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.accounts.models import User
from app.ai_client import call_groq
from app.extensions import db
from app.learning.models import Category
from app.quizzes.models import AttemptAnswer, Question, QuestionOption, Quiz, QuizAttempt
from app.utils import AIValidationError, PortalError, admin_required, log_admin, paginate, utcnow

quizzes = Blueprint("quizzes", __name__)

QUIZ_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "correct_answer": {"type": "integer"},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "options", "correct_answer", "explanation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


def _parse_questions(raw):
    try:
        rows = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Questions must be valid JSON.") from exc
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("A quiz must contain between 1 and 100 questions.")
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Question {index} must be an object.")
        prompt = row.get("question")
        explanation = row.get("explanation", "")
        options = row.get("options")
        try:
            marks = int(row.get("marks", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Question {index} marks must be an integer.") from exc
        if (
            not isinstance(prompt, str)
            or not prompt.strip()
            or len(prompt) > 4000
            or not isinstance(explanation, str)
            or len(explanation) > 4000
        ):
            raise ValueError(f"Question {index} needs text and a valid explanation.")
        if not isinstance(options, list) or not 2 <= len(options) <= 6:
            raise ValueError(f"Question {index} needs between 2 and 6 options.")
        parsed_options = []
        for option in options:
            if not isinstance(option, dict):
                raise ValueError(f"Question {index} options must contain text and correct fields.")
            text = option.get("text")
            correct = option.get("correct") is True
            if not isinstance(text, str) or not text.strip() or len(text) > 1000:
                raise ValueError(f"Question {index} contains an empty or oversized option.")
            parsed_options.append({"text": text.strip(), "correct": correct})
        if len({option["text"].casefold() for option in parsed_options}) != len(parsed_options):
            raise ValueError(f"Question {index} options must be distinct.")
        if sum(option["correct"] for option in parsed_options) != 1:
            raise ValueError(f"Question {index} must have exactly one correct option.")
        if not 1 <= marks <= 100:
            raise ValueError(f"Question {index} marks must be between 1 and 100.")
        normalized.append(
            {
                "question": prompt.strip(),
                "explanation": explanation.strip(),
                "marks": marks,
                "options": parsed_options,
            }
        )
    return normalized


def _save_questions(quiz, questions):
    quiz.questions.clear()
    for question_data in questions:
        question = Question(
            question_text=question_data["question"],
            explanation=question_data["explanation"],
            marks=question_data["marks"],
        )
        question.options = [
            QuestionOption(
                option_text=option["text"],
                is_correct=option["correct"],
            )
            for option in question_data["options"]
        ]
        quiz.questions.append(question)
    quiz.total_questions = len(questions)


def _new_attempt(user_id, quiz, questions):
    started_at = utcnow()
    return QuizAttempt(
        user_id=user_id,
        quiz_id=quiz.quiz_id,
        total_questions=len(questions),
        total_marks=sum(question.marks for question in questions),
        started_at=started_at,
        deadline_at=(
            started_at + timedelta(minutes=quiz.duration_minutes)
            if quiz.duration_minutes
            else None
        ),
        status="in_progress",
    )


def _expire_attempt(attempt, questions):
    if not attempt.answers:
        for question in questions:
            attempt.answers.append(
                AttemptAnswer(
                    question_id=question.question_id,
                    selected_option_id=None,
                    is_correct=False,
                    marks_obtained=Decimal("0"),
                )
            )
    attempt.correct_answers = 0
    attempt.obtained_marks = Decimal("0")
    attempt.percentage = Decimal("0")
    attempt.result = "fail"
    attempt.status = "submitted"
    attempt.timed_out = True
    attempt.submitted_at = utcnow()


def _quiz_from_form(quiz=None):
    title = request.form.get("quiz_title", "").strip()
    description = request.form.get("description", "").strip()
    difficulty = request.form.get("difficulty", "")
    try:
        category_id = int(request.form.get("category_id", ""))
        passing_percentage = Decimal(request.form.get("passing_percentage", "70"))
        duration_value = request.form.get("duration_minutes", "").strip()
        duration = int(duration_value) if duration_value else None
        questions_data = _parse_questions(request.form.get("questions_json", ""))
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(str(exc)) from exc
    category = db.session.get(Category, category_id)
    if category is None or not category.status:
        raise ValueError("Choose an active category.")
    if not title or len(title) > 200 or len(description) > 5000:
        raise ValueError("Enter a title (up to 200 characters) and a description up to 5,000 characters.")
    if difficulty not in {"easy", "medium", "hard"}:
        raise ValueError("Choose a valid difficulty.")
    if not passing_percentage.is_finite() or not 0 <= passing_percentage <= 100:
        raise ValueError("Passing percentage must be between 0 and 100.")
    if duration is not None and not 1 <= duration <= 600:
        raise ValueError("Duration must be between 1 and 600 minutes.")
    if quiz is None:
        quiz = Quiz(created_by=current_user.user_id)
        db.session.add(quiz)
    quiz.category_id = category.category_id
    quiz.quiz_title = title
    quiz.description = description or None
    quiz.difficulty = difficulty
    quiz.passing_percentage = passing_percentage
    quiz.duration_minutes = duration
    _save_questions(quiz, questions_data)
    return quiz


@quizzes.get("/quizzes")
@login_required
def list_quizzes():
    rows = paginate(
        select(Quiz)
        .join(Category)
        .where(
            Quiz.status == "published",
            Quiz.is_demo.is_(False),
            Category.status.is_(True),
        )
        .order_by(Quiz.created_at.desc())
    )
    return render_template("quizzes.html", quizzes=rows, pagination=rows, admin=False)


@quizzes.get("/admin/quizzes")
@admin_required
def admin_quizzes():
    include_demo = request.args.get("include_demo") == "1"
    statement = select(Quiz).order_by(Quiz.created_at.desc())
    if not include_demo:
        statement = statement.where(Quiz.is_demo.is_(False))
    rows = paginate(statement)
    return render_template(
        "quizzes.html",
        quizzes=rows,
        pagination=rows,
        admin=True,
        include_demo=include_demo,
    )


@quizzes.route("/admin/quizzes/new", methods=["GET", "POST"])
@admin_required
def create_quiz():
    categories = db.session.scalars(select(Category).where(Category.status.is_(True)).order_by(Category.category_name)).all()
    if request.method == "POST":
        try:
            quiz = _quiz_from_form()
            quiz.generation_type = "manual"
            quiz.status = "draft"
            db.session.flush()
            log_admin("created", "quizzes", f"Created draft quiz {quiz.quiz_title}")
            db.session.commit()
            flash("Draft quiz saved. Review it before publishing.", "success")
            return redirect(url_for("quizzes.edit_quiz", quiz_id=quiz.quiz_id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    return render_template("quiz_form.html", quiz=None, categories=categories, questions_json="[]")


@quizzes.route("/admin/quizzes/<int:quiz_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        abort(404)
    if request.method == "POST" and quiz.attempts:
        flash("This quiz has attempt history and cannot be edited without changing past results. Create a new quiz version instead.", "error")
        return redirect(url_for("quizzes.admin_quizzes"))
    categories = db.session.scalars(select(Category).where(Category.status.is_(True)).order_by(Category.category_name)).all()
    if request.method == "POST":
        try:
            _quiz_from_form(quiz)
            db.session.flush()
            log_admin("updated", "quizzes", f"Updated quiz {quiz.quiz_title}")
            db.session.commit()
            flash("Quiz saved. Published quizzes remain published; use the publish action for drafts.", "success")
            return redirect(url_for("quizzes.admin_quizzes"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    question_data = [
        {
            "question": question.question_text,
            "explanation": question.explanation or "",
            "marks": question.marks,
            "options": [
                {"text": option.option_text, "correct": option.is_correct}
                for option in question.options
            ],
        }
        for question in quiz.questions
    ]
    return render_template(
        "quiz_form.html",
        quiz=quiz,
        categories=categories,
        questions_json=json.dumps(question_data, ensure_ascii=False, indent=2),
    )


@quizzes.post("/admin/quizzes/<int:quiz_id>/publish")
@admin_required
def publish_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        abort(404)
    try:
        if quiz.status == "published":
            quiz.status = "inactive"
            action = "unpublished"
            message = "Quiz unpublished."
        elif not quiz.questions or any(
            (
                len(question.options) != 4
                if quiz.generation_type == "ai"
                else not 2 <= len(question.options) <= 6
            )
            or sum(option.is_correct for option in question.options) != 1
            for question in quiz.questions
        ):
            flash("Add valid questions with the required number of options and one correct answer before publishing.", "error")
            return redirect(url_for("quizzes.admin_quizzes"))
        elif not quiz.category.status:
            flash("Activate this quiz's category before publishing.", "error")
            return redirect(url_for("quizzes.admin_quizzes"))
        else:
            quiz.status = "published"
            action = "published"
            message = "Quiz published."
        log_admin(action, "quizzes", f"{action.capitalize()} quiz {quiz.quiz_title}")
        db.session.commit()
        flash(message, "success")
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error("Quiz status update failed: %s", type(exc).__name__)
        flash("Could not update the quiz status. No changes were saved.", "error")
    return redirect(url_for("quizzes.admin_quizzes"))


@quizzes.post("/admin/quizzes/<int:quiz_id>/delete")
@admin_required
def delete_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        abort(404)
    if quiz.is_demo:
        flash("Fictional demo quizzes are retained for demonstrations and cannot be deleted.", "warning")
    elif quiz.attempts:
        quiz.status = "inactive"
        log_admin("archived", "quizzes", f"Archived quiz {quiz.quiz_title} with attempt history")
        flash("The quiz has existing attempts and was archived instead of deleted.", "warning")
    else:
        title = quiz.quiz_title
        db.session.delete(quiz)
        log_admin("deleted", "quizzes", f"Deleted quiz {title}")
        flash("Quiz deleted.", "success")
    db.session.commit()
    return redirect(url_for("quizzes.admin_quizzes"))


@quizzes.route("/admin/quizzes/generate", methods=["GET", "POST"])
@admin_required
def generate_quiz():
    categories = db.session.scalars(select(Category).where(Category.status.is_(True)).order_by(Category.category_name)).all()
    if request.method == "GET":
        return render_template("quiz_generate.html", categories=categories, form={})
    title = request.form.get("quiz_title", "").strip()
    topic = request.form.get("topic", "").strip()
    difficulty = request.form.get("difficulty", "medium")
    description = request.form.get("description", "").strip()
    try:
        category_id = int(request.form.get("category_id", ""))
        count = int(request.form.get("question_count", "5"))
    except ValueError:
        flash("Choose a category and a valid question count.", "error")
        return render_template("quiz_generate.html", categories=categories, form=request.form)
    category = db.session.get(Category, category_id)
    if (
        not category
        or not category.status
        or not title
        or len(title) > 200
        or not topic
        or len(topic) > 250
        or len(description) > 1000
        or not 3 <= count <= 20
        or difficulty not in {"easy", "medium", "hard"}
    ):
        flash("Provide an active category, a title, a valid difficulty, and 3-20 questions.", "error")
        return render_template("quiz_generate.html", categories=categories, form=request.form)
    prompt = (
        "Return a JSON object with exactly this shape: "
        '{"questions":[{"question":"...","options":["...","...","...","..."],'
        '"correct_answer":0,"explanation":"..."}]}. '
        f"Create exactly {count} original multiple-choice cyber-awareness questions "
        f"about {topic!r} in the {category.category_name!r} category, at {difficulty} difficulty. "
        "Each question has exactly four distinct options and correct_answer is a zero-based index. "
        "Keep explanations factual, concise, and suitable for general users."
    )
    if description:
        prompt += f" Context: {description[:1000]}"
    try:
        response = json.loads(call_groq(prompt, QUIZ_RESPONSE_SCHEMA))
        generated = response.get("questions") if isinstance(response, dict) else None
        if not isinstance(generated, list) or len(generated) != count:
            raise AIValidationError("The AI response did not contain the requested number of questions.")
        normalized = []
        for index, item in enumerate(generated):
            if not isinstance(item, dict):
                raise AIValidationError(f"AI question {index + 1} has an invalid shape.")
            option_texts = item.get("options")
            correct = item.get("correct_answer")
            if (
                not isinstance(option_texts, list)
                or len(option_texts) != 4
                or isinstance(correct, bool)
                or not isinstance(correct, int)
                or not 0 <= correct < 4
            ):
                raise AIValidationError(f"AI question {index + 1} has invalid options or answer index.")
            normalized.append(
                {
                    "question": item.get("question"),
                    "explanation": item.get("explanation"),
                    "marks": 1,
                    "options": [
                        {"text": text, "correct": option_index == correct}
                        for option_index, text in enumerate(option_texts)
                    ],
                }
            )
        _parse_questions(json.dumps(normalized))
        quiz = Quiz(
            category_id=category.category_id,
            quiz_title=title,
            description=description or f"AI-generated draft topic: {topic}",
            difficulty=difficulty,
            passing_percentage=Decimal("70"),
            generation_type="ai",
            status="draft",
            created_by=current_user.user_id,
        )
        db.session.add(quiz)
        _save_questions(quiz, normalized)
        db.session.flush()
        log_admin("generated", "quizzes", f"Generated draft quiz {quiz.quiz_title} with AI")
        db.session.commit()
        flash("AI quiz draft created. Review and edit every question before publishing.", "success")
        return redirect(url_for("quizzes.edit_quiz", quiz_id=quiz.quiz_id))
    except PortalError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    except (json.JSONDecodeError, AIValidationError, ValueError) as exc:
        db.session.rollback()
        flash(f"Could not validate the AI-generated quiz: {exc}", "error")
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error("Generated quiz could not be saved: %s", type(exc).__name__)
        flash("The generated quiz could not be saved. No changes were saved.", "error")
    return render_template("quiz_generate.html", categories=categories, form=request.form)


@quizzes.route("/quizzes/<int:quiz_id>/attempt", methods=["GET", "POST"])
@login_required
def attempt_quiz(quiz_id):
    if current_user.role != "user":
        abort(403)
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None or quiz.status != "published" or not quiz.category.status:
        abort(404)
    questions = quiz.questions
    attempt_key = f"quiz_attempt_{quiz.quiz_id}"
    active_attempt_id = session.get(attempt_key)
    attempt = db.session.get(QuizAttempt, active_attempt_id) if active_attempt_id else None
    if attempt is not None and (
        attempt.user_id != current_user.user_id
        or attempt.quiz_id != quiz.quiz_id
        or attempt.status != "in_progress"
    ):
        attempt = None
    if attempt is None and request.method == "GET":
        attempt = db.session.scalar(
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == current_user.user_id,
                QuizAttempt.quiz_id == quiz.quiz_id,
                QuizAttempt.status == "in_progress",
            )
            .order_by(QuizAttempt.created_at.desc())
        )
    if request.method == "POST":
        if attempt is None:
            abort(409, "Start the quiz before submitting answers.")
        if attempt.status != "in_progress":
            abort(409)
        if attempt.deadline_at and utcnow() >= attempt.deadline_at:
            _expire_attempt(attempt, questions)
            db.session.commit()
            session.pop(attempt_key, None)
            flash("Time expired. Your unanswered quiz was submitted as a failure.", "warning")
            return redirect(url_for("quizzes.attempt_result", attempt_id=attempt.attempt_id))
        total_marks = sum(question.marks for question in questions)
        obtained_marks = Decimal("0")
        correct_count = 0
        for question in questions:
            selected = request.form.get(f"question_{question.question_id}", type=int)
            option_ids = {option.option_id: option for option in question.options}
            selected_option = option_ids.get(selected)
            is_correct = bool(selected_option and selected_option.is_correct)
            if is_correct:
                correct_count += 1
                obtained_marks += Decimal(question.marks)
            attempt.answers.append(
                AttemptAnswer(
                    question_id=question.question_id,
                    selected_option_id=selected_option.option_id if selected_option else None,
                    is_correct=is_correct,
                    marks_obtained=Decimal(question.marks) if is_correct else Decimal("0"),
                )
            )
        percentage = (obtained_marks / Decimal(total_marks) * 100) if total_marks else Decimal("0")
        attempt.correct_answers = correct_count
        attempt.obtained_marks = obtained_marks
        attempt.percentage = percentage.quantize(Decimal("0.01"))
        attempt.result = "pass" if percentage >= quiz.passing_percentage else "fail"
        attempt.status = "submitted"
        attempt.submitted_at = utcnow()
        db.session.flush()
        if attempt.result == "pass":
            from app.certificates.service import create_certificate

            create_certificate(attempt)
        db.session.commit()
        session.pop(attempt_key, None)
        return redirect(url_for("quizzes.attempt_result", attempt_id=attempt.attempt_id))
    if attempt is None:
        attempt = _new_attempt(current_user.user_id, quiz, questions)
        db.session.add(attempt)
        db.session.commit()
        session[attempt_key] = attempt.attempt_id
    elif attempt.deadline_at and utcnow() >= attempt.deadline_at:
        _expire_attempt(attempt, questions)
        db.session.commit()
        session.pop(attempt_key, None)
        flash("Time expired. Your unanswered quiz was submitted as a failure.", "warning")
        return redirect(url_for("quizzes.attempt_result", attempt_id=attempt.attempt_id))
    else:
        session[attempt_key] = attempt.attempt_id
    return render_template("quiz_attempt.html", quiz=quiz, attempt=attempt)


@quizzes.get("/quiz-attempts/<int:attempt_id>")
@login_required
def attempt_result(attempt_id):
    attempt = db.session.get(QuizAttempt, attempt_id)
    if attempt is None:
        abort(404)
    if attempt.user_id != current_user.user_id and current_user.role != "admin":
        abort(403)
    return render_template("quiz_result.html", attempt=attempt)


@quizzes.get("/quiz-history")
@login_required
def quiz_history():
    rows = paginate(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == current_user.user_id)
        .order_by(QuizAttempt.created_at.desc())
    )
    return render_template("quiz_history.html", attempts=rows, pagination=rows)
