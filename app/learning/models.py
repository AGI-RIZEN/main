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


class EventMedia(db.Model):
    __tablename__ = "event_media"

    media_id = db.Column(db.Integer, primary_key=True)
    media_type = db.Column(db.Enum("image", "video", name="event_media_type", native_enum=False), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    status = db.Column(
        db.Enum("published", "inactive", name="event_media_status", native_enum=False),
        nullable=False,
        default="inactive",
    )
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Poster(db.Model):
    __tablename__ = "posters"

    poster_id = db.Column(db.Integer, primary_key=True)
    tone = db.Column(db.String(10), nullable=False, default="p1")
    icon = db.Column(db.String(10), nullable=False, default="\U0001F511")
    title_en = db.Column(db.String(200), nullable=False)
    tips_en = db.Column(db.Text, nullable=False)
    title_hi = db.Column(db.String(200), nullable=False)
    tips_hi = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum("published", "inactive", name="poster_status", native_enum=False),
        nullable=False,
        default="inactive",
    )
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def tip_list_en(self):
        return [line.strip() for line in (self.tips_en or "").splitlines() if line.strip()]

    def tip_list_hi(self):
        return [line.strip() for line in (self.tips_hi or "").splitlines() if line.strip()]


class Infographic(db.Model):
    __tablename__ = "infographics"

    infographic_id = db.Column(db.Integer, primary_key=True)
    icon = db.Column(db.String(10), nullable=False, default="\U0001F4E6")
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum("published", "inactive", name="infographic_status", native_enum=False),
        nullable=False,
        default="inactive",
    )
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class DecisionScenario(db.Model):
    __tablename__ = "decision_scenarios"

    scenario_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    intro_text = db.Column(db.Text)
    icon = db.Column(db.String(10), nullable=False, default="\U0001F9ED")
    # JSON-encoded branching tree: {"start": "node_id", "nodes": {node_id: {...}}}.
    # Each node has "prompt" text and either "choices" (list of {"label", "next"})
    # or an "outcome" ({"result": "good"|"neutral"|"bad", "message": "..."}).
    scenario_data = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum("published", "inactive", name="decision_scenario_status", native_enum=False),
        nullable=False,
        default="inactive",
    )
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


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
