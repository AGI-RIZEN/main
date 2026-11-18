from pathlib import Path

import click
from email_validator import EmailNotValidError, validate_email
from flask import Flask
from werkzeug.security import generate_password_hash

from app.config import Config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.testing and app.config["SECRET_KEY"] in {
        None,
        "",
        "dev-only-change-me",
        "replace-with-a-long-random-string",
    }:
        raise RuntimeError("Set SECRET_KEY to a unique random value before starting the application.")
    Path(app.config["MEDIA_ROOT"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.accounts.models import User
    from app.certificates.models import Certificate
    from app.learning.models import AwarenessFilm, Category, CyberNews, FilmProgress
    from app.phishing.models import (
        PhishingAttempt,
        PhishingAttemptSelection,
        PhishingHotspot,
        PhishingScenario,
    )
    from app.quizzes.models import (
        AttemptAnswer,
        Question,
        QuestionOption,
        Quiz,
        QuizAttempt,
    )
    from app.reports.models import AdminActivityLog

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from app.accounts.routes import accounts
    from app.certificates.routes import certificates
    from app.learning.routes import learning
    from app.main.routes import main
    from app.phishing.routes import phishing
    from app.quizzes.routes import quizzes

    for blueprint in (main, accounts, quizzes, certificates, phishing, learning):
        app.register_blueprint(blueprint)

    from app.utils import page_url

    @app.context_processor
    def inject_pagination_url():
        return {"page_url": page_url}

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt="Full name")
    def create_admin(email, name):
        """Create an administrator without exposing public admin registration."""
        from app.accounts.models import User

        try:
            normalized_email = validate_email(email.strip(), check_deliverability=False).normalized
        except EmailNotValidError as exc:
            raise click.ClickException("Enter a valid email address.") from exc
        if not name.strip():
            raise click.ClickException("The administrator name cannot be empty.")
        if User.query.filter_by(email=normalized_email).first():
            raise click.ClickException("A user with that email already exists.")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("Use a password with at least 12 characters.")
        admin = User(
            full_name=name.strip(),
            email=normalized_email,
            role="admin",
            status="active",
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrator created: {normalized_email}")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Insert idempotent demo learning content without creating demo users."""
        from app.demo_data import seed_demo_data

        totals = seed_demo_data()
        click.echo(
            "Demo data ready: "
            f"{totals['categories']} categories, {totals['quizzes']} quizzes, "
            f"{totals['scenarios']} phishing scenarios, {totals['films']} inactive film placeholders, "
            f"{totals['news']} clearly labeled fictional news items."
        )

    return app


__all__ = ["create_app"]
