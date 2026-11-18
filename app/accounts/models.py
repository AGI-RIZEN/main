from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.utils import utcnow


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    mobile = db.Column(db.String(15))
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("admin", "user", name="user_role", native_enum=False),
        nullable=False,
        default="user",
    )
    profile_image = db.Column(db.String(255))
    status = db.Column(
        db.Enum("active", "inactive", name="user_status", native_enum=False),
        nullable=False,
        default="active",
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, onupdate=utcnow)

    def get_id(self):
        return str(self.user_id)

    @property
    def is_active(self):
        return self.status == "active"

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"
    __table_args__ = (
        db.Index("idx_login_attempts_identity_time", "identity_hash", "created_at"),
        db.Index("idx_login_attempts_ip_time", "ip_hash", "created_at"),
    )

    login_attempt_id = db.Column(db.Integer, primary_key=True)
    identity_hash = db.Column(db.String(64), nullable=False)
    ip_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
