from __future__ import annotations

from typing import Any

from app.agent.routing_schemas import ToolRoutingDecision
from app.agent.state import AgentConversationContext, SelectedGameContext
from app.domains.chat.controller.schemas import ToolName


def build_assistant_content(
    *,
    message: str,
    decision: ToolRoutingDecision,
    tool_payload: dict[str, Any] | None,
) -> str:
    if decision.needs_clarification:
        return _clarification_text(decision.clarification_reason)

    if decision.unsupported_reason is not None:
        return _unsupported_text(decision.unsupported_reason)

    if not decision.should_call_tool:
        return "질문은 확인했어요. 현재 MVP에서는 사용할 수 있는 도구 범위 안에서 답변을 준비하고 있습니다."

    if tool_payload is None:
        return "도구 호출이 필요했지만 결과를 만들지 못했습니다. 잠시 뒤 다시 시도해 주세요."

    if tool_payload.get("status") == "failed":
        return "도구 실행 중 문제가 생겨서 정확한 결과를 가져오지 못했습니다. 잠시 뒤 다시 시도해 주세요."

    tool_name = tool_payload.get("name")
    result = tool_payload.get("result")
    if not isinstance(tool_name, str) or not isinstance(result, dict):
        return "도구 결과를 확인했습니다."

    return _tool_summary(tool_name=tool_name, result=result, fallback_message=message)


def build_selected_game_place_answer(selected_game: SelectedGameContext) -> str:
    matchup = f"{selected_game.away_team_name} vs {selected_game.home_team_name}"
    return f"직전 조회한 {matchup} 경기는 {selected_game.stadium_name}에서 열립니다."


def promote_context_from_tool_payload(
    *,
    context: AgentConversationContext,
    tool_payload: dict[str, Any] | None,
) -> AgentConversationContext:
    if tool_payload is None or tool_payload.get("status") != "completed":
        return context

    tool_name = tool_payload.get("name")
    result = tool_payload.get("result")
    if tool_name != "find_kbo_game" or not isinstance(result, dict):
        return context.model_copy(update={"last_tool_name": tool_name})

    games = result.get("games")
    if not isinstance(games, list) or len(games) != 1:
        return context.model_copy(update={"last_tool_name": tool_name})

    game = games[0]
    if not isinstance(game, dict):
        return context.model_copy(update={"last_tool_name": tool_name})

    selected_game = SelectedGameContext.model_validate(
        {
            "game_id": game["id"],
            "game_date": game["game_date"],
            "start_time": game.get("start_time"),
            "away_team_id": game["away_team_id"],
            "home_team_id": game["home_team_id"],
            "away_team_name": game["away_team_name"],
            "home_team_name": game["home_team_name"],
            "stadium_id": game["stadium_id"],
            "stadium_name": game["stadium_name"],
            "game_status": game["game_status"],
        }
    )

    return context.model_copy(
        update={
            "selected_game": selected_game,
            "selected_stadium_id": selected_game.stadium_id,
            "selected_stadium_name": selected_game.stadium_name,
            "last_tool_name": tool_name,
        }
    )


def can_answer_selected_game_place(
    *,
    message: str,
    context: AgentConversationContext,
) -> bool:
    if context.selected_game is None:
        return False

    normalized = "".join(message.strip().split())
    place_markers = ("어디서", "어디", "장소", "구장", "경기장")
    game_markers = ("경기", "야구", "거기")
    return any(marker in normalized for marker in place_markers) and any(
        marker in normalized for marker in game_markers
    )


def _clarification_text(reason: str | None) -> str:
    if reason == "team_required_for_schedule_lookup":
        return "어느 팀 경기를 볼지 알려주시면 일정과 경기 여부를 확인해드릴게요."
    if reason == "stadium_required_for_stadium_guide_search":
        return "어느 구장 기준인지 알려주시면 반입, 교통, 시설 정보를 찾아드릴게요."
    if reason == "stadium_required_for_weather_lookup":
        return "어느 구장 날씨를 볼지 알려주시면 직관 컨디션을 확인해드릴게요."
    return "조금만 더 구체적으로 알려주시면 확인해드릴게요."


def _unsupported_text(reason: str) -> str:
    messages = {
        "out_of_scope": "지금은 KBO 직관과 야구 관련 질문만 도와드릴 수 있어요.",
        "weather_or_realtime_cancellation_prediction_required": (
            "공식 우천 취소 여부는 구단/KBO의 확정 공지가 필요해요. "
            "대신 구장 기준 날씨와 직관 준비 수준은 확인할 수 있습니다."
        ),
        "weather_forecast_range_not_supported": "현재 날씨 도구는 오늘부터 글피까지만 지원합니다.",
        "ticket_inventory_tool_required": "실시간 잔여석은 아직 조회할 수 없어요. 예매처와 예매 방법 안내는 가능합니다.",
        "opponent_team_filter_not_supported_yet": "두 팀 맞대결 일정 필터는 아직 지원하지 않습니다.",
    }
    return messages.get(reason, "현재 MVP에서 아직 지원하지 않는 요청입니다.")


def _tool_summary(
    *,
    tool_name: ToolName | str,
    result: dict[str, Any],
    fallback_message: str,
) -> str:
    if tool_name == "find_kbo_game":
        total = result.get("total")
        if total == 0:
            return "조회 조건에 맞는 KBO 경기를 찾지 못했어요."
        return f"경기 일정을 조회했습니다. 조건에 맞는 경기는 총 {total}건입니다."

    if tool_name == "get_stadium_info":
        stadium = result.get("stadium")
        if not isinstance(stadium, dict):
            return "구장 정보를 찾지 못했어요."
        name = stadium.get("name_ko") or stadium.get("short_name") or "해당 구장"
        address = stadium.get("address")
        dome_text = "돔구장입니다" if stadium.get("is_dome") else "돔구장은 아닙니다"
        if address:
            return f"{name} 정보를 확인했습니다. 주소는 {address}이고, {dome_text}."
        return f"{name} 정보를 확인했습니다. {dome_text}."

    if tool_name == "get_weather_context":
        stadium_name = result.get("stadium_name") or result.get("stadium_id") or "해당 구장"
        visit_condition = result.get("visit_condition")
        level = None
        if isinstance(visit_condition, dict):
            level = visit_condition.get("level")
        return f"{stadium_name} 기준 날씨 정보를 확인했습니다. 직관 컨디션은 {level or '확인 필요'} 수준입니다."

    if tool_name in {"search_stadium_guide", "search_ticketing_guide"}:
        answerable = result.get("answerable")
        items = result.get("items")
        count = len(items) if isinstance(items, list) else 0
        if not answerable:
            return "관련 안내 문서를 찾지 못했어요. 공식 구단 안내를 함께 확인해 주세요."
        return f"관련 안내 문서 {count}건을 찾았습니다. 카드에서 출처와 주요 내용을 확인할 수 있어요."

    if tool_name == "search_baseball_knowledge":
        answerable = result.get("answerable")
        items = result.get("items")
        count = len(items) if isinstance(items, list) else 0
        if not answerable:
            return "관련 야구 지식 문서를 찾지 못했어요."
        return f"질문 '{fallback_message}'에 참고할 야구 지식 근거 {count}건을 찾았습니다."

    return "도구 결과를 확인했습니다."
