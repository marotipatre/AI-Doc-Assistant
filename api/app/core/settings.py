from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./repolens.db"
    redis_url: str = ""
    llm_provider: Literal["gemini", "openai", "groq"] = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    retrieval_mode: Literal["lexical", "hybrid"] = "lexical"
    max_output_tokens: int = Field(default=1200, ge=256, le=4096)
    evidence_char_budget: int = Field(default=7000, ge=2000, le=16000)
    history_char_budget: int = Field(default=2000, ge=0, le=6000)
    answer_cache_enabled: bool = True
    answer_cache_ttl_seconds: int = Field(default=3600, ge=0, le=86400)
    gemini_api_key: str = ""
    gemini_model: str = Field(default="gemini-2.5-flash", pattern=r"^(models/)?[a-zA-Z0-9._-]+$")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001", pattern=r"^(models/)?[a-zA-Z0-9._-]+$"
    )
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=1536, ge=1536, le=1536)
    github_token: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:3000/api/backend/v1/auth/github/callback"
    token_encryption_key: str = ""
    session_secret: str = ""
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    environment: str = "development"
    seed_demo: bool = True
    max_files: int = 150
    max_file_bytes: int = 150_000
    max_repository_bytes: int = 8_000_000
    requests_per_minute: int = 90
    messages_per_minute: int = 12
    indexing_per_hour: int = 10

    @property
    def provider_configured(self) -> bool:
        if self.llm_provider == "groq":
            return bool(self.groq_api_key)
        return bool(self.gemini_api_key if self.llm_provider == "gemini" else self.openai_api_key)

    @property
    def embeddings_enabled(self) -> bool:
        return (
            self.retrieval_mode == "hybrid"
            and self.llm_provider != "groq"
            and self.provider_configured
        )

    @property
    def provider_label(self) -> str:
        if self.llm_provider == "groq":
            return "Groq"
        return "Gemini" if self.llm_provider == "gemini" else "OpenAI"

    @property
    def provider_key_name(self) -> str:
        if self.llm_provider == "groq":
            return "GROQ_API_KEY"
        return "GEMINI_API_KEY" if self.llm_provider == "gemini" else "OPENAI_API_KEY"

    @property
    def chat_model(self) -> str:
        if self.llm_provider == "groq":
            return self.groq_model
        return self.gemini_model if self.llm_provider == "gemini" else self.openai_model

    @property
    def embedding_identity(self) -> str:
        if self.llm_provider == "groq":
            return "lexical:none"
        model = (
            self.gemini_embedding_model.removeprefix("models/")
            if self.llm_provider == "gemini"
            else self.openai_embedding_model
        )
        return f"{self.llm_provider}:{model}:{self.embedding_dimensions}:v1"

    @property
    def oauth_configured(self) -> bool:
        return bool(
            self.github_client_id
            and self.github_client_secret
            and self.token_encryption_key
            and self.session_secret
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
