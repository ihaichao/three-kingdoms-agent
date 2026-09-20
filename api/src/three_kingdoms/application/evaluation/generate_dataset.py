"""用 LLM 为每个 chunk 生成一条评测问题。

思路：语料里的每一段原文，都是一条"标准答案"。让模型看着这段原文，
反过来写出一个玩家会问的问题——这样问题和答案天然对齐，不用人工标注。

关键约束是**问题必须用现代口语**。语料是文言，玩家说白话，这个语域落差
正是检索真正难的地方。如果让模型照着原文措辞出题，题目会变得太好做，
评出来的分数虚高，反映不了真实使用情况。约束写在
domain/prompts.py 的 EVALUATION_QUESTION_PROMPT 里。
"""

import random

from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from three_kingdoms.application.conversation_service.workflow.chains import (
    get_chat_model,
)
from three_kingdoms.application.data.extract import get_extraction_generator
from three_kingdoms.application.rag.splitters import get_splitter
from three_kingdoms.config import settings
from three_kingdoms.domain.evaluation import (
    EvaluationDataset,
    EvaluationSample,
    GeneratedQuestion,
)
from three_kingdoms.domain.prompts import EVALUATION_QUESTION_PROMPT


def get_question_chain():
    """出题链：原文片段 -> GeneratedQuestion。

    温度给 0.3 而不是对话用的 0.7。这里要的是忠实于原文，不是文采。
    """
    model = get_chat_model(temperature=0.3).with_structured_output(GeneratedQuestion)
    prompt = ChatPromptTemplate.from_messages(
        [("human", EVALUATION_QUESTION_PROMPT.prompt)],
        template_format="jinja2",
    )
    # 实测 169 次调用里有 9 次模型没走 tool call，直接吐了 "question: ..." 纯文本，
    # 解析器拿去 json.loads 就炸。重试两次能捞回大部分——这类失败是随机的，
    # 不是这个 chunk 天生不行。
    return (prompt | model).with_retry(stop_after_attempt=3)


def _context_window(chunks: list, index: int) -> str:
    """取第 index 块，加上它在**同一回、同一角色**里的前后邻居。

    给判官用的 context。只给单块会造成大量误判：agent 提到同一回里前后
    贯通的背景（完全正确的内容），判官在 700 字的窗口里找不到，就判幻觉。
    实测这类占最差 20 条的 30%。

    限定在同一回之内，是因为跨回扩下去会让判官过于宽松——什么都能找到
    依据，指标就失去了区分度。同一角色的 chunk 列表里，相邻元素未必同回
    （诸葛亮在第 37 回出现、第 38 回不出现、第 39 回又出现），所以两个
    条件都要卡。

    邻居数由 settings.EVALUATION_CONTEXT_NEIGHBORS 控制。
    """
    n = settings.EVALUATION_CONTEXT_NEIGHBORS
    if n <= 0:
        return chunks[index].page_content

    here = chunks[index].metadata
    parts = []
    for j in range(index - n, index + n + 1):
        if not 0 <= j < len(chunks):
            continue
        meta = chunks[j].metadata
        if meta["character_id"] != here["character_id"] or meta.get(
            "chapter"
        ) != here.get("chapter"):
            continue
        parts.append(chunks[j].page_content)
    return "\n\n".join(parts)


def generate_dataset() -> EvaluationDataset:
    """遍历全部角色的 chunk，生成评测集。

    切分必须走跟 long_term_memory.py 同一条路径（同一个 extract 生成器、
    同一个 splitter、同一个 RAG_CHUNK_SIZE），否则这里的 source_chunk
    跟向量库里实际存的 chunk 对不上，后面拿它当 context 去评幻觉就是错的。
    """
    splitter = get_splitter(settings.RAG_CHUNK_SIZE)
    chain = get_question_chain()

    # 先把所有 chunk 摊平成一个列表，再一次性批量调用。
    # 分角色串行调用的话，并发度被角色数卡住，白白浪费。
    chunks = []
    for character, docs in get_extraction_generator():
        if not docs:
            continue
        character_chunks = splitter.split_documents(docs)
        chunks.extend(character_chunks)
        logger.info(f"{character.name}: {len(character_chunks)} 块待出题")

    # 演义切出来 1792 篇，每篇都出题既慢又贵，随机抽一批。
    # 固定 seed，保证两次跑出来的评测集可比——换了检索策略要对照分数，
    # 题目集合必须一样，否则分差里混着抽样噪声。
    if len(chunks) > settings.EVALUATION_SAMPLE_SIZE:
        rng = random.Random(42)
        # 抽下标而不是抽元素——后面要靠下标找同一回里的前后邻居。
        picked = sorted(rng.sample(range(len(chunks)), settings.EVALUATION_SAMPLE_SIZE))
        logger.info(f"抽样 {len(picked)} 篇出题（seed=42，可复现）")
    else:
        picked = list(range(len(chunks)))

    windows = [_context_window(chunks, i) for i in picked]
    chunks = [chunks[i] for i in picked]

    inputs = [
        {
            "character_name": chunk.metadata["character_name"],
            "volume": chunk.metadata["volume"],
            "chunk": chunk.page_content,
        }
        for chunk in chunks
    ]

    logger.info(f"共 {len(inputs)} 块，开始出题（并发 8）")
    # batch 内部是线程池，不是协程；异步版本叫 abatch。
    # return_exceptions=True：单条失败不炸掉整批，失败的那条返回异常对象本身。
    results = chain.batch(
        inputs,
        config={"max_concurrency": 8},
        return_exceptions=True,
    )

    samples: list[EvaluationSample] = []
    failed = 0
    skipped = 0

    for chunk, window, result in zip(chunks, windows, results):
        if isinstance(result, Exception):
            failed += 1
            logger.warning(f"出题失败（{chunk.metadata['volume']}）：{result}")
            continue

        # prompt 里允许模型对着废料（纯官职罗列、残片）返回空串，不硬造。
        if not result.question.strip() or not result.expected_answer.strip():
            skipped += 1
            continue

        samples.append(
            EvaluationSample(
                question=result.question.strip(),
                character_id=chunk.metadata["character_id"],
                expected_answer=result.expected_answer.strip(),
                source_chunk=chunk.page_content,
                context_window=window,
                volume=chunk.metadata["volume"],
            )
        )

    logger.info(
        f"生成 {len(samples)} 条 / 共 {len(chunks)} 块"
        f"（模型主动跳过 {skipped}，调用失败 {failed}）"
    )
    return EvaluationDataset(samples=samples)
