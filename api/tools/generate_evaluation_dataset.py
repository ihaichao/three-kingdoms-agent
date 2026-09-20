from loguru import logger

from three_kingdoms.application.evaluation.generate_dataset import generate_dataset
from three_kingdoms.config import settings

if __name__ == "__main__":
    dataset = generate_dataset()
    dataset.to_json(settings.EVALUATION_DATASET_FILE_PATH)
    logger.info(f"已写入 {settings.EVALUATION_DATASET_FILE_PATH}")
