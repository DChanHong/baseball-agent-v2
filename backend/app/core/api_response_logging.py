from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.api.access")

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "apikey",
}


class ApiResponseLoggingMiddleware:
    """Log HTTP request/response metadata and persist captured responses as JSON."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool,
        log_dir: str,
        max_body_bytes: int,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.log_dir = Path(log_dir)
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        request_body = bytearray()
        request_body_truncated = False
        response_body = bytearray()
        response_body_truncated = False
        status_code: int | None = None
        response_headers: dict[str, str] = {}

        async def receive_wrapper() -> Message:
            nonlocal request_body_truncated

            message = await receive()
            if message["type"] == "http.request":
                request_body_truncated = _capture_body_chunk(
                    request_body,
                    message.get("body", b""),
                    self.max_body_bytes,
                    request_body_truncated,
                )
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_body_truncated, response_headers, status_code

            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = _headers_to_dict(message.get("headers", []))
            elif message["type"] == "http.response.body":
                response_body_truncated = _capture_body_chunk(
                    response_body,
                    message.get("body", b""),
                    self.max_body_bytes,
                    response_body_truncated,
                )

            await send(message)

            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                self._persist_record(
                    scope=scope,
                    request_id=request_id,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    status_code=status_code,
                    request_body=bytes(request_body),
                    request_body_truncated=request_body_truncated,
                    response_body=bytes(response_body),
                    response_body_truncated=response_body_truncated,
                    response_headers=response_headers,
                    error=None,
                )

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            self._persist_record(
                scope=scope,
                request_id=request_id,
                started_at=started_at,
                duration_ms=duration_ms,
                status_code=status_code,
                request_body=bytes(request_body),
                request_body_truncated=request_body_truncated,
                response_body=bytes(response_body),
                response_body_truncated=response_body_truncated,
                response_headers=response_headers,
                error=repr(exc),
            )
            raise

    def _persist_record(
        self,
        *,
        scope: Scope,
        request_id: str,
        started_at: datetime,
        duration_ms: float,
        status_code: int | None,
        request_body: bytes,
        request_body_truncated: bool,
        response_body: bytes,
        response_body_truncated: bool,
        response_headers: dict[str, str],
        error: str | None,
    ) -> None:
        path = str(scope.get("path", ""))
        method = str(scope.get("method", ""))
        query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
        request_headers = _headers_to_dict(scope.get("headers", []))
        content_type = response_headers.get("content-type", "")

        record = {
            "request_id": request_id,
            "timestamp": started_at.isoformat(),
            "duration_ms": duration_ms,
            "request": {
                "method": method,
                "path": path,
                "query_string": query_string,
                "client": _client_to_dict(scope.get("client")),
                "headers": _redact_headers(request_headers),
                "body": _decode_body(request_body, request_headers.get("content-type", "")),
                "body_truncated": request_body_truncated,
            },
            "response": {
                "status_code": status_code,
                "headers": _redact_headers(response_headers),
                "body": _decode_body(response_body, content_type),
                "body_truncated": response_body_truncated,
            },
            "error": error,
        }

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.log_dir / _build_log_file_name(started_at, method, path, request_id)
            file_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to persist API response log")

        logger.info(
            "%s %s -> %s %.2fms request_id=%s",
            method,
            path,
            status_code,
            duration_ms,
            request_id,
        )


def _capture_body_chunk(
    buffer: bytearray,
    chunk: bytes,
    max_body_bytes: int,
    already_truncated: bool,
) -> bool:
    if not chunk or already_truncated:
        return already_truncated

    remaining = max_body_bytes - len(buffer)
    if remaining <= 0:
        return True

    buffer.extend(chunk[:remaining])
    return len(chunk) > remaining


def _headers_to_dict(headers: Any) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in headers
    }


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: "[REDACTED]" if key.lower() in SENSITIVE_HEADERS else value
        for key, value in headers.items()
    }


def _decode_body(body: bytes, content_type: str) -> Any:
    if not body:
        return None

    text = body.decode("utf-8", errors="replace")
    if "application/json" not in content_type.lower():
        return text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _client_to_dict(client: Any) -> dict[str, Any] | None:
    if client is None:
        return None
    host, port = client
    return {"host": host, "port": port}


def _build_log_file_name(
    timestamp: datetime,
    method: str,
    path: str,
    request_id: str,
) -> str:
    safe_path = path.strip("/").replace("/", "_") or "root"
    safe_path = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_"
        for character in safe_path
    )
    safe_timestamp = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    return f"{safe_timestamp}_{method.lower()}_{safe_path}_{request_id[:8]}.json"
