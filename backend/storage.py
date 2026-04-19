"""Upload PNGs to Google Cloud Storage and return public URLs."""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from google.cloud import storage

_BUCKET_NAME = os.environ.get("GCS_BUCKET")


def _bucket() -> storage.Bucket:
    if not _BUCKET_NAME:
        raise RuntimeError("GCS_BUCKET env var not set")
    client = storage.Client()
    return client.bucket(_BUCKET_NAME)


def upload_pngs(pngs: list[bytes], prefix: str | None = None) -> list[str]:
    """Upload PNGs in parallel. Returns public HTTPS URLs (objects must be world-readable
    via bucket-level IAM allUsers:roles/storage.objectViewer)."""
    bucket = _bucket()
    job_id = prefix or uuid.uuid4().hex[:12]

    def _upload(idx_blob: tuple[int, bytes]) -> str:
        idx, data = idx_blob
        name = f"runs/{job_id}/{idx + 1:02d}.png"
        blob = bucket.blob(name)
        blob.cache_control = "public, max-age=3600"
        blob.upload_from_string(data, content_type="image/png")
        # URL ends in .png — important: Instagram rejects redirected/extension-less URLs.
        return f"https://storage.googleapis.com/{bucket.name}/{name}"

    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(_upload, list(enumerate(pngs))))
