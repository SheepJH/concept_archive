"""FastAPI entrypoint for the card news pipeline.

Endpoint:
  POST /tg  - Telegram webhook (auth via X-Telegram-Bot-Api-Secret-Token = API_SECRET)
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request

import telegram as tg
from gemini_client import generate_cards
from instagram import publish_carousel
from prompts import build_system_prompt, load_manifest, load_template_html
from renderer import (
    build_card_by_id,
    build_template_css_map,
    load_shared_css,
    render_cards_to_png,
)
from storage import upload_pngs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("cardnews")

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
SHARED_DIR = ROOT / "shared"

# Loaded once at startup ------------------------------------------------------
_CARDS: list[dict] = []
_STAGES: list[dict] = []
_CARD_BY_ID: dict[str, dict] = {}
_TEMPLATES_HTML: dict[str, str] = {}
_TEMPLATE_CSS: dict[str, str] = {}
_SHARED_CSS: str = ""
_SYSTEM_PROMPT: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _CARDS, _STAGES, _CARD_BY_ID, _TEMPLATES_HTML, _TEMPLATE_CSS, _SHARED_CSS, _SYSTEM_PROMPT
    manifest = load_manifest(TEMPLATES_DIR)
    _CARDS = manifest["cards"]
    _STAGES = manifest["stages"]
    _CARD_BY_ID = build_card_by_id(_CARDS)
    _TEMPLATES_HTML = load_template_html(TEMPLATES_DIR, _CARDS)
    _TEMPLATE_CSS = build_template_css_map(_TEMPLATES_HTML)
    _SHARED_CSS = load_shared_css(SHARED_DIR)
    _SYSTEM_PROMPT = build_system_prompt(_TEMPLATES_HTML, _CARDS, _STAGES)
    log.info("Loaded %d templates", len(_TEMPLATES_HTML))
    yield


app = FastAPI(title="card-news", version="0.1.0", lifespan=lifespan)


# Telegram bot ----------------------------------------------------------------

# Last successful job per chat (for "다시 만들기" / "인스타 아카이브" buttons).
# Lost on Cloud Run cold start — that's fine; user just re-sends the concept.
_LAST_JOBS: dict[int, dict] = {}

_ACTION_BUTTONS = [[("🔁 다시 만들기", "redo"), ("📤 인스타 아카이브", "archive")]]


async def _keep_typing(chat_id: int) -> None:
    """Refresh the 'upload_photo' indicator every 4s until cancelled."""
    while True:
        await tg.send_upload_photo_action(chat_id)
        await asyncio.sleep(4)


def _short_err(e: Exception, limit: int = 250) -> str:
    s = f"{type(e).__name__}: {e}"
    return s if len(s) <= limit else s[:limit] + "…"


async def _notify_err(chat_id: int, stage: str, e: Exception) -> None:
    """Send a stage-tagged error message to the user. Best-effort."""
    try:
        await tg.send_message(chat_id, f"❌ [{stage}] 실패\n{_short_err(e)}")
    except Exception:
        log.exception("[tg] failed to send error notification")


async def _do_telegram_publish(chat_id: int, concept: str) -> None:
    """Render the cards and send them back to the Telegram chat as an album.
    Each pipeline stage notifies the chat on failure with a tag identifying which stage failed."""
    typing_task = asyncio.create_task(_keep_typing(chat_id))
    try:
        # Stage 1: Gemini ---------------------------------------------------
        try:
            log.info("[tg] generate concept=%r", concept)
            result = await generate_cards(concept, _SYSTEM_PROMPT)
            title = result.get("title", "")
            tags = result.get("tags", []) or []
            cards = result["cards"]
        except Exception as e:
            log.exception("[tg] gemini failed concept=%r", concept)
            await _notify_err(chat_id, "Gemini 생성", e)
            return

        # Stage 2: Playwright render ---------------------------------------
        try:
            log.info("[tg] rendering %d cards", len(cards))
            pngs = await render_cards_to_png(cards, tags, _SHARED_CSS, _TEMPLATE_CSS, _CARD_BY_ID)
        except Exception as e:
            log.exception("[tg] render failed")
            await _notify_err(chat_id, "카드 렌더링", e)
            return

        # Stage 3: GCS upload ----------------------------------------------
        try:
            log.info("[tg] uploading to GCS")
            image_urls = upload_pngs(pngs)
        except Exception as e:
            log.exception("[tg] gcs upload failed")
            await _notify_err(chat_id, "GCS 업로드", e)
            return

        caption_parts = [title]
        if tags:
            caption_parts.append(" ".join(tags))
        caption = "\n\n".join(p for p in caption_parts if p)

        # Stage 4: Telegram send -------------------------------------------
        try:
            log.info("[tg] sending media group (%d photos)", len(image_urls))
            await tg.send_media_group(chat_id, image_urls, caption=caption)
        except Exception as e:
            log.exception("[tg] media group send failed")
            await _notify_err(chat_id, "텔레그램 전송", e)
            return

        _LAST_JOBS[chat_id] = {
            "concept": concept,
            "image_urls": image_urls,
            "caption": caption,
        }
        try:
            await tg.send_message(chat_id, "다음 작업을 선택하세요.", buttons=_ACTION_BUTTONS)
        except Exception:
            log.exception("[tg] failed to send action buttons (non-fatal)")
        log.info("[tg] DONE title=%r", title)
    finally:
        typing_task.cancel()


async def _do_telegram_archive(chat_id: int, image_urls: list[str], caption: str) -> None:
    """Publish the previously-generated images to Instagram as a carousel."""
    try:
        log.info("[tg] archiving to IG (%d images)", len(image_urls))
        media_id = await publish_carousel(image_urls, caption)
        log.info("[tg] IG DONE media_id=%s", media_id)
        await tg.send_message(chat_id, "✅ 인스타 아카이브 완료!")
    except Exception as e:
        log.exception("[tg] archive failed")
        await _notify_err(chat_id, "인스타 발행", e)


@app.post("/tg")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """Telegram webhook. Auth via the secret_token set when registering the webhook
    (we reuse API_SECRET as that token)."""
    expected = os.environ.get("API_SECRET")
    if not expected or x_telegram_bot_api_secret_token != expected:
        raise HTTPException(401, "invalid secret token")

    update = await request.json()

    # Handle inline-button presses ----------------------------------------
    cb = update.get("callback_query")
    if cb:
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        await tg.answer_callback(cb["id"])
        job = _LAST_JOBS.get(chat_id)
        if not job:
            await tg.send_message(chat_id, "⚠️ 세션이 만료됐어요. 개념을 다시 보내주세요.")
            return {"ok": True}
        if data == "redo":
            await tg.send_message(chat_id, f"🔁 다시 만들고 있어요: {job['concept']}")
            asyncio.create_task(_do_telegram_publish(chat_id, job["concept"]))
        elif data == "archive":
            await tg.send_message(chat_id, "📤 인스타에 올리는 중... (1~2분)")
            asyncio.create_task(
                _do_telegram_archive(chat_id, job["image_urls"], job["caption"])
            )
        return {"ok": True}

    # Handle text messages ------------------------------------------------
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    if not text or text.startswith("/start") or text.startswith("/help"):
        await tg.send_message(
            chat_id,
            "모르는 개념을 보내주시면 카드뉴스 8장을 만들어 답장해드려요. 예) '더닝-크루거 효과'",
        )
        return {"ok": True}

    if len(text) > 500:
        await tg.send_message(chat_id, "개념이 너무 길어요 (500자 이내).")
        return {"ok": True}

    await tg.send_message(chat_id, "⏳ 생성 중... (1~2분 정도 걸려요)")
    asyncio.create_task(_do_telegram_publish(chat_id, text))
    return {"ok": True}
