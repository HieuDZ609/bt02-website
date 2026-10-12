"""Cấu hình tập trung, đọc từ biến môi trường (.env khi chạy local)."""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class Config:
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "").strip()
    SECRET_KEY: str = os.getenv("SECRET_KEY", "").strip() or secrets.token_hex(32)

    PORT: int = _int("PORT", 8000)
    MAX_LEN: int = _int("MAX_LEN", 500)
    RATE_LIMIT_SECONDS: int = _int("RATE_LIMIT_SECONDS", 5)
    LOGIN_MAX_ATTEMPTS: int = _int("LOGIN_MAX_ATTEMPTS", 5)
    LOGIN_LOCKOUT_SECONDS: int = _int("LOGIN_LOCKOUT_SECONDS", 60)

    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    DEFAULT_BANNER: str = os.getenv(
        "DEFAULT_BANNER",
        "Chào mừng bạn đến với website cá nhân của mình!",
    )

    NOTIFY_ENABLED: bool = bool(DISCORD_WEBHOOK_URL)