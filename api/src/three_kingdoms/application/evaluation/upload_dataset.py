import opik
from loguru import logger

from three_kingdoms.config import settings
from three_kingdoms.domain.evaluation import EvaluationDataset


def upload_dataset() -> opik.Dataset:
    """把本地评测集推到 Opik。

    键名直接起成 Opik 指标要的参数名（input / expected_output / context），
    """
    dataset = EvaluationDataset.from_json(settings.EVALUATION_DATASET_FILE_PATH)

    items = [
        {
            "input": sample.question,
            "expected_output": sample.expected_answer,
            # 判官的 context 用带前后文的窗口，不是单块——单块会把
            # "答案提到了同一回的背景"误判成幻觉（实测占最差样本的 30%）。
            "context": [sample.context_window],
            # 原始那一块也带上，将来算检索指标要用，指标本身不读它。
            "source_chunk": sample.source_chunk,
            "character_id": sample.character_id,
            "volume": sample.volume,
        }
        for sample in dataset.samples
    ]

    client = opik.Opik()
    opik_dataset = client.get_or_create_dataset(name=settings.OPIK_DATASET_NAME)
    opik_dataset.insert(items)

    logger.info(f"已上传 {len(items)} 条到 Opik 数据集 {settings.OPIK_DATASET_NAME}")
    return opik_dataset
