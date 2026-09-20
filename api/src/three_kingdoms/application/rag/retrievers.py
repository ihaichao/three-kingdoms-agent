from langchain_mongodb import MongoDBAtlasVectorSearch

from three_kingdoms.application.rag.embeddings import get_embedding_model
from three_kingdoms.config import settings


def get_vectorstore() -> MongoDBAtlasVectorSearch:
    return MongoDBAtlasVectorSearch.from_connection_string(
        connection_string=settings.MONGO_URI,
        embedding=get_embedding_model(),
        namespace=f"{settings.MONGO_DB_NAME}.{settings.MONGO_LONG_TERM_MEMORY_COLLECTION}",
        text_key="chunk",
        embedding_key="embedding",
        relevance_score_fn="cosine",
    )


def get_retriever(k: int | None = None, character_id: str | None = None):
    search_kwargs: dict = {"k": k or settings.RAG_TOP_K}
    if character_id:
        search_kwargs["pre_filter"] = {"character_id": {"$eq": character_id}}
    return get_vectorstore().as_retriever(search_kwargs=search_kwargs)
