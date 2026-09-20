"""自定义评估指标。

Opik 的打分机制（源码 opik/evaluation/metrics/arguments_helpers.py）：

    mapped_inputs = {**dataset_item, **task_output}

dataset item 的每个键、task 返回的每个键，都摊给每一个指标，然后按各自
score() 的签名挑走需要的。所以只要 task 多返回一个 retrieved_context，
声明了这个参数名的指标就能收到，不用写 scoring_key_mapping。
"""

from typing import Any

from opik.evaluation.metrics import BaseMetric, Hallucination
from opik.evaluation.metrics.score_result import ScoreResult


class FaithfulnessToRetrieved(BaseMetric):
    def __init__(self, model: str, name: str = "faithfulness_vs_retrieved") -> None:
        super().__init__(name=name)
        self._judge = Hallucination(model=model, name=name, track=False)

    def score(
        self,
        input: str,
        output: str,
        retrieved_context: list[str],
        **ignored_kwargs: Any,
    ) -> ScoreResult:
        if not retrieved_context:
            return ScoreResult(
                name=self.name,
                value=0.0,
                reason="本轮未调用检索，忠实度无从谈起",
                scoring_failed=True,
            )

        result = self._judge.score(
            input=input, output=output, context=list(retrieved_context)
        )
        return ScoreResult(name=self.name, value=result.value, reason=result.reason)


class ToolCalled(BaseMetric):
    def __init__(self, name: str = "tool_called") -> None:
        super().__init__(name=name, track=False)

    def score(self, retrieved_context: list[str], **ignored_kwargs: Any) -> ScoreResult:
        called = bool(retrieved_context)
        return ScoreResult(
            name=self.name,
            value=1.0 if called else 0.0,
            reason=f"检索到 {len(retrieved_context)} 段" if called else "未调用检索",
        )
