from __future__ import annotations

import base64
import hashlib


def _keystream(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_secret(value: str, secret: str) -> str:
    raw = value.encode("utf-8")
    key = _keystream(secret)
    payload = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decrypt_secret(value: str, secret: str) -> str:
    payload = base64.urlsafe_b64decode(value.encode("utf-8"))
    key = _keystream(secret)
    raw = bytes(payload[i] ^ key[i % len(key)] for i in range(len(payload)))
    return raw.decode("utf-8")
