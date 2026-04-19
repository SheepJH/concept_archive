"""Gemini API client with structured output."""
from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

from prompts import RESPONSE_SCHEMA


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def _client() -> genai.Client:
    api_key = os.environ["GEMINI_KEY"]
    return genai.Client(api_key=api_key)


async def generate_cards(concept: str, system_prompt: str, model: str | None = None) -> dict[str, Any]:
    """Call Gemini with system prompt + concept, return parsed JSON dict.

    The dict matches RESPONSE_SCHEMA: { title, tags[], cards[{id, main}] }.
    """
    client = _client()
    cfg = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        temperature=0.7,
    )

    resp = await client.aio.models.generate_content(
        model=model or DEFAULT_MODEL,
        contents=concept,
        config=cfg,
    )

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
