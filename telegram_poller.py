"""Long-poll Telegram getUpdates: admin gửi /banner <nội dung> -> cập nhật banner.

Chạy trong 1 thread nền (an toàn với gunicorn --workers 1). Chỉ nhận tin từ
TELEGRAM_ADMIN_ID; tin từ người khác bị bỏ qua. Offset lưu tại /data để không
xử lý lại sau khi restart.
"""
import json
import logging
import os
import tempfile
import threading
import time

import requests

from config import Config
from storage import set_banner
from telegram_notify import api_url

log = logging.getLogger("telegram.poller")

_OFFSET_FILE = os.path.join(Config.DATA_DIR, "telegram_offset.json")
_COMMAND = "/banner"
_HELP_COMMANDS = ("/start", "/id")

_thread_started = False
_alive = False
_lock = threading.Lock()


def is_alive() -> bool:
    return _alive


def _load_offset() -> int | None:
    try:
        with open(_OFFSET_FILE, "r", encoding="utf-8") as fh:
            return int(json.load(fh).get("offset", 0))
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def _save_offset(offset: int) -> None:
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=Config.DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"offset": offset}, fh)
        os.replace(tmp_path, _OFFSET_FILE)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _get_updates(offset: int, timeout: int) -> list:
    resp = requests.get(
        api_url("getUpdates"),
        params={"offset": offset, "timeout": timeout},
        timeout=timeout + 10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"getUpdates lỗi: {data}")
    return data.get("result", [])


def _delete_webhook() -> None:
    try:
        requests.get(api_url("deleteWebhook"), timeout=10)
    except (requests.RequestException, ValueError) as exc:
        log.warning("deleteWebhook thất bại: %s", exc)


def _send_reply(chat_id, text: str) -> None:
    try:
        requests.post(
            api_url("sendMessage"),
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except (requests.RequestException, ValueError) as exc:
        log.warning("Trả lời Telegram thất bại: %s", exc)


def _is_admin(chat_id) -> bool:
    admin = Config.TELEGRAM_ADMIN_ID
    return bool(admin) and str(chat_id) == str(admin)


def _handle(message: dict) -> None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not text:
        return
    if not _is_admin(chat_id):
        log.info("Bỏ qua tin từ chat không phải admin: %s", chat_id)
        return
    if text in _HELP_COMMANDS:
        _send_reply(
            chat_id,
            f"Chào admin! chat_id của bạn: {chat_id}\n"
            f"Đổi banner trang chủ: /banner <nội dung>",
        )
        return
    if not text.lower().startswith(_COMMAND):
        return

    content = text[len(_COMMAND):].strip()
    if not content:
        _send_reply(chat_id, "Dùng: /banner <nội dung>")
        return
    if len(content) > Config.MAX_LEN:
        _send_reply(chat_id, f"Nội dung tối đa {Config.MAX_LEN} ký tự.")
        return

    set_banner(content)
    log.info("Admin cập nhật banner qua Telegram: %s", content[:60])
    _send_reply(chat_id, "✅ Đã cập nhật banner.")


def _init_offset() -> int:
    saved = _load_offset()
    if saved is not None:
        return saved
    # Lần đầu chạy: bỏ qua backlog, chỉ xử lý tin mới để không set banner bằng tin cũ.
    try:
        updates = _get_updates(offset=-1, timeout=0)
        if updates:
            return updates[-1]["update_id"] + 1
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        log.warning("Không lấy được backlog ban đầu: %s", exc)
    return 0


def _loop() -> None:
    global _alive
    _alive = True
    _delete_webhook()
    offset = _init_offset()
    _save_offset(offset)
    log.info("Telegram poller khởi động, offset=%s", offset)

    while True:
        try:
            updates = _get_updates(offset=offset, timeout=25)
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if msg:
                    try:
                        _handle(msg)
                    except Exception:  # 1 tin lỗi không được làm chết poller
                        log.exception("Lỗi xử lý tin Telegram")
                _save_offset(offset)
        except Exception as exc:
            log.warning("Vòng poll lỗi: %s", exc)
            time.sleep(5)


def start() -> None:
    """Khởi động poller đúng 1 lần (idempotent). Không làm gì nếu thiếu cấu hình."""
    global _thread_started
    if not Config.NOTIFY_TELEGRAM:
        log.warning("Không khởi động Telegram poller: thiếu cấu hình.")
        return
    with _lock:
        if _thread_started:
            return
        _thread_started = True
    threading.Thread(target=_loop, name="telegram-poller", daemon=True).start()
