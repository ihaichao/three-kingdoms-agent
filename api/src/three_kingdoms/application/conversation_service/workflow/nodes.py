from langchain_core.runnables import RunnableConfig

from three_kingdoms.application.conversation_service.workflow.chains import (
    get_character_response_chain,
)
from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)


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
