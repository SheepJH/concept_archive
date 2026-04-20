"""Render generated card HTML to 1080×1350 PNG via Playwright."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Iterable

from playwright.async_api import async_playwright

from prompts import CARD_BY_ID

CANVAS_W = 1080
CANVAS_H = 1350

_STYLE_RE = re.compile(r"<style>(.*?)</style>", re.DOTALL | re.IGNORECASE)


def extract_template_css(template_html: str) -> str:
    """Pull the inline <style> block from a template HTML file."""
    m = _STYLE_RE.search(template_html)
    return m.group(1).strip() if m else ""


def build_template_css_map(template_html_by_id: dict[str, str]) -> dict[str, str]:
    return {cid: extract_template_css(html) for cid, html in template_html_by_id.items()}


def build_card_html(
    card: dict,
    page: int,
    total: int,
    tags: list[str],
    shared_css: str,
    template_css_by_id: dict[str, str],
) -> str:
    """Mirror of buildSrcdoc() in index.html, fully self-contained (no external links)."""
    meta = CARD_BY_ID.get(card["id"])
    if not meta:
        raise ValueError(f"Unknown card id: {card['id']}")
    pg = f"{page:02d}"
    tt = f"{total:02d}"
    tag_str = " ".join(tags) if tags else ""
    tpl_css = template_css_by_id.get(card["id"], "")
    main_html = card["main"]
    page_display = f"{pg} / {tt}"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
{shared_css}
{tpl_css}
</style>
</head>
<body data-page="{pg}" data-total="{tt}">
  <div class="card {meta['cls']}">
    <div class="meta-top">
      <span class="label">{meta['label']}</span>
      <span class="num page-display">{page_display}</span>
    </div>
    <div class="main">{main_html}</div>
    <div class="meta-bottom">
      <span class="brand">@what_is_this.zip</span>
      <span>{tag_str}</span>
    </div>
  </div>
</body>
</html>"""


async def render_cards_to_png(
    cards: list[dict],
    tags: list[str],
    shared_css: str,
    template_css_by_id: dict[str, str],
) -> list[bytes]:
    """Render every card to a PNG in parallel, return list of PNG byte blobs."""
    total = len(cards)
    htmls = [
        build_card_html(card, i + 1, total, tags, shared_css, template_css_by_id)
        for i, card in enumerate(cards)
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            context = await browser.new_context(
                viewport={"width": CANVAS_W, "height": CANVAS_H},
                # 2x supersampling: render at 2160x2700 so IG's downscale to 1080
                # produces sharper text antialiasing.
                device_scale_factor=2,
            )
            try:
                async def render_one(html: str) -> bytes:
                    page = await context.new_page()
                    try:
                        await page.set_content(html, wait_until="networkidle")
                        # Wait for fonts (Pretendard from CDN) to load.
                        await page.evaluate("document.fonts ? document.fonts.ready : null")
                        return await page.screenshot(type="png", full_page=False, omit_background=False)
                    finally:
                        await page.close()

                # Render serially to keep memory low on Cloud Run.
                results: list[bytes] = []
                for html in htmls:
                    results.append(await render_one(html))
                return results
            finally:
                await context.close()
        finally:
            await browser.close()


def load_shared_css(shared_dir: Path) -> str:
    return (shared_dir / "styles.css").read_text(encoding="utf-8")
