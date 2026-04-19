"""FastAPI entrypoint for the card news pipeline.

Endpoints (all require Bearer token = API_SECRET):
  GET  /healthz                  - liveness probe
  POST /generate                 - concept -> JSON cards (preview, no IG)
  POST /publish                  - concept -> render -> upload -> IG publish
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import asyncio

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from gemini_client import generate_cards
from instagram import publish_carousel
from prompts import build_system_prompt, load_template_html
from renderer import (
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

app = FastAPI(title="card-news", version="0.1.0")


# Loaded once at startup ------------------------------------------------------
_TEMPLATES_HTML: dict[str, str] = {}
_TEMPLATE_CSS: dict[str, str] = {}
_SHARED_CSS: str = ""
_SYSTEM_PROMPT: str = ""


@app.on_event("startup")
def _startup() -> None:
    global _TEMPLATES_HTML, _TEMPLATE_CSS, _SHARED_CSS, _SYSTEM_PROMPT
    _TEMPLATES_HTML = load_template_html(TEMPLATES_DIR)
    _TEMPLATE_CSS = build_template_css_map(_TEMPLATES_HTML)
    _SHARED_CSS = load_shared_css(SHARED_DIR)
    _SYSTEM_PROMPT = build_system_prompt(_TEMPLATES_HTML)
    log.info("Loaded %d templates", len(_TEMPLATES_HTML))


# Auth ------------------------------------------------------------------------

def require_auth(authorization: str | None = Header(default=None)) -> None:
    secret = os.environ.get("API_SECRET")
    if not secret:
        raise HTTPException(500, "API_SECRET not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    if authorization.removeprefix("Bearer ").strip() != secret:
        raise HTTPException(401, "invalid token")


# Schemas ---------------------------------------------------------------------

class GenerateReq(BaseModel):
    concept: str = Field(..., min_length=1, max_length=500)
    model: str | None = None


class PublishReq(GenerateReq):
    extra_caption: str | None = None  # appended after title + tags


# Routes ----------------------------------------------------------------------

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "templates": len(_TEMPLATES_HTML)}


@app.post("/generate", dependencies=[Depends(require_auth)])
async def generate(req: GenerateReq) -> dict:
    log.info("generate concept=%r", req.concept)
    return await generate_cards(req.concept, _SYSTEM_PROMPT, req.model)


async def _do_publish(req: PublishReq) -> None:
    """The actual long-running pipeline. Runs in the background."""
    try:
        log.info("[bg] publish concept=%r", req.concept)
        result = await generate_cards(req.concept, _SYSTEM_PROMPT, req.model)
        title = result.get("title", "")
        tags = result.get("tags", []) or []
        cards = result["cards"]

        log.info("[bg] rendering %d cards", len(cards))
        pngs = await render_cards_to_png(cards, tags, _SHARED_CSS, _TEMPLATE_CSS)

        log.info("[bg] uploading to GCS")
        image_urls = upload_pngs(pngs)

        caption_parts = [title]
        if tags:
            caption_parts.append(" ".join(tags))
        if req.extra_caption:
            caption_parts.append(req.extra_caption)
        caption = "\n\n".join(p for p in caption_parts if p)

        log.info("[bg] publishing to IG (%d images)", len(image_urls))
        media_id = await publish_carousel(image_urls, caption)
        log.info("[bg] DONE media_id=%s title=%r", media_id, title)
    except Exception:
        log.exception("[bg] publish failed concept=%r", req.concept)


@app.post("/publish", dependencies=[Depends(require_auth)])
async def publish(req: PublishReq) -> dict:
    """Fire-and-forget: schedule the pipeline and return immediately.
    Check Cloud Run logs / Instagram for the actual result."""
    log.info("publish (queued) concept=%r", req.concept)
    asyncio.create_task(_do_publish(req))
    return {"ok": True, "queued": True, "concept": req.concept}
