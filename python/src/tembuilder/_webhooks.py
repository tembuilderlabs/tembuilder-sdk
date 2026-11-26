from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Iterable, Mapping
from typing import Any

from ._errors import WebhookVerificationError

SIGNATURE_HEADER = "tembuilder-signature"
TIMESTAMP_HEADER = "tembuilder-timestamp"
DEFAULT_TOLERANCE_SECONDS = 300


def verify_webhook(
    *,
    payload: str | bytes,
    headers: Mapping[str, str] | Iterable[tuple[str, str]],
    secret: str,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    """Verifies a webhook request and returns the parsed event.

    The signature is ``v1=`` + hex(HMAC-SHA256(secret, f"{timestamp}.{raw_body}")). ``payload`` must be the
    raw body exactly as received. Raises WebhookVerificationError when a header is missing, the timestamp is
    outside the tolerance, the signature does not match or the body is not JSON.
    """
    timestamp = _header(headers, TIMESTAMP_HEADER)
    signatures = _header(headers, SIGNATURE_HEADER)
    if not timestamp or not signatures:
        raise WebhookVerificationError("missing Tembuilder-Timestamp or Tembuilder-Signature header")
    if not timestamp.isdigit():
        raise WebhookVerificationError("Tembuilder-Timestamp is not a unix timestamp")
    current = int(now if now is not None else time.time())
    if abs(current - int(timestamp)) > tolerance_seconds:
        raise WebhookVerificationError("webhook timestamp is outside the accepted tolerance")

    key = _decode_secret(secret)
    body = payload.encode("utf-8") if isinstance(payload, str) else payload
    expected = "v1=" + hmac.new(key, timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(candidate.strip(), expected) for candidate in signatures.split(",")):
        raise WebhookVerificationError("webhook signature does not match")

    try:
        event = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise WebhookVerificationError("webhook body is not valid JSON") from error
    if not isinstance(event, dict):
        raise WebhookVerificationError("webhook body is not a JSON object")
    return event


def _decode_secret(secret: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(secret + "=" * (-len(secret) % 4))
    except (binascii.Error, ValueError) as error:
        raise WebhookVerificationError("webhook secret is not base64url") from error
    if not key:
        raise WebhookVerificationError("webhook secret is empty or not base64url")
    return key


def _header(headers: Mapping[str, str] | Iterable[tuple[str, str]], name: str) -> str | None:
    items = headers.items() if isinstance(headers, Mapping) else headers
    values = [value for key, value in items if key.lower() == name]
    return ",".join(values) if values else None
