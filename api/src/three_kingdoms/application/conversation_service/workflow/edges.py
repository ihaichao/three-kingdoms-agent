from typing import Literal

from langgraph.graph import END

from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)
from three_kingdoms.config import settings


def should_summarize_conversation(
    state: CharacterState,
) -> Literal["summarize_conversation_node", "__end__"]:
    if len(state["messages"]) > settings.TOTAL_MESSAGES_SUMMARY_TRIGGER:
        return "summarize_conversation_node"
    return END
