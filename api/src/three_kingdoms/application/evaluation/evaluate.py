"""跑端到端评估：让 agent 回答评测集里的问题，再让判官模型打分。"""

import asyncio
from functools import lru_cache
from typing import Any

import opik
from langchain_core.messages import AIMessage, ToolMessage
from loguru import logger
from opik.evaluation import evaluate
from opik.evaluation.metrics import AnswerRelevance, Hallucination

from three_kingdoms.application.conversation_service.workflow.graph import (
    create_workflow_graph,
)
from three_kingdoms.application.evaluation.metrics import (
    FaithfulnessToRetrieved,
    ToolCalled,
)
from three_kingdoms.config import settings
from three_kingdoms.domain.character_factory import CharacterFactory


@lru_cache(maxsize=1)
def _get_graph():
    """编译一次全程复用。

    **故意不挂 checkpointer。**评测集每条题都是独立的单轮问答，不需要
    持久化；挂上反而有两个坏处：196 条题如果共用 thread_id，第 50 条会
    带着前 49 条的历史，还会触发摘要节点；而且离线脚本里没有 FastAPI
    lifespan，get_checkpointer() 会直接抛"未初始化"。
    """
    return create_workflow_graph().compile()


async def _run_agent(item: dict[str, Any]) -> dict[str, Any]:
    character = CharacterFactory.get_character(item["character_id"])

    state = await _get_graph().ainvoke(
        input={
            "messages": [{"role": "user", "content": item["input"]}],
            "character_id": character.id,
            "character_name": character.name,
            "character_perspective": character.perspective,
            "character_style": character.style,
        }
    )

    messages = state["messages"]

    # 检索结果原样躺在 ToolMessage 里，不用改图就能取到。
    retrieved = [m.content for m in messages if isinstance(m, ToolMessage)]

    # 取最后一条有内容的 AIMessage。不能直接用 messages[-1]：带工具调用的
    # 那一轮里，AIMessage 的 content 是空的（内容都在 tool_calls 上）。
    answer = next(
        (
            m.content
            for m in reversed(messages)
            if isinstance(m, AIMessage) and m.content
        ),
        "",
    )

    # 键名不能叫 context——会覆盖 dataset item 里的 gold context。
    return {"output": answer, "retrieved_context": retrieved}


def agent_task(item: dict[str, Any]) -> dict[str, Any]:
    """opik.evaluate 要的是同步可调用，我们的图是异步的，这里包一层。

    evaluate 内部用线程池（task_threads）跑 task，每个线程各自
    asyncio.run 起一个自己的事件循环，互不干扰。
    """
    return asyncio.run(_run_agent(item))


def evaluate_agent(nb_samples: int | None = None) -> None:
    client = opik.Opik()
    dataset = client.get_dataset(name=settings.OPIK_DATASET_NAME)

    judge = settings.EVALUATION_JUDGE_MODEL
    metrics = [
        # context 来自 dataset 的 gold chunk -> 端到端（含检索）
        Hallucination(model=judge, name="hallucination_vs_gold"),
        # context 来自 task 的 retrieved_context -> 只测生成层
        FaithfulnessToRetrieved(model=judge),
        AnswerRelevance(model=judge),
        # 不调 LLM，是上面 faithfulness 的分母
        ToolCalled(),
    ]
    # Moderation 已移除：试跑 5 条全是 0.0000，玩家问的是三国，不会有有害
    # 内容。它占判官调用的 1/4，砍掉省 25% 成本，不损失任何信息。
    # 走一遍 LLMOps 流程的目的，那 5 条已经达到了。

    logger.info(f"开始评估，判官模型 {judge}，样本 {nb_samples or '全部'}")
    result = evaluate(
        dataset=dataset,
        task=agent_task,
        scoring_metrics=metrics,
        experiment_name_prefix="three-kingdoms",
        nb_samples=nb_samples,
        # agent 每轮要跑 2-4 次 LLM 调用，并发太高会被 OpenRouter 限流
        task_threads=4,
        experiment_config={
            "corpus": settings.CORPUS,
            "agent_model": settings.OPENROUTER_LLM_MODEL,
            "judge_model": judge,
            "chunk_size": settings.RAG_CHUNK_SIZE,
            "top_k": settings.RAG_TOP_K,
        },
    )
    logger.info("评估完成，去 Opik 看 experiment")
    return result
