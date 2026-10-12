"""Webhook signature verification.

The payment provider signs each delivery with a shared secret:

    X-Signature: t=<unix timestamp>,v1=<hex HMAC-SHA256 of "<timestamp>.<raw body>">

We recompute the HMAC over the raw bytes (never re-serialised JSON), compare in
constant time and reject old timestamps so a captured request can't be replayed.
"""

from __future__ import annotations

import hashlib
import hmac
import time

TOLERANCE_SECONDS = 300


class SignatureError(Exception):
    pass


def sign(secret: str, body: bytes, timestamp: int) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={mac.hexdigest()}"


def verify(secret: str, body: bytes, header: str | None, now: float | None = None) -> None:
    if not secret:
        raise SignatureError("Webhook secret is not configured")
    if not header:
        raise SignatureError("Missing signature header")
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        timestamp = int(parts["t"])
        received = parts["v1"]
    except (KeyError, ValueError) as e:
        raise SignatureError("Malformed signature header") from e

    now = time.time() if now is None else now
    if abs(now - timestamp) > TOLERANCE_SECONDS:
        raise SignatureError("Signature timestamp outside tolerance")

    expected = sign(secret, body, timestamp).split("v1=", 1)[1]
    if not hmac.compare_digest(expected, received):
        raise SignatureError("Signature does not match")
