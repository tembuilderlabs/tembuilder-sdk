from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any

import pytest
from helpers import load_contract

from tembuilder import WebhookVerificationError, verify_webhook

SUITE = load_contract("webhooks.json")


def headers_for(vector: dict[str, Any]) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if vector["timestamp"] is not None:
        headers["Tembuilder-Timestamp"] = vector["timestamp"]
    if vector["signature"] is not None:
        headers["Tembuilder-Signature"] = vector["signature"]
    return headers


@pytest.mark.parametrize("vector", [pytest.param(v, id=v["name"]) for v in SUITE["vectors"]])
def test_shared_vectors(vector: dict[str, Any]) -> None:
    def verify() -> dict[str, Any]:
        return verify_webhook(
            payload=vector["body"],
            headers=headers_for(vector),
            secret=SUITE["secret"],
            tolerance_seconds=SUITE["tolerance_seconds"],
            now=vector["now"],
        )

    if vector["valid"]:
        assert verify() == __import__("json").loads(vector["body"])
    else:
        with pytest.raises(WebhookVerificationError):
            verify()


VALID = SUITE["vectors"][0]


def test_accepts_bytes_and_header_pairs() -> None:
    event = verify_webhook(
        payload=VALID["body"].encode(),
        headers=[("tembuilder-timestamp", VALID["timestamp"]), ("tembuilder-signature", VALID["signature"])],
        secret=SUITE["secret"],
        now=VALID["now"],
    )
    assert event["type"] == "renders.status"


def sign(body: str, timestamp: str) -> str:
    key = base64.urlsafe_b64decode(SUITE["secret"] + "==")
    return "v1=" + hmac.new(key, f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


def test_uses_current_time_by_default() -> None:
    now = str(int(time.time()))
    body = '{"api_version":"2026-09-12","type":"webhook.test","data":{"message":"hi"}}'
    event = verify_webhook(
        payload=body,
        headers={"Tembuilder-Timestamp": now, "Tembuilder-Signature": sign(body, now)},
        secret=SUITE["secret"],
    )
    assert event["data"] == {"message": "hi"}


def test_rejects_signed_non_object_json() -> None:
    body = "[1, 2]"
    with pytest.raises(WebhookVerificationError, match="not a JSON object"):
        verify_webhook(
            payload=body,
            headers={
                "Tembuilder-Timestamp": VALID["timestamp"],
                "Tembuilder-Signature": sign(body, VALID["timestamp"]),
            },
            secret=SUITE["secret"],
            now=VALID["now"],
        )


@pytest.mark.parametrize(("secret", "message"), [("", "empty"), ("a", "not base64url")])
def test_rejects_unusable_secret(secret: str, message: str) -> None:
    with pytest.raises(WebhookVerificationError, match=message):
        verify_webhook(payload=VALID["body"], headers=headers_for(VALID), secret=secret, now=VALID["now"])
