"""HTTP auth gate for the localfabric API.

Posture:
- The default uvicorn bind is 127.0.0.1, so loopback-only is the v1
  stance — anyone on the same machine can call it without a token.
- For non-loopback access set the `LOCALFABRIC_API_TOKEN` env var; the
  `require_token` FastAPI dependency then enforces an `Authorization:
  Bearer <token>` header.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request, status


def require_token(request: Request) -> None:
    """FastAPI dependency. Allows loopback unconditionally; requires
    Bearer token from non-loopback clients."""
    token = os.environ.get("LOCALFABRIC_API_TOKEN", "").strip()
    client = request.client.host if request.client else ""
    if client in ("127.0.0.1", "::1", "localhost", ""):
        return
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non-loopback access requires LOCALFABRIC_API_TOKEN to be set on the server.",
        )
    auth = request.headers.get("authorization", "")
    expected = f"Bearer {token}"
    if auth != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header.",
        )
