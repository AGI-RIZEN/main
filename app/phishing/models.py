from app.extensions import db
from app.utils import utcnow


class PhishingScenario(db.Model):
    __tablename__ = "phishing_scenarios"

    scenario_id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False, index=True)
    scenario_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    original_image = db.Column(db.String(255), nullable=False)
    phishing_image = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(
        db.Enum("easy", "medium", "hard", name="scenario_difficulty", native_enum=False),
        nullable=False,
        default="medium",
    )
    total_hotspots = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(
        db.Enum("active", "inactive", name="scenario_status", native_enum=False),
        nullable=False,
        default="inactive",
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    category = db.relationship("Category", back_populates="scenarios")
    hotspots = db.relationship(
        "PhishingHotspot",
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="PhishingHotspot.hotspot_id",
    )
    attempts = db.relationship("PhishingAttempt", back_populates="scenario")


class PhishingHotspot(db.Model):
    __tablename__ = "phishing_hotspots"

    hotspot_id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("phishing_scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True)
    hotspot_title = db.Column(db.String(150), nullable=False)
    x_position = db.Column(db.Numeric(7, 3), nullable=False)
    y_position = db.Column(db.Numeric(7, 3), nullable=False)
    width = db.Column(db.Numeric(7, 3), nullable=False)
    height = db.Column(db.Numeric(7, 3), nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False, default=10)

    scenario = db.relationship("PhishingScenario", back_populates="hotspots")


class PhishingAttempt(db.Model):
    __tablename__ = "phishing_attempts"

    phishing_attempt_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("phishing_scenarios.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    total_score = db.Column(db.Integer, nullable=False)
    correct_hotspots = db.Column(db.Integer, nullable=False, default=0)
    incorrect_clicks = db.Column(db.Integer, nullable=False, default=0)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User")
    scenario = db.relationship("PhishingScenario", back_populates="attempts")
    selections = db.relationship(
        "PhishingAttemptSelection",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class PhishingAttemptSelection(db.Model):
    __tablename__ = "phishing_attempt_selections"

    selection_id = db.Column(db.Integer, primary_key=True)
    phishing_attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("phishing_attempts.phishing_attempt_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hotspot_id = db.Column(db.Integer, db.ForeignKey("phishing_hotspots.hotspot_id", ondelete="SET NULL"))
    x_percent = db.Column(db.Numeric(7, 3), nullable=False)
    y_percent = db.Column(db.Numeric(7, 3), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    attempt = db.relationship("PhishingAttempt", back_populates="selections")
    hotspot = db.relationship("PhishingHotspot")
