from __future__ import annotations

import uuid

import httpx
from fastapi import Request
from starlette.responses import Response, StreamingResponse

from app.settings import get_settings

_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=60.0), follow_redirects=True)
    return _client


def wants_ui(method: str, path: str, accept: str, ui_origin: str) -> bool:
    if not (ui_origin or "").strip():
        return False
    if path.startswith("/internal") or path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
        return False
    verb = method.upper()
    if verb != "GET" and verb != "HEAD":
        return False
    if path.startswith("/videos"):
        parts = [part for part in path.split("/") if part]
        if len(parts) != 2:
            return False
        try:
            uuid.UUID(parts[1])
        except ValueError:
            return False
        return "text/html" in (accept or "").lower()
    return True


async def proxy_ui(request: Request) -> Response:
    base = str(get_settings().ui_origin).rstrip("/")
    url = f"{base}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = [(key, value) for key, value in request.headers.items() if key.lower() not in _HOP]
    try:
        upstream = await _http().send(
            _http().build_request(request.method, url, headers=headers, content=await request.body()),
            stream=True,
        )
    except httpx.RequestError:
        return Response("UI is not running.", status_code=502)

    out_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in _HOP
    }
    if "text/html" in (upstream.headers.get("content-type") or ""):
        out_headers["cache-control"] = "no-store"

    async def body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()

    return StreamingResponse(
        body(),
        status_code=upstream.status_code,
        headers=out_headers,
    )
