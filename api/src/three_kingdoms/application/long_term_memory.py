from loguru import logger

from three_kingdoms.application.data.extract import get_extraction_generator
from three_kingdoms.application.rag.retrievers import get_vectorstore
from three_kingdoms.application.rag.splitters import get_splitter
from three_kingdoms.config import settings


def _ensure_vector_index(vectorstore) -> None:
    existing = {ix["name"] for ix in vectorstore.collection.list_search_indexes()}

    if settings.MONGO_VECTOR_INDEX_NAME in existing:
        logger.info(f"向量索引 {settings.MONGO_VECTOR_INDEX_NAME} 已存在，跳过")
        return

    vectorstore.create_vector_search_index(
        dimensions=settings.RAG_TEXT_EMBEDDING_MODEL_DIM,
        filters=["character_id"],
        wait_until_complete=120,
    )
    logger.info("向量索引已创建")


def create_long_term_memory(character_ids: list[str] | None = None) -> None:
    vectorstore = get_vectorstore()
    splitter = get_splitter(settings.RAG_CHUNK_SIZE)

    vectorstore.collection.delete_many({})

    for character, docs in get_extraction_generator(character_ids):
        if not docs:
            continue
        chunks = splitter.split_documents(docs)
        vectorstore.add_documents(chunks)
        logger.info(f"{character.name}: {len(chunks)} 块已入库")

    _ensure_vector_index(vectorstore)
