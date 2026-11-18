import uuid
from pathlib import Path

from flask import current_app
from PIL import Image

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
    directory = Path(current_app.config["MEDIA_ROOT"]) / folder_name
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    image.save(directory / filename, format="PNG")
    return f"{folder_name}/{filename}"
