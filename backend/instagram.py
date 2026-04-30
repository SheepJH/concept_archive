"""Publish a carousel to Instagram via the Graph API.

Three steps:
  1. Create one IMAGE container per slide (is_carousel_item=true).
  2. Wait for each container's status_code == FINISHED.
  3. Create the parent CAROUSEL container (children=ids, caption=...).
  4. POST media_publish with creation_id=parent.
"""
from __future__ import annotations

import asyncio
import os
import time

import httpx

GRAPH_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def _env() -> tuple[str, str]:
    token = os.environ["IG_TOKEN"]
    user_id = os.environ["IG_USER_ID"]
    return token, user_id


async def _create_image_container(client: httpx.AsyncClient, ig_user_id: str, token: str, image_url: str) -> str:
    r = await client.post(
        f"{BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": token,
        },
    )
    r.raise_for_status()
    cid = r.json().get("id")
    if not cid:
        raise RuntimeError(f"Image container creation failed: {r.text}")
    return cid


async def _wait_until_ready(client: httpx.AsyncClient, container_id: str, token: str, timeout_s: int = 120) -> None:
    deadline = time.monotonic() + timeout_s
    delay = 1.5
    while True:
        r = await client.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
        )
        r.raise_for_status()
        body = r.json()
        status = body.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} failed: {body}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Container {container_id} not ready after {timeout_s}s: {body}")
        await asyncio.sleep(delay)
        delay = min(delay * 1.4, 5.0)


async def _create_carousel(client: httpx.AsyncClient, ig_user_id: str, token: str, child_ids: list[str], caption: str) -> str:
    r = await client.post(
        f"{BASE}/{ig_user_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": token,
        },
    )
    r.raise_for_status()
    cid = r.json().get("id")
    if not cid:
        raise RuntimeError(f"Carousel container creation failed: {r.text}")
    return cid


async def _publish(client: httpx.AsyncClient, ig_user_id: str, token: str, creation_id: str) -> str:
    r = await client.post(
        f"{BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
    )
    r.raise_for_status()
    pid = r.json().get("id")
    if not pid:
        raise RuntimeError(f"Publish failed: {r.text}")
    return pid


async def publish_carousel(image_urls: list[str], caption: str) -> str:
    """Publish carousel and return the resulting media id."""
    if not (2 <= len(image_urls) <= 10):
        raise ValueError(f"IG carousel needs 2-10 images, got {len(image_urls)}")

    token, ig_user_id = _env()
    timeout = httpx.Timeout(60.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Create children sequentially (cheap; avoids rate-limit edge cases).
        child_ids: list[str] = []
        for url in image_urls:
            cid = await _create_image_container(client, ig_user_id, token, url)
            child_ids.append(cid)

        # Wait for all children to finish processing in parallel.
        await asyncio.gather(*(_wait_until_ready(client, cid, token) for cid in child_ids))

        carousel_id = await _create_carousel(client, ig_user_id, token, child_ids, caption)
        await _wait_until_ready(client, carousel_id, token)

        return await _publish(client, ig_user_id, token, carousel_id)
