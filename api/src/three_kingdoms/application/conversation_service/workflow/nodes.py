from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig

from three_kingdoms.application.conversation_service.workflow.chains import (
    get_character_response_chain,
    get_conversation_summary_chain,
)
from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)
from three_kingdoms.config import settings


async def conversation_node(state: CharacterState, config: RunnableConfig):
    summary = state.get("summary", "")
    chain = get_character_response_chain()

    response = await chain.ainvoke(
        {
            "messages": state["messages"],
            "character_name": state["character_name"],
            "character_perspective": state["character_perspective"],
            "character_style": state["character_style"],
            "summary": summary,
        },
        config,
    )

    return {"messages": response}


async def summarize_conversation_node(state: CharacterState):
    summary = state.get("summary", "")
    chain = get_conversation_summary_chain(summary)
    response = await chain.ainvoke(
        {
            "messages": state["messages"],
            "character_name": state["character_name"],
            "summary": summary,
        }
    )

    delete_messages = [
        RemoveMessage(id=m.id)
        for m in state["messages"][: -settings.TOTAL_MESSAGES_AFTER_SUMMARY]
    ]
    return {"summary": response.content, "messages": delete_messages}
