"""Minimal Telegram Bot API client (just what this project needs).

Uses raw HTTP via httpx so we don't pull in a heavy bot framework.
"""
from __future__ import annotations

import os

import httpx

TG_BASE = "https://api.telegram.org"


def _token() -> str:
    return os.environ["TG_TOKEN"]


async def send_message(
    chat_id: int,
    text: str,
    buttons: list[list[tuple[str, str]]] | None = None,
) -> None:
    """Send a text message. Optional `buttons` is rows of (label, callback_data)."""
    payload: dict = {"chat_id": chat_id, "text": text}
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": label, "callback_data": data} for label, data in row]
                for row in buttons
            ]
        }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{TG_BASE}/bot{_token()}/sendMessage",
            json=payload,
        )
        r.raise_for_status()


async def answer_callback(callback_query_id: str) -> None:
    """Acknowledge a button press so the loading spinner on the button stops."""
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            await c.post(
                f"{TG_BASE}/bot{_token()}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id},
            )
        except Exception:
            pass


async def send_upload_photo_action(chat_id: int) -> None:
    """Show a transient "uploading photo..." indicator. Lasts ~5s on the client."""
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            await c.post(
                f"{TG_BASE}/bot{_token()}/sendChatAction",
                json={"chat_id": chat_id, "action": "upload_photo"},
            )
        except Exception:
            pass  # non-critical UX hint


async def send_media_group(chat_id: int, image_urls: list[str], caption: str | None = None) -> None:
    """Send up to 10 photos as an album. Caption attaches to first photo."""
    if not (2 <= len(image_urls) <= 10):
        raise ValueError(f"sendMediaGroup needs 2-10 photos, got {len(image_urls)}")
    media: list[dict] = []
    for i, url in enumerate(image_urls):
        item: dict = {"type": "photo", "media": url}
        if i == 0 and caption:
            item["caption"] = caption
        media.append(item)
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            f"{TG_BASE}/bot{_token()}/sendMediaGroup",
            json={"chat_id": chat_id, "media": media},
        )
        r.raise_for_status()
