"""Gemini API client with structured output."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from prompts import RESPONSE_SCHEMA


MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
MAX_RETRIES = 4
RETRY_BACKOFF_SEC = (2, 5, 10, 20)


def _client() -> genai.Client:
    api_key = os.environ["GEMINI_KEY"]
    return genai.Client(api_key=api_key)


async def generate_cards(concept: str, system_prompt: str) -> dict[str, Any]:
    """Call Gemini with system prompt + concept, return parsed JSON dict.

    The dict matches RESPONSE_SCHEMA: { title, tags[], cards[{id, main}] }.
    Retries on 503/UNAVAILABLE (free-tier capacity spikes).
    """
    client = _client()
    cfg = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        temperature=0.7,
    )

    resp = None
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.aio.models.generate_content(
                model=MODEL,
                contents=concept,
                config=cfg,
            )
            break
        except genai_errors.ServerError as e:
            last_err = e
            status = getattr(e, "code", None)
            if status in (503, 429) and attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_SEC[attempt])
                continue
            raise
    if resp is None:
        raise RuntimeError(f"Gemini retries exhausted: {last_err}")

    text = resp.text or ""
    if not text.strip():
        raise RuntimeError("Gemini returned empty response")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini returned non-JSON: {text[:200]}") from e

    # Defensive: cards/tags may come back as strings even with structured output.
    if isinstance(data.get("cards"), str):
        data["cards"] = json.loads(data["cards"])
    if isinstance(data.get("tags"), str):
        data["tags"] = json.loads(data["tags"])

    if not isinstance(data.get("cards"), list) or len(data["cards"]) != 8:
        raise RuntimeError(
            f"Gemini returned invalid card count: {len(data.get('cards') or [])}"
        )

    return data
