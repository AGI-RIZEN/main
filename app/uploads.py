import io
import uuid
from pathlib import Path

from flask import current_app
from PIL import Image

from app.storage import cloudinary_enabled

Image.MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def load_upload(file_storage, max_edge=4000):
    if file_storage is None or not file_storage.filename:
        raise ValueError("Choose an image file.")
    extension = ""
    if "." in file_storage.filename:
        extension = file_storage.filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PNG, JPG, and WEBP images are allowed.")
    file_storage.stream.seek(0)
    try:
        image = Image.open(file_storage.stream)
        image.load()
    except Exception as exc:
        raise ValueError("That file is not a valid image.") from exc
    if image.width > max_edge or image.height > max_edge:
        raise ValueError("That image is too large.")
    if image.width < 20 or image.height < 20:
        raise ValueError("That image is too small.")
    return image.convert("RGB")


def store_image(image, folder_name):
    """Save a validated PIL image and return a path or URL to serve it from.

    Uploads to Cloudinary when configured (durable across redeploys); falls
    back to local disk under MEDIA_ROOT otherwise, matching the behaviour of
    app.storage.upload_video. Templates resolve either form via the shared
    media_url() helper.
    """
    if cloudinary_enabled():
        import cloudinary.uploader
        from cloudinary.exceptions import Error as CloudinaryError

        from app.storage import _configure_cloudinary

        _configure_cloudinary()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        try:
            result = cloudinary.uploader.upload(
                buffer,
                resource_type="image",
                folder=f"cleanclick/{folder_name}",
                public_id=uuid.uuid4().hex,
            )
        except (CloudinaryError, OSError) as exc:
            raise ValueError("Could not upload the image. Please try again.") from exc
        return result["secure_url"]

    directory = Path(current_app.config["MEDIA_ROOT"]) / folder_name
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    image.save(directory / filename, format="PNG")
    return f"{folder_name}/{filename}"
