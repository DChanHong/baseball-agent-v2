import logging

from openai import AsyncOpenAI

from app.agent.prompts import build_tool_routing_system_prompt
from app.agent.routing_schemas import (
    ToolRoutingDecision,
    ToolRoutingRequest,
    ToolRoutingUserContext,
)
from app.core.config import get_settings
from app.core.llm import get_openai_client

logger = logging.getLogger(__name__)


class ToolRoutingService:
    """Decides whether a user message should call a backend tool."""

    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client or get_openai_client()
        self._model = model or settings.openai_model

    async def execute(
        self,
        message: str,
        user_context: ToolRoutingUserContext,
    ) -> ToolRoutingDecision:
        """Route a user message to either a tool, clarification, or direct answer."""

        request = ToolRoutingRequest(
            message=message,
            user_context=user_context,
        )

        logger.info(
            "tool routing started model=%s favorite_team_id=%s today=%s timezone=%s",
            self._model,
            user_context.favorite_team_id,
            user_context.today,
            user_context.timezone,
        )

        try:
            response = await self._client.responses.parse(
                model=self._model,
                instructions=build_tool_routing_system_prompt(),
                input=request.model_dump_json(),
                text_format=ToolRoutingDecision,
            )
        except Exception:
            logger.exception("tool routing failed model=%s", self._model)
            raise

        decision = response.output_parsed

        logger.info(
            (
                "tool routing completed model=%s is_in_scope=%s "
                "should_call_tool=%s tool_name=%s needs_clarification=%s "
                "unsupported_reason=%s"
            ),
            self._model,
            decision.is_in_scope,
            decision.should_call_tool,
            decision.tool_name,
            decision.needs_clarification,
            decision.unsupported_reason,
        )

        return decision
