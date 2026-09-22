import os
from pathlib import Path
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

    RAG_TEXT_EMBEDDING_MODEL_ID: str = "baai/bge-m3"
    RAG_TEXT_EMBEDDING_MODEL_DIM: int = 1024
    RAG_CHUNK_SIZE: int = 700
    RAG_TOP_K: int = 5

    MONGO_URI: str = Field(
        default="mongodb://tkagent:tkagent@local_dev_atlas:27017/?directConnection=true",
        description="Connection URI for the local MongoDB Atlas instance.",
    )
    MONGO_DB_NAME: str = "three_kingdoms"
    MONGO_STATE_CHECKPOINT_COLLECTION: str = "state_checkpoints"
    MONGO_STATE_WRITES_COLLECTION: str = "state_writes"
    MONGO_LONG_TERM_MEMORY_COLLECTION: str = "long_term_memory"
    MONGO_VECTOR_INDEX_NAME: str = "vector_index"

    COMET_API_KEY: str | None = Field(
        default=None, description="API key for Comet ML and Opik services."
    )
    COMET_PROJECT: str = Field(
        default="three-kingdoms-agent",
        description="Project name for Comet ML and Opik tracking.",
    )

    # --- 部署 ---
    # 允许访问的前端来源，逗号分隔，在 .env 里配。
    # 留空 = 本地开发模式，放行 localhost 常用端口（见 api.py）。
    # 生产必须填成 CDN 上那个域名。不能留空，更不能填 "*"。
    ALLOWED_ORIGINS: str = ""

    # /reset-memory 的口令。留空 = 该接口不注册（生产默认就该这样）。
    # 它会清掉所有人的对话状态，公开暴露等于给全世界一个重置按钮。
    ADMIN_TOKEN: SecretStr | None = None

    CORPUS: Literal["yanyi", "zhi"] = "yanyi"

    EVALUATION_DATASET_FILE_PATH: Path = Path("data/evaluation_dataset.json")
    # 数据集改了结构或出题规则就**换名字**，不要往旧的里灌。
    # Opik 的 insert 是幂等追加（deduplication=True），新旧混在一起会变成
    # 400 条半新半旧的题，基线就毁了。换名字还能留着旧数据集做对照。
    #   v1 = 单 chunk 当 context，出题没有时空定语约束（基线 0.181，已废弃）
    #   v2 = context 扩到前后各一段，出题强制时空定语 + 独立成立自检
    OPIK_DATASET_NAME: str = "three_kingdoms_qa_v2"
    EVALUATION_JUDGE_MODEL: str = "openrouter/openai/gpt-4o-mini"
    EVALUATION_SAMPLE_SIZE: int = 200
    # 判官的 context 往前后各扩几段（同一回之内）。
    # 0 = 只给出题依据的那一段（会产生大量误判，见 EvaluationSample.context_window）。
    # 1 ≈ 2100 字，够覆盖"前后贯通的背景"这类误判，判官又不至于大海捞针。
    # 想试整回就调大，判官成本大致线性增长。
    EVALUATION_CONTEXT_NEIGHBORS: int = 1

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
