from __future__ import annotations

import os
import time
from typing import Any

import httpx
import jwt
from fastapi import Header, HTTPException


AUTH_REQUIRED = os.getenv("HIVE_AUTH_REQUIRED", "false").lower() == "true"
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/"
    "securetoken@system.gserviceaccount.com"
)
_cert_cache: dict[str, Any] = {"expires_at": 0.0, "certs": {}}


def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not AUTH_REQUIRED and not FIREBASE_PROJECT_ID:
        return {"uid": None, "email": None, "authenticated": False}

    if not authorization:
        if AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        return {"uid": None, "email": None, "authenticated": False}

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    claims = verify_firebase_token(token)
    return {
        "uid": claims.get("uid") or claims.get("user_id") or claims.get("sub"),
        "email": claims.get("email"),
        "authenticated": True,
        "claims": claims,
    }


def verify_firebase_token(token: str) -> dict[str, Any]:
    if not FIREBASE_PROJECT_ID:
        raise HTTPException(
            status_code=500,
            detail="FIREBASE_PROJECT_ID is required when backend auth is enabled.",
        )

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid Firebase token") from exc

    key_id = header.get("kid")
    cert = get_firebase_certs().get(key_id)
    if not cert:
        raise HTTPException(status_code=401, detail="Unknown Firebase token key")

    try:
        return jwt.decode(
            token,
            cert,
            algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid Firebase token") from exc


def get_firebase_certs() -> dict[str, str]:
    now = time.time()
    if _cert_cache["certs"] and _cert_cache["expires_at"] > now:
        return _cert_cache["certs"]

    response = httpx.get(CERTS_URL, timeout=10)
    response.raise_for_status()
    max_age = parse_max_age(response.headers.get("cache-control", ""))
    _cert_cache["certs"] = response.json()
    _cert_cache["expires_at"] = now + max_age
    return _cert_cache["certs"]


def parse_max_age(cache_control: str) -> int:
    for part in cache_control.split(","):
        part = part.strip()
        if part.startswith("max-age="):
            try:
                return int(part.split("=", 1)[1])
            except ValueError:
                return 3600
    return 3600
