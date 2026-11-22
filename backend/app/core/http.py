"""Request limits, sanitized diagnostics, and headers for the JSON API."""

import asyncio
import json
import logging
import time
from uuid import uuid4
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("bhashabridge.http")


def api_error(status, code, detail, request_id, headers=None):
    return JSONResponse(
        {"detail": detail, "code": code, "request_id": request_id},
        status_code=status,
        headers=headers,
    )


async def bounded_body(receive, limit):
    body = bytearray()
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return None
        body.extend(message.get("body", b""))
        if len(body) > limit:
            raise OverflowError
        if not message.get("more_body"):
            return bytes(body)


class ApiMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.monotonic()
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        request_headers = Headers(scope=scope)
        status = 0

        async def send_response(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Cache-Control"] = "no-store"
            await send(message)

        async def reject(status_code, code, detail):
            await api_error(status_code, code, detail, request_id)(
                scope, receive, send_response
            )

        try:
            if settings.APP_ENV == "production":
                expected_host = urlsplit(settings.PUBLIC_ORIGIN).netloc
                if request_headers.getlist("host") != [expected_host]:
                    await reject(400, "invalid_host", "Invalid request host")
                    return
            if scope["method"] not in ("GET", "HEAD", "OPTIONS"):
                length = request_headers.get("content-length")
                if length is not None and (
                    not length.isascii() or not length.isdecimal()
                ):
                    await reject(400, "invalid_content_length", "Invalid request size")
                    return
                if length is not None and (
                    len(length) > 10 or int(length) > settings.MAX_REQUEST_BYTES
                ):
                    await reject(
                        413, "body_too_large", "Request body exceeds the size limit"
                    )
                    return
                try:
                    body = await asyncio.wait_for(
                        bounded_body(receive, settings.MAX_REQUEST_BYTES), timeout=10
                    )
                except OverflowError:
                    await reject(
                        413, "body_too_large", "Request body exceeds the size limit"
                    )
                    return
                except TimeoutError:
                    await reject(408, "body_timeout", "Request body timed out")
                    return
                if body is None:
                    return
                delivered = False

                async def replay():
                    nonlocal delivered
                    if delivered:
                        return await receive()
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}

                await self.app(scope, replay, send_response)
            else:
                await self.app(scope, receive, send_response)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "request_failure",
                        "request_id": request_id,
                        "kind": type(exc).__name__,
                    }
                )
            )
            if status == 0:
                await reject(500, "internal_error", "An internal error occurred")
            # Once headers have been sent the only safe response is to stop the stream.
            elif status != 500:
                raise RuntimeError("HTTP response interrupted") from None
        finally:
            from app.services.runtime import http_event

            route = getattr(scope.get("route"), "path", "unmatched")
            elapsed = round((time.monotonic() - started) * 1000, 2)
            http_event(route, status, elapsed)
            logger.info(
                json.dumps(
                    {
                        "event": "request",
                        "request_id": request_id,
                        "route": route,
                        "status": status,
                        "elapsed_ms": elapsed,
                    }
                )
            )
