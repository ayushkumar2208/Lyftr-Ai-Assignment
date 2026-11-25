from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lyftr AI Chatbot"
    app_env: str = "development"

    # LLM
    llm_model: str = "gemini/gemini-3.5-flash-lite"
    llm_api_keys: str = ""
    default_system_prompt: str = (
        "You are a helpful, concise, and accurate AI assistant."
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Frontend / CORS
    allowed_origins: str = "http://localhost:3000"

    # Assignment failover testing
    enable_failure_simulation: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def api_keys(self) -> list[str]:
        return [
            key.strip()
            for key in self.llm_api_keys.split(",")
            if key.strip()
        ]

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()