from app.extensions import db
from app.utils import utcnow


class Certificate(db.Model):
    __tablename__ = "certificates"

    certificate_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.attempt_id", ondelete="RESTRICT"), nullable=False, unique=True)
    certificate_number = db.Column(db.String(100), nullable=False, unique=True)
    certificate_file = db.Column(db.String(255))
    issue_date = db.Column(db.DateTime, nullable=False, default=utcnow)
    verification_code = db.Column(db.String(100), nullable=False, unique=True)
    status = db.Column(
        db.Enum("valid", "revoked", name="certificate_status", native_enum=False),
        nullable=False,
        default="valid",
    )

    user = db.relationship("User")
    attempt = db.relationship("QuizAttempt", back_populates="certificate")
