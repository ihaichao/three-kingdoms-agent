"""对照两个判官模型，决定评估用哪个。

为什么要单独跑这个：判官换了，历史实验就不可比——4o-mini 判 0.36、
nano 判 0.48，这个差是判官变了不是系统变了，但报表上看不出来。
所以判官要在跑基线之前定死，之后整个对比周期不许动。

隔离变量的关键：**agent 只跑一次**，同一批 (问题, 答案, 检索内容) 交给
两个判官各打一遍。重跑 agent 的话答案本身就变了，分差里混着 agent 的
随机性，比不出判官的差别。

这是一次性诊断，不走 opik.evaluate，免得往实验列表里灌垃圾数据。
"""

import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from opik.evaluation.metrics import AnswerRelevance, Hallucination

from three_kingdoms.application.evaluation.evaluate import agent_task
from three_kingdoms.application.evaluation.metrics import FaithfulnessToRetrieved
from three_kingdoms.config import settings
from three_kingdoms.domain.evaluation import EvaluationDataset

JUDGES = {
    "4o-mini": "openrouter/openai/gpt-4o-mini",
    "nano": "openrouter/openai/gpt-5-nano",
}


def _score_all(model: str, rows: list[dict]) -> dict[str, list[float]]:
    halluc = Hallucination(model=model, track=False)
    faith = FaithfulnessToRetrieved(model=model)
    relev = AnswerRelevance(model=model, track=False)

    out: dict[str, list[float]] = {"gold": [], "faith": [], "relev": []}
    for row in rows:
        out["gold"].append(
            halluc.score(
                input=row["input"], output=row["output"], context=row["context"]
            ).value
        )
        out["faith"].append(
            faith.score(
                input=row["input"],
                output=row["output"],
                retrieved_context=row["retrieved_context"],
            ).value
        )
        out["relev"].append(
            relev.score(
                input=row["input"], output=row["output"], context=row["context"]
            ).value
        )
    return out


def main(n: int) -> None:
    dataset = EvaluationDataset.from_json(settings.EVALUATION_DATASET_FILE_PATH)
    samples = dataset.samples[:n]

    logger.info(f"跑 agent（{len(samples)} 条，并发 4）—— 只跑这一次")
    items = [
        {
            "input": s.question,
            "context": [s.source_chunk],
            "character_id": s.character_id,
        }
        for s in samples
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(agent_task, items))

    rows = [{**item, **result} for item, result in zip(items, results)]
    no_tool = sum(1 for r in rows if not r["retrieved_context"])
    logger.info(f"agent 跑完，其中 {no_tool} 条未调检索")

    scores = {}
    for label, model in JUDGES.items():
        logger.info(f"判官 {label} ({model}) 开始打分")
        scores[label] = _score_all(model, rows)

    a, b = list(JUDGES)
    print(f"\n{'#':>3} {'问题':<24} {a + ' gold':>12} {b + ' gold':>12} {'差':>6}")
    for i, row in enumerate(rows):
        ga, gb = scores[a]["gold"][i], scores[b]["gold"][i]
        q = row["input"][:22]
        print(f"{i:>3} {q:<24} {ga:>12.2f} {gb:>12.2f} {abs(ga - gb):>6.2f}")

    print()
    for key, title in [
        ("gold", "hallucination_vs_gold"),
        ("faith", "faithfulness_vs_retrieved"),
        ("relev", "answer_relevance"),
    ]:
        xa, xb = scores[a][key], scores[b][key]
        mae = statistics.fmean(abs(p - q) for p, q in zip(xa, xb))
        print(
            f"{title:<28} {a} 均值 {statistics.fmean(xa):.3f} | "
            f"{b} 均值 {statistics.fmean(xb):.3f} | 平均绝对差 {mae:.3f}"
        )

    print(
        "\n怎么看：平均绝对差小（<0.15）说明两个判官看法接近，可以放心用便宜的；"
        "\n差得大就说明便宜的那个判不动这个任务，省下的钱会以错误结论的形式还回来。"
        "\n另外留意 nano 会不会把分数压成清一色的 0 或 1——那是判不动、在瞎猜的典型表现。"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=10, help="用多少条题做对照")
    main(parser.parse_args().n)
