from app.extensions import db
from app.utils import utcnow


class Category(db.Model):
    __tablename__ = "categories"

    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    quizzes = db.relationship("Quiz", back_populates="category")
    scenarios = db.relationship("PhishingScenario", back_populates="category")
    films = db.relationship("AwarenessFilm", back_populates="category")
    news_items = db.relationship("CyberNews", back_populates="category")


class AwarenessFilm(db.Model):
    __tablename__ = "awareness_films"

    film_id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False, index=True)
    film_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(255), nullable=False)
    thumbnail = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    status = db.Column(
        db.Enum("published", "inactive", name="film_status", native_enum=False),
        nullable=False,
        default="published",
    )
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    category = db.relationship("Category", back_populates="films")
    progress_rows = db.relationship("FilmProgress", back_populates="film")


class FilmProgress(db.Model):
    __tablename__ = "film_progress"
    __table_args__ = (db.UniqueConstraint("user_id", "film_id", name="uq_film_progress_user_film"),)

    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    film_id = db.Column(db.Integer, db.ForeignKey("awareness_films.film_id", ondelete="RESTRICT"), nullable=False, index=True)
    watched_seconds = db.Column(db.Integer, nullable=False, default=0)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    last_watched_at = db.Column(db.DateTime)

    film = db.relationship("AwarenessFilm", back_populates="progress_rows")
    user = db.relationship("User")


class CyberNews(db.Model):
    __tablename__ = "cyber_news"

    news_id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.category_id", ondelete="SET NULL"),
        index=True,
    )
    title = db.Column(db.String(300), nullable=False)
    display_title = db.Column(db.String(300))
    source = db.Column(db.String(200), nullable=False)
    article_url = db.Column(db.String(1000), nullable=False, unique=True)
    description = db.Column(db.Text)
    published_at = db.Column(db.DateTime)
    summary = db.Column(db.Text)
    key_points = db.Column(db.Text)
    safety_tips = db.Column(db.Text)
    status = db.Column(
        db.Enum("draft", "published", "inactive", name="news_status", native_enum=False),
        nullable=False,
        default="draft",
        index=True,
    )
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, onupdate=utcnow)

    category = db.relationship("Category", back_populates="news_items")
