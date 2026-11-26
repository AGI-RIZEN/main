from flask import Blueprint, jsonify, url_for
from sqlalchemy import select

from app.extensions import db
from app.learning.models import EventMedia, Infographic, Poster

api = Blueprint("api", __name__, url_prefix="/api")


def _media_url(path_or_url):
    """Resolve a stored image reference to an absolute URL for API consumers.

    Cloudinary uploads already store a full https:// URL; older rows
    (uploaded before Cloudinary was configured) store a relative path
    served from local disk via main.media_file.
    """
    if not path_or_url:
        return None
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return url_for("main.media_file", filename=path_or_url, _external=True)


@api.get("/posters")
def posters():
    rows = db.session.scalars(
        select(Poster).where(Poster.status == "published").order_by(Poster.created_at.desc())
    ).all()
    return jsonify([
        {
            "id": p.poster_id,
            "tone": p.tone,
            "icon": p.icon,
            "en": {"title": p.title_en, "tips": p.tip_list_en()},
            "hi": {"title": p.title_hi, "tips": p.tip_list_hi()},
        }
        for p in rows
    ])


@api.get("/infographics")
def infographics():
    rows = db.session.scalars(
        select(Infographic).where(Infographic.status == "published").order_by(Infographic.created_at.desc())
    ).all()
    return jsonify([
        {"id": i.infographic_id, "icon": i.icon, "title": i.title, "body": i.body}
        for i in rows
    ])


@api.get("/events")
def events():
    rows = db.session.scalars(
        select(EventMedia).where(EventMedia.status == "published").order_by(EventMedia.created_at.desc()).limit(10)
    ).all()
    return jsonify([
        {
            "id": e.media_id,
            "type": e.media_type,
            "title": e.title,
            "caption": e.caption,
            "image_url": _media_url(e.image_path),
            "video_url": e.video_url,
        }
        for e in rows
    ])
