"""正对照：量一下 hallucination 指标的本底噪声。

背景：v1 和 v2 两套差异很大的测量设置下，hallucination_vs_gold 都稳在
0.18 左右（0.1898 / 0.1832）。这可能不是巧合，而是说明 0.18 里有相当
一部分是**指标自身的噪声**，不是 agent 的误差。

做法：把评测集里的 `expected_answer` 当成 agent 的 output 喂给判官，
context 照旧用 context_window。参考答案是出题时从这段原文里提炼的，
按定义零幻觉——它得多少分，就是这把尺子的零点在哪。

读法：
    本底 ≈ 0.02  ->  0.183 是真误差，还有很大改进空间，继续修检索和生成层
    本底 ≈ 0.15  ->  agent 基本贴着天花板，这个指标没有分辨率再衡量改进，
                     后面的优化做了也测不出来，该换评法而不是继续调系统

顺带跑一个负对照：把答案换成一句跟问题无关的废话。它应该拿高分（接近
1.0）。如果负对照也是 0.2，说明判官压根没在判，整个指标作废。

不跑 agent，只调判官。40 条约一分五。
"""

import argparse
import random
import statistics
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from opik.evaluation.metrics import Hallucination

from three_kingdoms.config import settings
from three_kingdoms.domain.evaluation import EvaluationDataset

# 负对照用的废话。跟三国有关但跟任何具体问题都无关，
# 用完全离题的句子太容易了，判官不费力就能识破。
NEGATIVE_ANSWER = "此事说来话长。大丈夫生于乱世，当带三尺剑立不世之功，余者皆不足论。"


def main(n: int) -> None:
    dataset = EvaluationDataset.from_json(settings.EVALUATION_DATASET_FILE_PATH)
    rng = random.Random(42)
    samples = (
        rng.sample(dataset.samples, n) if len(dataset.samples) > n else dataset.samples
    )
    logger.info(f"抽 {len(samples)} 条做对照，判官 {settings.EVALUATION_JUDGE_MODEL}")

    judge = Hallucination(model=settings.EVALUATION_JUDGE_MODEL, track=False)

    def score(args) -> float:
        sample, answer = args
        return judge.score(
            input=sample.question,
            output=answer,
            context=[sample.context_window],
        ).value

    with ThreadPoolExecutor(max_workers=8) as pool:
        positive = list(pool.map(score, [(s, s.expected_answer) for s in samples]))
        negative = list(pool.map(score, [(s, NEGATIVE_ANSWER) for s in samples]))

    def report(label: str, values: list[float]) -> None:
        buckets = [0] * 5
        for v in values:
            buckets[min(int(v * 5), 4)] += 1
        dist = " ".join(
            f"{i * 0.2:.1f}-{(i + 1) * 0.2:.1f}:{c}" for i, c in enumerate(buckets)
        )
        sd = statistics.stdev(values) if len(values) > 1 else 0.0
        print(f"{label:<18} 均值 {statistics.fmean(values):.3f}  标准差 {sd:.3f}")
        print(f"{'':<18} 分布 {dist}")

    print()
    report("正对照(参考答案)", positive)
    report("负对照(答非所问)", negative)
    print(f"\n{'对照组已知基线':<18} agent 实测 0.183（v2 全量 196 条）")
    print(
        "\n读法：\n"
        "  正对照接近 0 且负对照接近 1  -> 尺子是准的，0.183 是真误差，继续优化系统\n"
        "  正对照也有 0.15 左右         -> 0.183 里大半是本底，agent 贴着天花板，\n"
        "                                 再优化也测不出来，该换评法\n"
        "  负对照没有明显高于正对照     -> 判官根本没在判，这个指标作废"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=40)
    main(parser.parse_args().n)
