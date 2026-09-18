from langgraph.checkpoint.mongodb import MongoDBSaver
from loguru import logger
from pymongo import MongoClient

from three_kingdoms.config import settings

_client: MongoClient | None = None
_saver: MongoDBSaver | None = None


def init_checkpointer() -> None:
    global _client, _saver
    _client = MongoClient(settings.MONGO_URI)
    _saver = MongoDBSaver(
        _client,
        db_name=settings.MONGO_DB_NAME,
        checkpoint_collection_name=settings.MONGO_STATE_CHECKPOINT_COLLECTION,
        writes_collection_name=settings.MONGO_STATE_WRITES_COLLECTION,
    )
    logger.info("MongoDB checkpointer 已初始化")


def get_checkpointer() -> MongoDBSaver:
    if _saver is None:
        raise RuntimeError("checkpointer 未初始化，请检查 FastAPI lifespan")
    return _saver


def close_checkpointer() -> None:
    global _client, _saver
    _client.close()
    _client = None
    _saver = None
