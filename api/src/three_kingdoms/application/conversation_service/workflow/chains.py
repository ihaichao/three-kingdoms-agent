from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from three_kingdoms.config import settings
from three_kingdoms.domain.prompts import CHARACTER_CARD


def get_chat_model(
    temperature: float = 0.7, model_name: str | None = None
) -> BaseChatModel:
    if settings.LLM_PROVIDER == "openrouter":
        return ChatOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY.get_secret_value(),
            model=model_name or settings.OPENROUTER_LLM_MODEL,
            temperature=temperature,
        )

    if settings.LLM_PROVIDER == "groq":
        return ChatGroq(
            api_key=settings.GROQ_API_KEY.get_secret_value(),
            model_name=model_name or settings.GROQ_LLM_MODEL,
            temperature=temperature,
        )

    raise ValueError(f"Invalid LLM provider: {settings.LLM_PROVIDER}")


def get_character_response_chain():
    model = get_chat_model()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHARACTER_CARD.prompt),
            MessagesPlaceholder(variable_name="messages"),
        ],
        template_format="jinja2",
    )
    return prompt | model
