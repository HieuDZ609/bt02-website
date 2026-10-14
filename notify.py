"""Điều phối thông báo khách tới điện thoại qua mọi kênh đang bật.

Chạy song song Discord Webhook và Telegram Bot (nếu đều được cấu hình).
Trả True nếu ít nhất một kênh gửi thành công.
"""
import logging

from config import Config
from discord_notify import send_message as send_discord
from telegram_notify import send_message as send_telegram

log = logging.getLogger("notify")


def send_message(text: str) -> bool:
    delivered = False

    if Config.NOTIFY_DISCORD:
        if send_discord(text):
            delivered = True
    else:
        log.info("Kênh Discord chưa cấu hình, bỏ qua.")

    if Config.NOTIFY_TELEGRAM:
        if send_telegram(text):
            delivered = True
    else:
        log.info("Kênh Telegram chưa cấu hình, bỏ qua.")

    return delivered
