"""把某次实验里得分最差的若干条完整导出来，供人肉过一遍。

为什么值得单独做这一步：基线跑完的分布是双峰的——168 条里 108 条落在
0.0-0.2，另有 15 条落在 0.8-1.0。那 15 条（9% 的样本）贡献了均值 0.181
里的 0.080，占总误差的 44%。

一小撮集中的失败通常有共同成因，看三条就能猜到病根，比任何全局调参
都有效。均值只告诉你"有 18% 的问题"，看不出这 18% 是摊在所有样本上
还是挤在一小撮里——而这两种情况该采取的行动完全不同。

输出到 data/worst_cases.md，用 markdown 是为了长文本读起来不难受。
"""

import argparse
from pathlib import Path

import opik
from loguru import logger

# 必须导入：Opik 的 API key 是 config.py 的导入副作用（见 analyze_experiment.py）
from three_kingdoms.config import settings  # noqa: F401

OUT_PATH = Path("data/worst_cases.md")


def _scores(item) -> dict[str, float]:
    return {s["name"]: s["value"] for s in item.feedback_scores}


def _reasons(item) -> dict[str, str]:
    return {s["name"]: (s.get("reason") or "") for s in item.feedback_scores}


def main(experiment_name: str | None, top: int, threshold: float) -> None:
    client = opik.Opik()

    if experiment_name:
        experiments = client.get_experiments_by_name(name=experiment_name)
        if not experiments:
            raise SystemExit(f"找不到实验 {experiment_name}")
        experiment = experiments[-1]
    else:
        page = client.rest_client.experiments.find_experiments(
            name="three-kingdoms",
            size=20,
            sorting='[{"field":"created_at","direction":"DESC"}]',
        )
        rows = page.content or []
        if not rows:
            raise SystemExit("没找到 three-kingdoms 开头的实验，请用 --name 指定")
        experiment = client.get_experiment_by_id(rows[0].id)

    items = experiment.get_items()
    logger.info(f"实验 {experiment.name}：{len(items)} 条")

    ranked = sorted(
        items,
        key=lambda it: _scores(it).get("hallucination_vs_gold", 0.0),
        reverse=True,
    )
    worst = [
        it
        for it in ranked
        if _scores(it).get("hallucination_vs_gold", 0.0) >= threshold
    ][:top]

    lines = [
        f"# 最差的 {len(worst)} 条（hallucination_vs_gold >= {threshold}）",
        "",
        f"实验：`{experiment.name}`",
        "",
        "看的时候按这几类归因：",
        "",
        "1. **判官误判** —— 答案其实对，只是依据了同一事件的另一回，"
        "gold chunk 看不到，判官就说你在编。演义反复叙事，这类会有一批。",
        "2. **检索捞错** —— retrieved 跟 gold 讲的根本不是一回事。",
        "3. **生成层加戏** —— retrieved 是对的，但答案添了原文没有的细节。",
        "4. **题目本身是坏的** —— 出题时就错了，该从评测集里剔掉。",
        "",
        "第 1 类多 = 指标偏严，要调评法；第 3 类多 = 改角色卡或换模型；"
        "第 4 类多 = 回去修出题 prompt。",
        "",
        "---",
        "",
    ]

    for rank, item in enumerate(worst, start=1):
        s, r = _scores(item), _reasons(item)
        data = item.dataset_item_data or {}
        out = item.evaluation_task_output or {}
        retrieved = out.get("retrieved_context") or []

        lines += [
            f"## {rank}. [{data.get('character_id', '?')}] "
            f"gold={s.get('hallucination_vs_gold', float('nan')):.2f} "
            f"faith={s.get('faithfulness_vs_retrieved', float('nan')):.2f} "
            f"tool={s.get('tool_called', 0.0):.0f}",
            "",
            f"**问**：{data.get('input', '')}",
            "",
            f"**参考答案**：{data.get('expected_output', '')}",
            "",
            f"**agent 答**：{out.get('output', '')}",
            "",
            f"**判官理由**：{r.get('hallucination_vs_gold', '')}",
            "",
            "<details><summary>gold chunk</summary>",
            "",
            "".join(data.get("context") or []),
            "",
            "</details>",
            "",
            f"<details><summary>实际检索到的 {len(retrieved)} 段</summary>",
            "",
            "\n\n----\n\n".join(retrieved) if retrieved else "（未调用检索）",
            "",
            "</details>",
            "",
            "**归因**： ",  # 留空给你手填
            "",
            "---",
            "",
        ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"已写入 {OUT_PATH}（{len(worst)} 条）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.6)
    a = parser.parse_args()
    main(a.name, a.top, a.threshold)
