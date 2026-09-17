import uuid
from typing import Any, AsyncGenerator, Union

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from three_kingdoms.application.conversation_service.workflow.graph import (
    create_workflow_graph,
)
from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)
from three_kingdoms.domain.character import Character


async def get_response(
    messages: str | list[str] | list[dict[str, Any]],
    character: Character,
    new_thread: bool = False,
) -> tuple[str, CharacterState]:
    graph_builder = create_workflow_graph()

    try:
        graph = graph_builder.compile()

        thread_id = character.id if not new_thread else f"{character.id}-{uuid.uuid4()}"
        config = {
            "configurable": {"thread_id": thread_id},
        }
        output_state = await graph.ainvoke(
            input={
                "messages": __format_messages(messages=messages),
                "character_name": character.name,
                "character_perspective": character.perspective,
                "character_style": character.style,
                "summary": "",
            },
            config=config,
        )
        last_message = output_state["messages"][-1]
        return last_message.content, CharacterState(**output_state)
    except Exception as e:
        raise RuntimeError(f"Error running conversation workflow: {str(e)}") from e


async def get_streaming_response(
    messages: str | list[str] | list[dict[str, Any]],
    character: Character,
    new_thread: bool = False,
) -> AsyncGenerator[str, None]:
    graph_builder = create_workflow_graph()

    try:
        graph = graph_builder.compile()

        thread_id = character.id if not new_thread else f"{character.id}-{uuid.uuid4()}"
        config = {
            "configurable": {"thread_id": thread_id},
        }

        async for chunk in graph.astream(
            input={
                "messages": __format_messages(messages=messages),
                "character_name": character.name,
                "character_perspective": character.perspective,
                "character_style": character.style,
                "summary": "",
            },
            config=config,
            stream_mode="messages",
        ):
            if chunk[1]["langgraph_node"] == "conversation_node" and isinstance(
                chunk[0], AIMessageChunk
            ):
                yield chunk[0].content

    except Exception as e:
        raise RuntimeError(
            f"Error running streaming conversation workflow: {str(e)}"
        ) from e


def __format_messages(
    messages: Union[str, list[dict[str, Any]]],
) -> list[Union[HumanMessage, AIMessage]]:
    if isinstance(messages, str):
        return [HumanMessage(content=messages)]

    if isinstance(messages, list):
        if not messages:
            return []

        if (
            isinstance(messages[0], dict)
            and "role" in messages[0]
            and "content" in messages[0]
        ):
            result = []
            for msg in messages:
                if msg["role"] == "user":
                    result.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    result.append(AIMessage(content=msg["content"]))
            return result

        return [HumanMessage(content=message) for message in messages]

    return []
