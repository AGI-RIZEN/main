import uuid

from flask import current_app

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}
MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB


def cloudinary_enabled():
    cfg = current_app.config
    return bool(cfg.get("CLOUDINARY_CLOUD_NAME") and cfg.get("CLOUDINARY_API_KEY") and cfg.get("CLOUDINARY_API_SECRET"))


def _configure_cloudinary():
    import cloudinary

    cfg = current_app.config
    cloudinary.config(
        cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
        api_key=cfg["CLOUDINARY_API_KEY"],
        api_secret=cfg["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def upload_video(file_storage, folder_name):
    """Upload a video file to Cloudinary and return its public HTTPS URL.

    Raises ValueError with a user-safe message on any failure, including
    when Cloudinary is not configured, so callers can flash it directly.
    """
    if file_storage is None or not file_storage.filename:
        raise ValueError("Choose a video file.")
    extension = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError("Only MP4, WEBM, MOV, and M4V videos are allowed.")
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise ValueError("That video file is empty.")
    if size > MAX_VIDEO_BYTES:
        raise ValueError("That video is too large (200 MB max). Use a video link instead.")
    if not cloudinary_enabled():
        raise ValueError(
            "Video file uploads are not configured yet. Paste a video link instead, "
            "or ask an administrator to set the CLOUDINARY_* settings."
        )
    _configure_cloudinary()
    import cloudinary.uploader
    from cloudinary.exceptions import Error as CloudinaryError

    try:
        result = cloudinary.uploader.upload(
            file_storage.stream,
            resource_type="video",
            folder=f"cleanclick/{folder_name}",
            public_id=uuid.uuid4().hex,
        )
    except (CloudinaryError, OSError) as exc:
        raise ValueError("Could not upload the video. Please try again.") from exc
    return result["secure_url"]
