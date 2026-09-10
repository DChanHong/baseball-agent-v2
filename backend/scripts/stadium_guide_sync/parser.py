from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from .schemas import CollectedSource


class ParseError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "br", "dt", "dd"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "dt", "dd"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


def visible_text(body: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(body)
    text = html.unescape(" ".join(parser.parts))
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_around(text: str, markers: tuple[str, ...], *, radius: int = 700) -> str:
    passages: list[str] = []
    for marker in markers:
        start = 0
        while (index := text.find(marker, start)) >= 0:
            passages.append(text[max(0, index - 100) : index + len(marker) + radius])
            start = index + len(marker)
    unique = list(dict.fromkeys(re.sub(r"\s+", " ", p).strip() for p in passages))
    return "\n".join(unique)


def parse_collected_source(collected: CollectedSource) -> str:
    text = visible_text(collected.body)
    parser_name = collected.source.parser_name
    if parser_name == "heroes_gocheok_faq":
        text = _extract_around(
            text,
            (
                "구장 내 음식물 섭취 가능한가요",
                "음식물 반입",
                "캔 반입 가능한가요",
            ),
            radius=900,
        )
        required = ("음식물", "반입")
    elif parser_name == "heroes_gocheok_ticket":
        text = _extract_around(text, ("SAFE 캠페인", "반입", "주차"), radius=1000)
        required = ("반입",)
    elif parser_name == "seoul_gocheok_faq":
        text = _extract_around(text, ("휠체어", "장애인", "매점", "음식"), radius=900)
        required = ()
    else:
        required = ()
    if len(text.strip()) < 80:
        raise ParseError("PARSED_TEXT_TOO_SHORT", "parsed text is too short")
    if any(marker not in text for marker in required):
        raise ParseError("EXPECTED_MARKER_MISSING", f"missing one of {required}")
    blocked_markers = ("Access Denied", "captcha", "로그인 후 이용")
    if any(marker.lower() in text.lower() for marker in blocked_markers):
        raise ParseError("BLOCK_OR_LOGIN_PAGE", "received a block or login page")
    return text

