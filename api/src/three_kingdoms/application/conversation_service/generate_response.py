import time
import uuid
from typing import Any, AsyncGenerator, Union

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from loguru import logger

from three_kingdoms.application.conversation_service.workflow.graph import (
    create_workflow_graph,
)
from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)
from three_kingdoms.domain.character import Character
from three_kingdoms.infrastructure.mongo.checkpointer import (
    get_checkpointer,
)


async def get_response(
    messages: str | list[str] | list[dict[str, Any]],
    character: Character,
    new_thread: bool = False,
) -> tuple[str, CharacterState]:
    graph_builder = create_workflow_graph()

    try:
        graph = graph_builder.compile(checkpointer=get_checkpointer())

        thread_id = character.id if not new_thread else f"{character.id}-{uuid.uuid4()}"
        config = {
            "configurable": {"thread_id": thread_id},
        }
        output_state = await graph.ainvoke(
            input={
                "messages": __format_messages(messages=messages),
                "character_id": character.id,
                "character_name": character.name,
                "character_perspective": character.perspective,
                "character_style": character.style,
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
        graph = graph_builder.compile(checkpointer=get_checkpointer())

        thread_id = character.id if not new_thread else f"{character.id}-{uuid.uuid4()}"
        config = {
            "configurable": {"thread_id": thread_id},
        }

        started = time.perf_counter()
        first_content_sent = False
        empty_chunks = 0

        async for chunk in graph.astream(
            input={
                "messages": __format_messages(messages=messages),
                "character_id": character.id,
                "character_name": character.name,
                "character_perspective": character.perspective,
                "character_style": character.style,
            },
            config=config,
            stream_mode="messages",
        ):
            if chunk[1]["langgraph_node"] == "conversation_node" and isinstance(
                chunk[0], AIMessageChunk
            ):
                if not chunk[0].content:
                    # 生成 tool_call 或 reasoning 时 content 为空，不往前端发
                    empty_chunks += 1
                    continue

                if not first_content_sent:
                    first_content_sent = True
                    logger.info(
                        f"[耗时] 首字延迟: {time.perf_counter() - started:.2f}s "
                        f"（其间跳过 {empty_chunks} 个空 chunk）"
                    )

                yield chunk[0].content

        logger.info(f"[耗时] 整轮总计: {time.perf_counter() - started:.2f}s")

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
