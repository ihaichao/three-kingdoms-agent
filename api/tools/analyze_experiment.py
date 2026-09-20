"""把 Opik 上某次实验的逐条分数拉回来，做分层统计。

为什么需要这个：汇总均值会骗人。Opik 计算均值时会排除 scoring_failed
的条目（见 opik/evaluation/score_statistics.py），所以

    faithfulness_vs_retrieved  只在"调了检索"的子集上算
    hallucination_vs_gold      在全部样本上算

两个数不是同一批样本，直接比是错的。要判断"检索是不是瓶颈"，必须把
gold 也限制到同一子集，再跟 faithfulness 对照。

不重跑 agent——实验结果已经在 Opik 上，读回来就行。
"""

import argparse
import statistics
from collections import defaultdict

import opik
from loguru import logger

# 必须导入 config：Opik 的 API key 是在 config.py 的 model_validator 里
# 作为**导入副作用**写进环境变量的（os.environ.setdefault("OPIK_API_KEY", ...)）。
from three_kingdoms.config import settings  # noqa: F401


def _scores(item) -> dict[str, float]:
    return {s["name"]: s["value"] for s in item.feedback_scores}


def main(experiment_name: str | None) -> None:
    client = opik.Opik()

    if experiment_name:
        experiments = client.get_experiments_by_name(name=experiment_name)
        if not experiments:
            raise SystemExit(f"找不到实验 {experiment_name}")
        experiment = experiments[-1]
    else:
        # 不给名字就自己找最新的。experiment_name_prefix="three-kingdoms"
        # 生成的名字带随机后缀，手抄很烦。
        page = client.rest_client.experiments.find_experiments(
            name="three-kingdoms",
            size=20,
            sorting='[{"field":"created_at","direction":"DESC"}]',
        )
        rows = page.content or []
        if not rows:
            raise SystemExit("没找到 three-kingdoms 开头的实验，请用 --name 指定")
        logger.info("最近的实验：" + ", ".join(r.name for r in rows[:5]))
        experiment = client.get_experiment_by_id(rows[0].id)
    items = experiment.get_items()
    logger.info(f"实验 {experiment.name}：{len(items)} 条")

    called, not_called = [], []
    for item in items:
        s = _scores(item)
        (called if s.get("tool_called", 0.0) >= 0.5 else not_called).append(s)

    def mean(rows, key):
        vals = [r[key] for r in rows if key in r]
        return statistics.fmean(vals) if vals else float("nan")

    print(f"\n{'':<22}{'调了检索':>12}{'没调检索':>12}{'全部':>12}")
    print(f"{'样本数':<22}{len(called):>12}{len(not_called):>12}{len(items):>12}")
    for key in [
        "hallucination_vs_gold",
        "faithfulness_vs_retrieved",
        "answer_relevance_metric",
    ]:
        print(
            f"{key:<22}{mean(called, key):>12.3f}"
            f"{mean(not_called, key):>12.3f}{mean(called + not_called, key):>12.3f}"
        )

    # 同一子集上的对照，这才是能用来判断瓶颈的那组数
    g = mean(called, "hallucination_vs_gold")
    f = mean(called, "faithfulness_vs_retrieved")
    print(f"\n【同子集对照】调了检索的 {len(called)} 条：")
    print(f"  对 gold 一致  {g:.3f}")
    print(f"  对 retrieved  {f:.3f}")
    print(
        f"  差值          {g - f:+.3f}   （正得多 = 忠实地基于错材料回答 = 检索是瓶颈）"
    )

    # 分布：均值相同可能来自完全不同的分布
    buckets = defaultdict(int)
    for s in called:
        v = s.get("hallucination_vs_gold", 0.0)
        buckets[min(int(v * 5), 4)] += 1
    print("\n  gold 分数分布（调了检索的）：")
    for i in range(5):
        lo, hi = i * 0.2, (i + 1) * 0.2
        n = buckets[i]
        print(f"    {lo:.1f}-{hi:.1f}  {'█' * (n * 40 // max(1, len(called)))} {n}")

    # 谁在拖后腿
    by_char = defaultdict(list)
    for item in items:
        cid = (item.dataset_item_data or {}).get("character_id", "?")
        s = _scores(item)
        if "hallucination_vs_gold" in s:
            by_char[cid].append((s["hallucination_vs_gold"], s.get("tool_called", 0.0)))
    print("\n  按角色：")
    for cid, rows in sorted(
        by_char.items(), key=lambda kv: -statistics.fmean(r[0] for r in kv[1])
    ):
        print(
            f"    {cid:<12} n={len(rows):<4} gold={statistics.fmean(r[0] for r in rows):.3f}"
            f"  调检索率={statistics.fmean(r[1] for r in rows):.2f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default=None, help="实验名")
    main(parser.parse_args().name)
