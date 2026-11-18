from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.certificates.models import Certificate
from app.extensions import db
from app.utils import paginate

certificates = Blueprint("certificates", __name__)


@certificates.get("/certificates")
@login_required
def list_certificates():
    rows = paginate(
        select(Certificate)
        .where(Certificate.user_id == current_user.user_id)
        .order_by(Certificate.issue_date.desc())
    )
    return render_template("certificates.html", certificates=rows, pagination=rows)


@certificates.get("/certificates/<int:certificate_id>/download")
@login_required
def download_certificate(certificate_id):
    certificate = db.session.get(Certificate, certificate_id)
    if certificate is None:
        abort(404)
    if certificate.user_id != current_user.user_id and current_user.role != "admin":
        abort(403)
    if certificate.status != "valid" or not certificate.certificate_file:
        abort(404)
    path = Path(current_app.config["MEDIA_ROOT"]) / certificate.certificate_file
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=f"{certificate.certificate_number}.pdf")


@certificates.route("/certificates/verify", methods=["GET", "POST"])
@certificates.route("/certificates/verify/<code>", methods=["GET"])
def verify_certificate(code=None):
    verification = (code or request.form.get("verification_code", "")).strip()
    certificate = None
    if verification:
        certificate = db.session.scalar(
            db.select(Certificate).where(Certificate.verification_code == verification)
        )
    if request.method == "POST" and not verification:
        flash("Enter a verification code.", "error")
    return render_template(
        "certificate_verify.html",
        certificate=certificate,
        verification_code=verification,
        verified=bool(certificate and certificate.status == "valid" and certificate.attempt.result == "pass"),
    )
