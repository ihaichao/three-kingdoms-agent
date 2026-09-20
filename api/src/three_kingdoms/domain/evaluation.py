import json
from pathlib import Path

from pydantic import BaseModel, Field


class EvaluationSample(BaseModel):
    question: str
    character_id: str
    expected_answer: str
    # 出题所依据的那一段，跟向量库里存的 chunk 逐字一致。
    # 将来要算 recall@k 就靠它对齐，别动。
    source_chunk: str
    # source_chunk 加上它在同一回里的前后邻居。判官用这个当 context。
    #
    # 为什么不直接用 source_chunk：实测最差的 20 条里有 30% 是判官误判——
    # agent 答得完全正确，只是提到了同一回里前后贯通的背景，而判官只看得见
    # 那 700 字的单块，就判"context 里没有"，给 0.8-1.0 的满分幻觉。
    # 这是评法的缺陷，不是 agent 的。
    context_window: str
    volume: str


class EvaluationDataset(BaseModel):
    samples: list[EvaluationSample]

    @classmethod
    def from_json(cls, file_path: Path) -> "EvaluationDataset":
        return cls.model_validate_json(file_path.read_text(encoding="utf-8"))

    def to_json(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(
            json.dumps(self.model_dump(), indent=4, ensure_ascii=False),
            encoding="utf-8",
        )


class GeneratedQuestion(BaseModel):
    question: str = Field(description="玩家会问的问题，现代口语，一句话，不超过40字")
    expected_answer: str = Field(description="参考答案，现代白话，一到两句，不超过60字")
