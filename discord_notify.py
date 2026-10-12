"""Đẩy thông báo khách gửi tới điện thoại admin qua Discord Webhook.

Webhook URL là bí mật, chỉ nằm trong .env, không bao giờ trong image.
"""
import logging

import requests

from config import Config

log = logging.getLogger("discord")


def send_message(text: str) -> bool:
    """Gửi thông điệp qua webhook. Trả True nếu Discord nhận thành công (HTTP 2xx)."""
    if not Config.NOTIFY_ENABLED:
        log.warning("Bỏ qua gửi Discord: chưa có DISCORD_WEBHOOK_URL.")
        return False
    try:
        resp = requests.post(
            Config.DISCORD_WEBHOOK_URL,
            json={"content": text},
            timeout=15,
        )
        ok = 200 <= resp.status_code < 300
        if not ok:
            log.warning("Discord webhook trả %s: %s", resp.status_code, resp.text[:200])
        return ok
    except requests.RequestException as exc:
        log.warning("Discord webhook thất bại: %s", exc)
        return False