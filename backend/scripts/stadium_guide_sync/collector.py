from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import httpx

from .schemas import CollectedSource, CollectorType, SourceDefinition


class CollectionError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class SourceCollector(Protocol):
    async def collect(self, source: SourceDefinition) -> CollectedSource: ...


class HttpSourceCollector:
    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self._timeout = timeout_seconds

    async def collect(self, source: SourceDefinition) -> CollectedSource:
        headers = {
            "User-Agent": "BaseballAgentV2-StadiumGuideSync/1.0 (+manual pipeline)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
        }
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self._timeout,
                headers=headers,
            ) as client:
                response = await client.get(source.url)
        except httpx.HTTPError as exc:
            raise CollectionError("HTTP_REQUEST_FAILED", str(exc)) from exc
        if response.status_code != 200:
            raise CollectionError(
                "HTTP_STATUS_NOT_OK",
                f"expected 200, got {response.status_code}",
                response.status_code,
            )
        body = response.text
        if len(body.strip()) < 200:
            raise CollectionError("RAW_BODY_TOO_SHORT", "response body is too short", 200)
        return CollectedSource(
            source=source,
            collected_at=datetime.now(UTC),
            body=body,
            status_code=response.status_code,
            collector_type=CollectorType.HTTP,
        )


class PlaywrightBrowserCollector:
    """Optional adapter for explicitly registered JavaScript-only sources."""

    async def collect(self, source: SourceDefinition) -> CollectedSource:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise CollectionError(
                "BROWSER_ADAPTER_UNAVAILABLE",
                "install Playwright only when a registered source requires it",
            ) from exc
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page(locale="ko-KR")
                response = await page.goto(source.url, wait_until="networkidle")
                body = await page.content()
                status_code = response.status if response else 200
            finally:
                await browser.close()
        if len(body.strip()) < 200:
            raise CollectionError("RAW_BODY_TOO_SHORT", "rendered body is too short")
        return CollectedSource(
            source=source,
            collected_at=datetime.now(UTC),
            body=body,
            status_code=status_code,
            collector_type=CollectorType.BROWSER,
        )


def collector_for(source: SourceDefinition) -> SourceCollector:
    if source.collector_type == CollectorType.BROWSER:
        return PlaywrightBrowserCollector()
    return HttpSourceCollector()

