"""Object storage through the S3 API (boto3).

Locally this talks to MinIO; in the cloud set S3_ENDPOINT_URL="" and real AWS keys —
no code change. Storage failures are logged, not fatal: the interview still works,
we just lose the original file.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger(__name__)


@lru_cache
def _client():
    import boto3

    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url or None,  # None = real AWS S3
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
    )


def upload_bytes(key: str, data: bytes, content_type: str) -> str | None:
    """Store bytes under `key`. Returns the key, or None if storage is off/unavailable."""
    s = get_settings()
    if not s.storage_enabled:
        return None
    try:
        _client().put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type)
        return key
    except Exception as err:  # noqa: BLE001 - storage must never break the interview
        log.warning("upload of %s failed: %s", key, err)
        return None


def download_bytes(key: str) -> bytes:
    s = get_settings()
    return _client().get_object(Bucket=s.s3_bucket, Key=key)["Body"].read()
