from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.agent.routing_schemas import ToolRoutingDecision, ToolRoutingRequest
from app.agent.tool_cards import TOOL_ROUTING_TOOL_CARDS

PROMPT_ASSET_DIR = Path(__file__).with_name("prompt_assets")
TOOL_ROUTING_POLICY_PROMPT_PATH = PROMPT_ASSET_DIR / "tool_routing_policy.md"
TOOL_ROUTING_FEW_SHOTS_PATH = PROMPT_ASSET_DIR / "tool_routing_few_shots.jsonl"


class ToolRoutingFewShotExample(BaseModel):
    """One validated few-shot example for tool routing prompt assembly."""

    model_config = ConfigDict(extra="forbid")

    request: ToolRoutingRequest
    decision: ToolRoutingDecision


@lru_cache
def load_tool_routing_policy_prompt() -> str:
    return TOOL_ROUTING_POLICY_PROMPT_PATH.read_text(encoding="utf-8").strip()


@lru_cache
def load_tool_routing_few_shot_examples() -> tuple[ToolRoutingFewShotExample, ...]:
    examples: list[ToolRoutingFewShotExample] = []
    for line_no, line in enumerate(
        TOOL_ROUTING_FEW_SHOTS_PATH.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in {TOOL_ROUTING_FEW_SHOTS_PATH.name}:{line_no}"
            ) from exc
        examples.append(ToolRoutingFewShotExample.model_validate(payload))

    if not examples:
        raise ValueError(f"{TOOL_ROUTING_FEW_SHOTS_PATH.name} must not be empty")
    return tuple(examples)


def build_tool_routing_few_shot_prompt() -> str:
    lines = ["예시:"]
    for example in load_tool_routing_few_shot_examples():
        lines.extend(
            [
                "",
                "입력:",
                _compact_json(example.request),
                "출력:",
                _compact_json(example.decision),
            ]
        )
    return "\n".join(lines)


def build_tool_routing_system_prompt() -> str:
    """Build the system prompt with only the currently enabled tool cards."""

    tool_cards = "\n\n".join(TOOL_ROUTING_TOOL_CARDS)
    return "\n\n".join(
        [
            load_tool_routing_policy_prompt(),
            "사용 가능한 도구:\n\n" + tool_cards,
            build_tool_routing_few_shot_prompt(),
        ]
    )


def _compact_json(model: BaseModel) -> str:
    payload: Any = model.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
