import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DEBUG = env_bool("DEBUG", False)
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if (
        DATABASE_URL
        and DATABASE_URL != "sqlite:///:memory:"
        and DATABASE_URL.startswith("sqlite:///")
        and not DATABASE_URL.startswith("sqlite:////")
    ):
        DATABASE_PATH = Path(DATABASE_URL.removeprefix("sqlite:///"))
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (BASE_DIR / DATABASE_PATH).as_posix()
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///" + (BASE_DIR / "db.sqlite3").as_posix()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MEDIA_ROOT = str(BASE_DIR / "media")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    MAX_VIDEO_CONTENT_LENGTH = 210 * 1024 * 1024
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    WTF_CSRF_SSL_STRICT = False
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    try:
        GROQ_TIMEOUT_SECONDS = int(os.environ.get("GROQ_TIMEOUT_SECONDS", "30"))
    except ValueError as exc:
        raise RuntimeError("GROQ_TIMEOUT_SECONDS must be an integer.") from exc
    if not 1 <= GROQ_TIMEOUT_SECONDS <= 120:
        raise RuntimeError("GROQ_TIMEOUT_SECONDS must be between 1 and 120.")
    RSS_FEEDS = tuple(
        feed.strip()
        for feed in os.environ.get(
            "RSS_FEEDS",
            "https://feeds.feedburner.com/TheHackersNews,"
            "https://www.bleepingcomputer.com/feed/,"
            "https://krebsonsecurity.com/feed/",
        ).split(",")
        if feed.strip()
    )
    NEWS_REQUEST_TIMEOUT = 10
    NEWS_MAX_ITEMS_PER_FEED = 20
    LOGIN_THROTTLE_DISABLED = False
    LOGIN_THROTTLE_MAX_ATTEMPTS = 10
    LOGIN_THROTTLE_WINDOW_SECONDS = 900
    PASSWORD_RESET_MAX_AGE = 1800


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    WTF_CSRF_ENABLED = False
    LOGIN_THROTTLE_DISABLED = True
    GROQ_API_KEY = ""
    RSS_FEEDS = ()
