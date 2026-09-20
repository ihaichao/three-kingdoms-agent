from langchain_openai import OpenAIEmbeddings

from three_kingdoms.config import settings


def get_embedding_model() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY.get_secret_value(),
        model=settings.RAG_TEXT_EMBEDDING_MODEL_ID,
        check_embedding_ctx_length=False,
    )
