import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agent.prompts import build_tool_routing_system_prompt
from app.agent.routing_schemas import (
    ToolRoutingDecision,
    ToolRoutingRequest,
    ToolRoutingUserContext,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ToolRoutingService:
    """Decides whether a user message should call a backend tool."""

    def __init__(
        self,
        chain: Any | None = None,
        model: str | None = None,
    ) -> None:
        if chain is not None and model is not None:
            self._model = model
            self._chain = chain
            return

        settings = get_settings()
        self._model = model or settings.openai_model
        self._chain = chain or _build_routing_chain(
            model=self._model,
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )

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
            response = await self._chain.ainvoke(
                {"request": request.model_dump_json()}
            )
        except Exception:
            logger.exception("tool routing failed model=%s", self._model)
            raise

        decision = (
            response
            if isinstance(response, ToolRoutingDecision)
            else ToolRoutingDecision.model_validate(response)
        )

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


def _build_routing_chain(
    *,
    model: str,
    api_key: str,
    timeout: float,
):
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=build_tool_routing_system_prompt()),
            ("human", "{request}"),
        ]
    )
    chat_model = ChatOpenAI(
        model=model,
        api_key=api_key,
        timeout=timeout,
    )
    return prompt | chat_model.with_structured_output(
        ToolRoutingDecision,
        method="json_schema",
        strict=True,
    )
