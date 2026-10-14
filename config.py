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

    # Telegram Bot: chiều ra (khách -> điện thoại) và chiều vào (admin -> banner)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_ADMIN_ID: str = os.getenv("TELEGRAM_ADMIN_ID", "").strip()
    # Nơi nhận thông báo khách; mặc định nhận chung chat với admin
    TELEGRAM_CHAT_ID: str = (
        os.getenv("TELEGRAM_CHAT_ID", "").strip() or TELEGRAM_ADMIN_ID
    )

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

    NOTIFY_DISCORD: bool = bool(DISCORD_WEBHOOK_URL)
    NOTIFY_TELEGRAM: bool = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    NOTIFY_ENABLED: bool = NOTIFY_DISCORD or NOTIFY_TELEGRAM