from app.extensions import db
from app.utils import utcnow


class AdminActivityLog(db.Model):
    __tablename__ = "admin_activity_logs"

    log_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    action = db.Column(db.String(200), nullable=False)
    module_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    admin = db.relationship("User")
