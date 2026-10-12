"""Đọc/ghi lời nhắn banner bền vững trên volume /data."""
import json
import os
import tempfile
import threading

from config import Config

_LOCK = threading.Lock()
_BANNER_FILE = os.path.join(Config.DATA_DIR, "banner.json")


def _ensure_dir() -> None:
    os.makedirs(Config.DATA_DIR, exist_ok=True)


def get_banner() -> str:
    try:
        with open(_BANNER_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        message = str(data.get("message", "")).strip()
        return message or Config.DEFAULT_BANNER
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return Config.DEFAULT_BANNER


def set_banner(message: str) -> str:
    message = message.strip()
    _ensure_dir()
    with _LOCK:
        fd, tmp_path = tempfile.mkstemp(dir=Config.DATA_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"message": message}, fh, ensure_ascii=False)
            os.replace(tmp_path, _BANNER_FILE)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    return message
