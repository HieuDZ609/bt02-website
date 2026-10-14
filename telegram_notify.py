"""Đẩy thông báo khách gửi tới điện thoại admin qua Telegram Bot API (sendMessage).

BOT_TOKEN là bí mật, chỉ nằm trong .env, không bao giờ trong image.
"""
import logging

import requests

from config import Config

log = logging.getLogger("telegram")


def api_url(method: str) -> str:
    """URL gọi Bot API cho một method (sendMessage, getUpdates...)."""
    return f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/{method}"


def send_message(text: str) -> bool:
    """Gửi thông điệp tới chat admin. Trả True nếu Telegram nhận thành công."""
    if not Config.NOTIFY_TELEGRAM:
        log.warning("Bỏ qua gửi Telegram: chưa có TELEGRAM_BOT_TOKEN/CHAT_ID.")
        return False
    try:
        resp = requests.post(
            api_url("sendMessage"),
            json={"chat_id": Config.TELEGRAM_CHAT_ID, "text": text},
            timeout=15,
        )
        ok = 200 <= resp.status_code < 300 and bool(resp.json().get("ok"))
        if not ok:
            log.warning("Telegram trả %s: %s", resp.status_code, resp.text[:200])
        return ok
    except (requests.RequestException, ValueError) as exc:
        log.warning("Gửi Telegram thất bại: %s", exc)
        return False
