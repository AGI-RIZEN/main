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


TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "static" / "certificates" / "template.png"
TEMPLATE_IMAGE_SIZE = (1536, 1024)

# Pixel bounding boxes (against TEMPLATE_IMAGE_SIZE) of the baked-in
# {{User Name}} / {{Date}} placeholders in the artwork. Used to mask the
# placeholder text and centre the real value in the same spot.
NAME_BBOX = (538, 400, 1009, 479)
DATE_BBOX = (206, 850, 419, 899)


def _pdf_rect(pixel_bbox, width, height, pad=6):
    """Convert a top-left-origin pixel bbox (against TEMPLATE_IMAGE_SIZE) into
    a bottom-left-origin (x, y, w, h) rect in PDF points, padded on each side.
    """
    img_w, img_h = TEMPLATE_IMAGE_SIZE
    x0, y0, x1, y1 = pixel_bbox
    left = (x0 / img_w) * width - pad
    right = (x1 / img_w) * width + pad
    pdf_bottom = height - (y1 / img_h) * height - pad
    pdf_top = height - (y0 / img_h) * height + pad
    return left, pdf_bottom, right - left, pdf_top - pdf_bottom


def _fit_font_size(pdf, text, font, max_size, max_width, min_size=8):
    size = max_size
    while size > min_size and pdf.stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _draw_field(pdf, text, pixel_bbox, width, height, max_font_size, pad=6):
    x, y, w, h = _pdf_rect(pixel_bbox, width, height, pad=pad)
    pdf.setFillColor(colors.HexColor("#fffaf0"))
    pdf.setStrokeColor(colors.HexColor("#c8a240"))
    pdf.setLineWidth(1)
    pdf.roundRect(x, y, w, h, min(6, h / 2), fill=1, stroke=1)
    font = "Helvetica-BoldOblique"
    size = _fit_font_size(pdf, text, font, max_font_size, w - 12)
    pdf.setFillColor(colors.HexColor("#17375e"))
    pdf.setFont(font, size)
    pdf.drawCentredString(x + w / 2, y + h / 2 - size * 0.32, text)


def _write_certificate(certificate, attempt):
    directory = Path(current_app.config["MEDIA_ROOT"]) / "certificates"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{certificate.certificate_number}.pdf"
    path = directory / filename

    buffer = BytesIO()
    page_size = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    pdf.drawImage(ImageReader(str(TEMPLATE_PATH)), 0, 0, width=width, height=height)

    _draw_field(pdf, attempt.user.full_name, NAME_BBOX, width, height, max_font_size=20, pad=4)
    completed_on = attempt.submitted_at.date().isoformat() if attempt.submitted_at else ""
    _draw_field(pdf, completed_on, DATE_BBOX, width, height, max_font_size=13, pad=5)

    # Verification stamp in the bottom-left corner, over the ornamental border.
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#17375e"))
    pdf.roundRect(18, 18, 230, 34, 6, fill=1, stroke=1)
    pdf.setFillColor(colors.HexColor("#17375e"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(26, 40, f"Certificate no.: {certificate.certificate_number}")
    pdf.drawString(26, 26, f"Verification code: {certificate.verification_code}")

    verify_url = url_for(
        "certificates.verify_certificate",
        code=certificate.verification_code,
        _external=True,
    )
    qr_image = qrcode.make(verify_url)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#17375e"))
    pdf.roundRect(width - 92, 18, 74, 74, 6, fill=1, stroke=1)
    pdf.drawImage(ImageReader(qr_buffer), width - 85, 25, width=60, height=60, mask="auto")

    pdf.showPage()
    pdf.save()
    path.write_bytes(buffer.getvalue())
    return f"certificates/{filename}"
