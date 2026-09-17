import os
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )

    LLM_PROVIDER: Literal["groq", "openrouter"] = "openrouter"

    OPENROUTER_API_KEY: SecretStr | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_LLM_MODEL: str = "deepseek/deepseek-chat"

    GROQ_API_KEY: SecretStr | None = None
    GROQ_LLM_MODEL: str = "llama-3.3-70b-versatile"

    MONGO_URI: str = Field(
        default="mongodb://tkagent:tkagent@local_dev_atlas:27017/?directConnection=true",
        description="Connection URI for the local MongoDB Atlas instance.",
    )
    MONGO_DB_NAME: str = "three_kingdoms"
    MONGO_STATE_CHECKPOINT_COLLECTION: str = "state_checkpoints"
    MONGO_STATE_WRITES_COLLECTION: str = "state_writes"

    COMET_API_KEY: str | None = Field(
        default=None, description="API key for Comet ML and Opik services."
    )
    COMET_PROJECT: str = Field(
        default="three-kingdoms-agent",
        description="Project name for Comet ML and Opik tracking.",
    )

    TOTAL_MESSAGES_SUMMARY_TRIGGER: int = 30
    TOTAL_MESSAGES_AFTER_SUMMARY: int = 5

    @model_validator(mode="after")
    def check_provider_key(self) -> "Settings":
        if self.LLM_PROVIDER == "openrouter" and not self.OPENROUTER_API_KEY:
            raise ValueError(
                "Openrouter is selected but OPENROUTER_API_KEY is not set."
            )
        if self.LLM_PROVIDER == "groq" and not self.GROQ_API_KEY:
            raise ValueError("Groq is selected but GROQ_API_KEY is not set.")

        if self.COMET_API_KEY:
            os.environ.setdefault("OPIK_API_KEY", self.COMET_API_KEY)
            os.environ.setdefault("COMET_API_KEY", self.COMET_API_KEY)
            os.environ.setdefault("OPIK_PROJECT_NAME", self.COMET_PROJECT)

        return self


settings = Settings()
