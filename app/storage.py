import mimetypes
import uuid

from flask import current_app

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}
MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB


def s3_enabled():
    cfg = current_app.config
    return bool(cfg.get("AWS_S3_BUCKET") and cfg.get("AWS_ACCESS_KEY_ID") and cfg.get("AWS_SECRET_ACCESS_KEY"))


def _client():
    import boto3

    cfg = current_app.config
    kwargs = {
        "aws_access_key_id": cfg["AWS_ACCESS_KEY_ID"],
        "aws_secret_access_key": cfg["AWS_SECRET_ACCESS_KEY"],
    }
    if cfg.get("AWS_S3_REGION"):
        kwargs["region_name"] = cfg["AWS_S3_REGION"]
    if cfg.get("AWS_S3_ENDPOINT_URL"):
        kwargs["endpoint_url"] = cfg["AWS_S3_ENDPOINT_URL"]
    return boto3.client("s3", **kwargs)


def _public_url(key):
    cfg = current_app.config
    base = cfg.get("AWS_S3_PUBLIC_BASE_URL")
    if base:
        return f"{base.rstrip('/')}/{key}"
    endpoint = cfg.get("AWS_S3_ENDPOINT_URL")
    bucket = cfg["AWS_S3_BUCKET"]
    if endpoint:
        return f"{endpoint.rstrip('/')}/{bucket}/{key}"
    region = cfg.get("AWS_S3_REGION") or "us-east-1"
    if region == "us-east-1":
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def upload_video(file_storage, folder_name):
    """Upload a video file to S3 and return its public URL.

    Raises ValueError with a user-safe message on any failure, including
    when S3 is not configured, so callers can flash it directly.
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
    if not s3_enabled():
        raise ValueError(
            "Video file uploads are not configured yet. Paste a video link instead, "
            "or ask an administrator to set the AWS_S3_BUCKET settings."
        )
    key = f"{folder_name}/{uuid.uuid4().hex}.{extension}"
    content_type = mimetypes.guess_type(file_storage.filename)[0] or "application/octet-stream"
    try:
        from botocore.exceptions import BotoCoreError, ClientError

        _client().upload_fileobj(
            file_storage.stream,
            current_app.config["AWS_S3_BUCKET"],
            key,
            ExtraArgs={"ContentType": content_type},
        )
    except (BotoCoreError, ClientError) as exc:
        raise ValueError("Could not upload the video. Please try again.") from exc
    return _public_url(key)
