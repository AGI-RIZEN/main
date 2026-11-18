import secrets
from io import BytesIO
from pathlib import Path

import qrcode
from flask import current_app, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.certificates.models import Certificate
from app.extensions import db


def create_certificate(attempt):
    existing = attempt.certificate
    if existing is not None:
        return existing
    certificate = Certificate(
        user_id=attempt.user_id,
        attempt_id=attempt.attempt_id,
        certificate_number=f"CAP-{secrets.token_hex(6).upper()}",
        verification_code=secrets.token_urlsafe(18),
    )
    db.session.add(certificate)
    db.session.flush()
    certificate.certificate_file = _write_certificate(certificate, attempt)
    return certificate


def _write_certificate(certificate, attempt):
    directory = Path(current_app.config["MEDIA_ROOT"]) / "certificates"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{certificate.certificate_number}.pdf"
    path = directory / filename

    buffer = BytesIO()
    page_size = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size
    pdf.setFillColor(colors.HexColor("#f5f8ff"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#234b83"))
    pdf.setLineWidth(4)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#17375e"))
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(width / 2, height - 82, "CYBER AWARENESS PORTAL")
    pdf.setFillColor(colors.HexColor("#172b4d"))
    pdf.setFont("Helvetica-Bold", 29)
    pdf.drawCentredString(width / 2, height - 140, "CERTIFICATE OF COMPLETION")
    pdf.setFillColor(colors.HexColor("#4b5c75"))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 185, "This certificate is proudly presented to")
    pdf.setFillColor(colors.HexColor("#17375e"))
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(width / 2, height - 225, attempt.user.full_name)
    pdf.setFillColor(colors.HexColor("#4b5c75"))
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 262, "for successfully completing")
    pdf.setFillColor(colors.HexColor("#172b4d"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 292, attempt.quiz.quiz_title[:90])
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        width / 2,
        height - 326,
        f"Score: {attempt.percentage:.2f}%  |  Completed: {attempt.submitted_at.date().isoformat()}",
    )
    pdf.setFillColor(colors.HexColor("#4b5c75"))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(55, 55, f"Certificate number: {certificate.certificate_number}")
    pdf.drawString(55, 39, f"Verification code: {certificate.verification_code}")

    verify_url = url_for(
        "certificates.verify_certificate",
        code=certificate.verification_code,
        _external=True,
    )
    qr_image = qrcode.make(verify_url)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    pdf.drawImage(ImageReader(qr_buffer), width - 125, 35, width=75, height=75, mask="auto")
    pdf.showPage()
    pdf.save()
    path.write_bytes(buffer.getvalue())
    return f"certificates/{filename}"
