from datetime import datetime, timedelta
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app import create_app
from app.accounts.models import User
from app.config import TestConfig
from app.extensions import db
from app.learning.models import AwarenessFilm, Category, CyberNews, FilmProgress
from app.phishing.models import PhishingAttempt, PhishingHotspot, PhishingScenario
from app.quizzes.models import Question, QuestionOption, Quiz, QuizAttempt
from app.utils import AIUnavailable, AIValidationError


@pytest.fixture
def app(tmp_path):
    class Config(TestConfig):
        MEDIA_ROOT = str(tmp_path / "media")
        RSS_FEEDS = ("https://feed.example/rss",)

    application = create_app(Config)
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_user(app, email, role="user"):
    with app.app_context():
        user = User(full_name=email.split("@")[0], email=email, role=role, status="active")
        user.set_password("correct-horse-battery")
        db.session.add(user)
        db.session.commit()
        return user.user_id


def login(client, email):
    return client.post(
        "/login",
        data={"email": email, "password": "correct-horse-battery"},
        follow_redirects=True,
    )


def test_registration_cannot_create_an_admin(app, client):
    response = client.post(
        "/register",
        data={
            "full_name": "New learner",
            "email": "learner@example.com",
            "password": "a-very-secure-password",
            "password_confirmation": "a-very-secure-password",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="learner@example.com").one()
        assert user.role == "user"


def test_login_throttle_hashes_identifiers_and_clears_failures_after_success(app, client):
    create_user(app, "limited@example.com")
    app.config["LOGIN_THROTTLE_DISABLED"] = False
    app.config["LOGIN_THROTTLE_MAX_ATTEMPTS"] = 3
    app.config["LOGIN_THROTTLE_WINDOW_SECONDS"] = 900

    for _ in range(2):
        response = client.post(
            "/login",
            data={"email": "limited@example.com", "password": "incorrect"},
        )
        assert response.status_code == 200
    with app.app_context():
        from app.accounts.models import LoginAttempt

        assert LoginAttempt.query.count() == 2
        assert all("limited@example.com" not in item.identity_hash for item in LoginAttempt.query.all())

    assert client.post(
        "/login",
        data={"email": "limited@example.com", "password": "correct-horse-battery"},
    ).status_code == 302
    with app.app_context():
        from app.accounts.models import LoginAttempt

        assert LoginAttempt.query.count() == 0

    client.post("/logout")
    for _ in range(3):
        client.post("/login", data={"email": "limited@example.com", "password": "incorrect"})
    assert client.post(
        "/login",
        data={"email": "limited@example.com", "password": "incorrect"},
    ).status_code == 429


def test_passing_quiz_creates_downloadable_verifiable_certificate(app, client):
    user_id = create_user(app, "learner@example.com")
    with app.app_context():
        category = Category(category_name="Phishing")
        db.session.add(category)
        db.session.flush()
        quiz = Quiz(
            category_id=category.category_id,
            quiz_title="Spot the scam",
            difficulty="easy",
            passing_percentage=50,
            status="published",
            created_by=user_id,
        )
        question = Question(question_text="Which link is suspicious?", explanation="Check the real domain.")
        question.options = [
            QuestionOption(option_text="Unknown domain", is_correct=True),
            QuestionOption(option_text="Known bookmark", is_correct=False),
        ]
        quiz.questions.append(question)
        db.session.add(quiz)
        db.session.commit()
        quiz_id = quiz.quiz_id
        question_id = question.question_id
        correct_option_id = question.options[0].option_id

    login(client, "learner@example.com")
    attempt_page = client.get(f"/quizzes/{quiz_id}/attempt")
    assert attempt_page.status_code == 200
    with app.app_context():
        attempt = QuizAttempt.query.one()
        assert attempt.status == "in_progress"
        assert attempt.started_at is not None
    response = client.post(
        f"/quizzes/{quiz_id}/attempt",
        data={f"question_{question_id}": str(correct_option_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Passed" in response.data
    with app.app_context():
        from app.certificates.models import Certificate

        certificate = Certificate.query.one()
        assert certificate.attempt.result == "pass"
        assert certificate.certificate_file
        code = certificate.verification_code
        certificate_id = certificate.certificate_id
        from app.certificates.service import create_certificate

        assert create_certificate(certificate.attempt).certificate_id == certificate_id

    pdf_response = client.get(f"/certificates/{certificate_id}/download")
    assert pdf_response.status_code == 200
    assert pdf_response.data.startswith(b"%PDF")
    verify_response = client.get(f"/certificates/verify/{code}")
    assert verify_response.status_code == 200
    assert b"Certificate is valid" in verify_response.data
    duplicate_response = client.post(
        f"/quizzes/{quiz_id}/attempt",
        data={f"question_{question_id}": str(correct_option_id)},
    )
    assert duplicate_response.status_code == 409


def test_quiz_requires_start_and_expired_submission_is_saved_as_failure(app, client):
    user_id = create_user(app, "timer@example.com")
    with app.app_context():
        category = Category(category_name="Timed quizzes")
        db.session.add(category)
        db.session.flush()
        quiz = Quiz(
            category_id=category.category_id,
            quiz_title="Timed practice",
            difficulty="easy",
            duration_minutes=1,
            passing_percentage=50,
            status="published",
            created_by=user_id,
        )
        question = Question(question_text="Select the safe choice.")
        question.options = [
            QuestionOption(option_text="Safe choice", is_correct=True),
            QuestionOption(option_text="Unsafe choice", is_correct=False),
        ]
        quiz.questions.append(question)
        db.session.add(quiz)
        db.session.commit()
        quiz_id = quiz.quiz_id
        question_id = question.question_id
        correct_option_id = question.options[0].option_id

    login(client, "timer@example.com")
    assert client.post(
        f"/quizzes/{quiz_id}/attempt",
        data={f"question_{question_id}": str(correct_option_id)},
    ).status_code == 409
    assert client.get(f"/quizzes/{quiz_id}/attempt").status_code == 200
    with app.app_context():
        attempt = QuizAttempt.query.one()
        attempt.deadline_at = attempt.started_at - timedelta(seconds=1)
        db.session.commit()

    response = client.post(
        f"/quizzes/{quiz_id}/attempt",
        data={f"question_{question_id}": str(correct_option_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Time expired" in response.data
    with app.app_context():
        attempt = QuizAttempt.query.one()
        assert attempt.status == "submitted"
        assert attempt.timed_out is True
        assert attempt.result == "fail"
        assert attempt.correct_answers == 0
        assert attempt.answers[0].selected_option_id is None


def test_phishing_attempt_scores_only_identified_hotspots(app, client):
    user_id = create_user(app, "learner@example.com")
    with app.app_context():
        category = Category(category_name="Online safety")
        db.session.add(category)
        db.session.flush()
        scenario = PhishingScenario(
            category_id=category.category_id,
            scenario_title="Fake login page",
            original_image="phishing/original.png",
            phishing_image="phishing/simulated.png",
            status="active",
            created_by=user_id,
        )
        scenario.hotspots.append(
            PhishingHotspot(
                hotspot_title="Unusual domain",
                x_position=10,
                y_position=10,
                width=30,
                height=30,
                explanation="The domain does not match the real service.",
                points=10,
            )
        )
        scenario.total_hotspots = 1
        db.session.add(scenario)
        db.session.commit()
        scenario_id = scenario.scenario_id

    login(client, "learner@example.com")
    response = client.post(
        f"/phishing/{scenario_id}/attempt",
        data={"clicks": json.dumps([{"x": 20, "y": 20}, {"x": 90, "y": 90}])},
    )
    assert response.status_code == 200
    assert b"10 / 10 points" in response.data
    with app.app_context():
        attempt = PhishingAttempt.query.one()
        assert attempt.correct_hotspots == 1
        assert attempt.incorrect_clicks == 1
        assert attempt.score == 10


def test_admin_can_create_a_scenario_with_validated_screenshot_uploads(app, client):
    create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="Phishing")
        db.session.add(category)
        db.session.commit()
        category_id = category.category_id

    def image_upload():
        image = Image.new("RGB", (200, 200), color="white")
        stream = BytesIO()
        image.save(stream, format="PNG")
        stream.seek(0)
        return stream

    login(client, "admin@example.com")
    response = client.post(
        "/admin/phishing/new",
        data={
            "scenario_title": "Look-alike sign-in page",
            "description": "A safe screenshot-based practice scenario.",
            "category_id": str(category_id),
            "difficulty": "easy",
            "hotspots_json": json.dumps(
                [
                    {
                        "title": "Incorrect domain",
                        "x": 10,
                        "y": 10,
                        "width": 20,
                        "height": 20,
                        "explanation": "Check the domain before signing in.",
                        "points": 10,
                    }
                ]
            ),
            "original_image": (image_upload(), "legitimate.png"),
            "phishing_image": (image_upload(), "simulated.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        scenario = PhishingScenario.query.one()
        assert scenario.status == "inactive"
        assert scenario.total_hotspots == 1
        assert scenario.original_image != scenario.phishing_image


def test_film_progress_is_updated_and_completion_persists(app, client):
    user_id = create_user(app, "learner@example.com")
    with app.app_context():
        category = Category(category_name="Data privacy")
        db.session.add(category)
        db.session.flush()
        film = AwarenessFilm(
            category_id=category.category_id,
            film_title="Protect your data",
            video_url="https://video.example/watch.mp4",
            duration=100,
            status="published",
            uploaded_by=user_id,
        )
        db.session.add(film)
        db.session.commit()
        film_id = film.film_id

    login(client, "learner@example.com")
    response = client.post(
        f"/films/{film_id}/progress",
        data={"watched_seconds": "90"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        progress = FilmProgress.query.one()
        assert progress.is_completed is True
        assert progress.watched_seconds == 90
    client.post(f"/films/{film_id}/progress", data={"watched_seconds": "30"})
    with app.app_context():
        assert FilmProgress.query.count() == 1
        assert FilmProgress.query.one().watched_seconds == 90


def test_rss_fetch_deduplicates_and_keeps_new_articles_as_drafts(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    entry = {
        "title": "A phishing campaign targets customers",
        "link": "https://news.example/article/1",
        "summary": "<p>A report describes a phishing campaign.</p>",
        "content": [{"value": "<p>Customers should review account alerts carefully.</p>"}],
    }
    fake_feed = SimpleNamespace(feed={"title": "Example News"}, entries=[entry], bozo=False)
    monkeypatch.setattr("app.learning.routes._fetch_feed", lambda url: fake_feed)
    summarize_calls = []

    def summarize(title, description):
        summarize_calls.append((title, description))
        return (
            title,
            "A phishing campaign is targeting customers.",
            "- Review unexpected account alerts.",
            "- Verify the sender.",
            "Phishing Attacks",
        )

    monkeypatch.setattr("app.learning.routes._summarize_article", summarize)
    login(client, "admin@example.com")

    for _ in range(2):
        response = client.post("/admin/news/fetch", follow_redirects=True)
        assert response.status_code == 200
    with app.app_context():
        assert len(summarize_calls) == 1
        assert CyberNews.query.count() == 1
        article = CyberNews.query.one()
        assert article.status == "draft"
        assert article.summary
        assert article.key_points
        assert article.display_title == article.title
        assert article.article_url == "https://news.example/article/1"
        assert "Customers should review account alerts carefully." in article.description
        assert article.is_demo is False
        assert article.category.category_name == "Phishing Attacks"
        article_id = article.news_id
    publish_response = client.post(
        f"/admin/news/{article_id}/status",
        follow_redirects=True,
    )
    assert publish_response.status_code == 200
    public_news = client.get("/news").get_data(as_text=True)
    assert "A phishing campaign targets customers" in public_news
    assert "A phishing campaign is targeting customers." in public_news
    assert "https://news.example/article/1" in public_news


def test_rss_feed_parser_extracts_publisher_metadata_without_network(app, monkeypatch):
    from app.learning.routes import _fetch_feed

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.close()

    payload = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>Publisher Feed</title>
    <item><title>Publisher incident report</title>
    <link>https://publisher.example/story</link>
    <description><![CDATA[<p>Publisher-provided article text.</p>]]></description>
    <pubDate>Tue, 17 Nov 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    seen = []

    def fake_urlopen(request, timeout):
        seen.append((request.full_url, timeout))
        return FakeResponse(payload)

    monkeypatch.setattr("app.learning.routes.urlopen", fake_urlopen)
    with app.app_context():
        parsed_feed = _fetch_feed("https://publisher.example/rss")

    assert parsed_feed.feed.title == "Publisher Feed"
    assert parsed_feed.entries[0].title == "Publisher incident report"
    assert parsed_feed.entries[0].link == "https://publisher.example/story"
    assert seen == [("https://publisher.example/rss", 10)]


def test_groq_news_summary_uses_only_source_text_and_validates_key_points(app, monkeypatch):
    from app.learning.routes import NEWS_RESPONSE_SCHEMA, _summarize_article

    calls = []

    def fake_groq(prompt, schema):
        calls.append((prompt, schema))
        return json.dumps(
            {
                "display_title": "Publisher headline",
                "summary": "A source reports a phishing attempt.",
                "important_points": ["The message requests account access.", "The report recommends checking the sender."],
                "safety_tips": ["Open the service directly.", "Verify the sender independently."],
                "category": "Phishing Attacks",
            }
        )

    monkeypatch.setattr("app.learning.routes.call_groq", fake_groq)
    with app.app_context():
        display_title, summary, key_points, safety_tips, category = _summarize_article(
            "Publisher headline",
            "Publisher facts only.",
        )

    assert display_title == "Publisher headline"
    assert summary == "A source reports a phishing attempt."
    assert key_points.startswith("- The message requests account access.")
    assert safety_tips.startswith("- Open the service directly.")
    assert category == "Phishing Attacks"
    assert "Publisher facts only." in calls[0][0]
    assert calls[0][1] is NEWS_RESPONSE_SCHEMA


def test_failed_news_summary_stays_unpublished_without_fabricated_content(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    entry = {
        "title": "Publisher's real headline",
        "link": "https://news.example/real-story",
        "summary": "Only source-provided text is stored.",
    }
    monkeypatch.setattr(
        "app.learning.routes._fetch_feed",
        lambda url: SimpleNamespace(feed={"title": "Publisher"}, entries=[entry], bozo=False),
    )

    def fail_summary(title, description):
        raise AIUnavailable("Groq is temporarily unavailable.")

    monkeypatch.setattr("app.learning.routes._summarize_article", fail_summary)
    login(client, "admin@example.com")
    response = client.post("/admin/news/fetch", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        article = CyberNews.query.one()
        article_id = article.news_id
        assert article.article_url == "https://news.example/real-story"
        assert article.status == "draft"
        assert article.summary is None
        assert article.key_points is None
        assert article.safety_tips is None
        assert article.is_demo is False
    assert b"Publisher's real headline" not in client.get("/news").data
    retry_response = client.post(
        f"/admin/news/{article_id}/status",
        follow_redirects=True,
    )
    assert retry_response.status_code == 200
    assert b"Groq is temporarily unavailable" in retry_response.data
    with app.app_context():
        assert CyberNews.query.one().status == "draft"


def test_publish_incomplete_news_generates_reviewable_content_before_publication(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="General Cybersecurity")
        db.session.add(category)
        db.session.flush()
        article = CyberNews(
            category=category,
            title="Publisher headline",
            source="Publisher",
            article_url="https://publisher.example/article",
            description="Publisher-provided article text for a summary.",
            status="draft",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.news_id

    calls = []

    def summarize(title, description):
        calls.append((title, description))
        return (
            "Concise display headline",
            "A source-grounded summary.",
            "- Important source point.\n- Another source point.",
            "- Verify the source.\n- Use a trusted channel.",
            "General Cybersecurity",
        )

    monkeypatch.setattr("app.learning.routes._summarize_article", summarize)
    login(client, "admin@example.com")
    first_publish = client.post(
        f"/admin/news/{article_id}/status",
        follow_redirects=True,
    )
    assert first_publish.status_code == 200
    assert b"Validated AI content was saved as a draft" in first_publish.data
    with app.app_context():
        article = db.session.get(CyberNews, article_id)
        assert article.status == "draft"
        assert article.display_title == "Concise display headline"
        assert article.summary == "A source-grounded summary."
        assert article.key_points
        assert article.safety_tips
    assert calls == [("Publisher headline", "Publisher-provided article text for a summary.")]
    assert b"Concise display headline" not in client.get("/news").data

    publish_after_review = client.post(
        f"/admin/news/{article_id}/status",
        follow_redirects=True,
    )
    assert publish_after_review.status_code == 200
    assert b"Concise display headline" in client.get("/news").data


def test_rss_article_without_source_text_is_skipped(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    entry = {
        "title": "Headline without article text",
        "link": "https://news.example/empty-story",
    }
    monkeypatch.setattr(
        "app.learning.routes._fetch_feed",
        lambda url: SimpleNamespace(feed={"title": "Publisher"}, entries=[entry], bozo=False),
    )
    monkeypatch.setattr(
        "app.learning.routes._summarize_article",
        lambda title, description: pytest.fail("Groq must not be called with an empty article body."),
    )
    login(client, "admin@example.com")
    response = client.post("/admin/news/fetch", follow_redirects=True)
    assert response.status_code == 200
    assert b"without publisher text" in response.data
    with app.app_context():
        assert CyberNews.query.count() == 0


def test_published_real_news_is_visible_but_demo_content_is_admin_only(app, client):
    admin_id = create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="Phishing Attacks")
        db.session.add(category)
        db.session.flush()
        category_id = category.category_id
        live_article = CyberNews(
            category=category,
            title="Publisher-reported incident",
            source="Trusted Publisher",
            article_url="https://news.example/publisher-story",
            published_at=datetime(2026, 11, 17),
            summary="A summary grounded in the publisher's article.",
            key_points="- Publisher-reported point one.\n- Publisher-reported point two.",
            safety_tips="- Verify alerts directly.\n- Avoid unexpected links.",
            status="published",
        )
        demo_article = CyberNews(
            category=category,
            title="DEMO ONLY: Fictional news",
            source="Fictional example",
            article_url="https://example.invalid/demo-news",
            summary="This is fictional.",
            key_points="- Fictional point one.\n- Fictional point two.",
            safety_tips="- Fictional safety example.\n- Fictional verification example.",
            status="published",
            is_demo=True,
        )
        db.session.add_all([live_article, demo_article])
        db.session.add(
            Quiz(
                category=category,
                quiz_title="DEMO · Fictional quiz",
                description="Fictional test fixture.",
                difficulty="easy",
                status="published",
                is_demo=True,
                created_by=admin_id,
            )
        )
        db.session.commit()
        live_news_id = live_article.news_id
        demo_news_id = demo_article.news_id

    public_news = client.get("/news")
    assert b"Publisher-reported incident" in public_news.data
    assert b"DEMO ONLY: Fictional news" not in public_news.data
    assert b"https://news.example/publisher-story" in public_news.data
    home_page = client.get("/")
    assert b"Publisher-reported incident" in home_page.data
    assert b"DEMO ONLY: Fictional news" not in home_page.data
    assert b"2026-11-17" in public_news.data
    filtered_news = client.get(f"/news?category={category_id}")
    assert b"Publisher-reported incident" in filtered_news.data
    article_detail = client.get(f"/news/{live_news_id}")
    assert b"Important points" in article_detail.data
    assert b"Safety precautions" in article_detail.data
    assert client.get(f"/news/{demo_news_id}").status_code == 404

    login(client, "admin@example.com")
    assert b"DEMO ONLY: Fictional news" not in client.get("/admin/news").data
    assert b"DEMO ONLY: Fictional news" in client.get("/admin/news?include_demo=1").data
    assert "DEMO · Fictional quiz" not in client.get("/admin/quizzes").get_data(as_text=True)
    assert "DEMO · Fictional quiz" in client.get("/admin/quizzes?include_demo=1").get_data(as_text=True)

    client.post("/logout")
    create_user(app, "learner@example.com")
    login(client, "learner@example.com")
    assert b"DEMO" not in client.get("/quizzes").data


def test_admin_pages_are_not_available_to_users(app, client):
    create_user(app, "learner@example.com")
    login(client, "learner@example.com")
    assert client.get("/admin/quizzes").status_code == 403
    assert client.get("/admin/users").status_code == 403
    assert client.get("/admin/reports").status_code == 403


def test_admin_dashboard_and_reports_render_database_backed_empty_states(app, client):
    create_user(app, "admin@example.com", role="admin")
    login(client, "admin@example.com")
    dashboard = client.get("/dashboard")
    reports = client.get("/admin/reports")
    assert dashboard.status_code == 200
    assert b"Administration" in dashboard.data
    assert reports.status_code == 200
    assert b"No quiz attempts have been recorded." in reports.data


def test_ai_quiz_generation_creates_a_reviewable_draft(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="Password security")
        db.session.add(category)
        db.session.commit()
        category_id = category.category_id
    response_data = {
        "questions": [
            {
                "question": f"Question {index}?",
                "options": ["Correct choice", "Distractor A", "Distractor B", "Distractor C"],
                "correct_answer": 0,
                "explanation": "Use a unique password.",
            }
            for index in range(3)
        ]
    }
    monkeypatch.setattr(
        "app.quizzes.routes.call_groq",
        lambda prompt, schema: json.dumps(response_data),
    )
    login(client, "admin@example.com")
    response = client.post(
        "/admin/quizzes/generate",
        data={
            "quiz_title": "Password basics",
            "topic": "Unique passwords",
            "category_id": str(category_id),
            "difficulty": "easy",
            "question_count": "3",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        quiz = Quiz.query.one()
        assert quiz.generation_type == "ai"
        assert quiz.status == "draft"
        assert len(quiz.questions) == 3
        assert all(len(question.options) == 4 for question in quiz.questions)
        assert all(sum(option.is_correct for option in question.options) == 1 for question in quiz.questions)
        quiz_id = quiz.quiz_id
    assert b"Password basics" not in client.get("/quizzes").data

    publish_response = client.post(f"/admin/quizzes/{quiz_id}/publish", follow_redirects=True)
    assert publish_response.status_code == 200
    available_quizzes = client.get("/quizzes").get_data(as_text=True)
    assert "Password basics" in available_quizzes
    assert "Password security · easy" in available_quizzes
    assert "3 questions · Pass mark 70%" in available_quizzes
    unpublish_response = client.post(f"/admin/quizzes/{quiz_id}/publish", follow_redirects=True)
    assert unpublish_response.status_code == 200
    assert b"Password basics" not in client.get("/quizzes").data


def test_invalid_groq_quiz_response_is_rejected_without_saving(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="Account security")
        db.session.add(category)
        db.session.commit()
        category_id = category.category_id
    invalid_response = {
        "questions": [
            {
                "question": f"Question {index}?",
                "options": ["Too few", "Options", "Here"],
                "correct_answer": 0,
                "explanation": "An invalid option set.",
            }
            for index in range(3)
        ]
    }
    monkeypatch.setattr(
        "app.quizzes.routes.call_groq",
        lambda prompt, schema: json.dumps(invalid_response),
    )
    login(client, "admin@example.com")
    response = client.post(
        "/admin/quizzes/generate",
        data={
            "quiz_title": "Invalid response",
            "topic": "Account safety",
            "category_id": str(category_id),
            "difficulty": "easy",
            "question_count": "3",
        },
    )
    assert response.status_code == 200
    assert b"invalid options or answer index" in response.data
    with app.app_context():
        assert Quiz.query.count() == 0


def test_groq_quiz_failure_preserves_admin_input_and_saves_nothing(app, client, monkeypatch):
    create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="Password security")
        db.session.add(category)
        db.session.commit()
        category_id = category.category_id

    def unavailable(prompt, schema):
        raise AIUnavailable("Groq is temporarily unavailable.")

    monkeypatch.setattr("app.quizzes.routes.call_groq", unavailable)
    login(client, "admin@example.com")
    response = client.post(
        "/admin/quizzes/generate",
        data={
            "quiz_title": "Preserved title",
            "topic": "Account safety",
            "category_id": str(category_id),
            "difficulty": "medium",
            "question_count": "3",
        },
    )
    assert response.status_code == 200
    assert b"Preserved title" in response.data
    assert b"Account safety" in response.data
    with app.app_context():
        assert Quiz.query.count() == 0


def test_seed_demo_is_idempotent_and_demo_quiz_is_attemptable(app, client):
    create_user(app, "admin@example.com", role="admin")
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed-demo"])
    assert first.exit_code == 0, first.output
    with app.app_context():
        counts = (
            Category.query.count(),
            Quiz.query.count(),
            Question.query.count(),
            PhishingScenario.query.count(),
            PhishingHotspot.query.count(),
            AwarenessFilm.query.count(),
            CyberNews.query.count(),
        )
        assert counts == (7, 8, 40, 5, 10, 2, 3)
        assert all(film.status == "inactive" for film in AwarenessFilm.query.all())
        assert all(article.is_demo and article.status == "published" for article in CyberNews.query.all())
        scenario = PhishingScenario.query.first()
        scenario_id = scenario.scenario_id
        scenario_category_id = scenario.category_id
        assert Path(app.config["MEDIA_ROOT"], scenario.phishing_image).is_file()
        quiz = Quiz.query.filter_by(status="published").first()
        quiz_id = quiz.quiz_id
        question = quiz.questions[0]
        question_id = question.question_id
        correct_option_id = next(option.option_id for option in question.options if option.is_correct)

    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0, second.output
    with app.app_context():
        assert (
            Category.query.count(),
            Quiz.query.count(),
            Question.query.count(),
            PhishingScenario.query.count(),
            PhishingHotspot.query.count(),
            AwarenessFilm.query.count(),
            CyberNews.query.count(),
        ) == counts

    create_user(app, "learner@example.com")
    login(client, "learner@example.com")
    assert client.get(f"/quizzes/{quiz_id}/attempt").status_code == 200
    response = client.post(
        f"/quizzes/{quiz_id}/attempt",
        data={f"question_{question_id}": str(correct_option_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db.session.get(Category, scenario_category_id).status = False
        db.session.commit()
    assert client.get("/phishing").status_code == 200
    assert client.get(f"/phishing/{scenario_id}").status_code == 404
    assert client.post(f"/phishing/{scenario_id}/attempt", data={"clicks": "[]"}).status_code == 404
    with app.app_context():
        assert PhishingAttempt.query.count() == 0


def test_groq_client_requires_a_server_api_key(app):
    from app.ai_client import call_groq

    with app.app_context(), pytest.raises(AIUnavailable, match="GROQ_API_KEY"):
        call_groq("Create a quiz", {"type": "object"})


def test_groq_client_uses_structured_json_and_timeout(app, monkeypatch):
    from types import SimpleNamespace

    from app.ai_client import call_groq

    class FakeGroq:
        instances = 0

        def __init__(self, *, api_key, timeout, max_retries):
            FakeGroq.instances += 1
            assert api_key == "test-key"
            assert timeout == 30
            assert max_retries == 0
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=self.create_completion,
                )
            )

        @staticmethod
        def create_completion(**kwargs):
            assert kwargs["model"] == "openai/gpt-oss-20b"
            assert kwargs["response_format"]["type"] == "json_schema"
            assert kwargs["max_completion_tokens"] == 4096
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
            )

    monkeypatch.setattr("app.ai_client.Groq", FakeGroq)
    class GroqTestConfig(TestConfig):
        GROQ_API_KEY = "test-key"
        GROQ_MODEL = "openai/gpt-oss-20b"

    configured_app = create_app(GroqTestConfig)
    with configured_app.app_context():
        assert call_groq("Create a quiz", {"type": "object"}) == '{"ok": true}'
        assert call_groq("Summarize an article", {"type": "object"}) == '{"ok": true}'
        assert FakeGroq.instances == 1


def test_admin_can_create_and_publish_a_manual_quiz(app, client):
    create_user(app, "admin@example.com", role="admin")
    with app.app_context():
        category = Category(category_name="Online safety")
        db.session.add(category)
        db.session.commit()
        category_id = category.category_id
    questions = [
        {
            "question": "What should you do with a suspicious link?",
            "explanation": "Verify it using a trusted route.",
            "marks": 1,
            "options": [
                {"text": "Open it immediately", "correct": False},
                {"text": "Verify it independently", "correct": True},
            ],
        }
    ]
    login(client, "admin@example.com")
    response = client.post(
        "/admin/quizzes/new",
        data={
            "quiz_title": "Safe browsing",
            "description": "A short manual quiz.",
            "category_id": str(category_id),
            "difficulty": "easy",
            "passing_percentage": "70",
            "questions_json": json.dumps(questions),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        quiz = Quiz.query.one()
        quiz_id = quiz.quiz_id
        assert quiz.status == "draft"
        assert quiz.total_questions == 1
    response = client.post(f"/admin/quizzes/{quiz_id}/publish", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Quiz, quiz_id).status == "published"


def test_user_and_admin_pages_render(app, client):
    create_user(app, "learner@example.com")
    public_pages = ["/", "/news", "/news/999", "/login", "/register"]
    for path in public_pages:
        response = client.get(path)
        assert response.status_code in {200, 404}, path

    login(client, "learner@example.com")
    user_pages = [
        "/dashboard",
        "/quizzes",
        "/quiz-history",
        "/certificates",
        "/certificates/verify",
        "/phishing",
        "/phishing-history",
        "/films",
    ]
    for path in user_pages:
        response = client.get(path)
        assert response.status_code == 200, path

    client.post("/logout")
    create_user(app, "admin@example.com", role="admin")
    login(client, "admin@example.com")
    admin_pages = [
        "/dashboard",
        "/admin/users",
        "/admin/categories",
        "/admin/quizzes",
        "/admin/quizzes/new",
        "/admin/quizzes/generate",
        "/admin/phishing",
        "/admin/phishing/new",
        "/admin/films",
        "/admin/films/new",
        "/admin/news",
    ]
    for path in admin_pages:
        response = client.get(path)
        assert response.status_code == 200, path
