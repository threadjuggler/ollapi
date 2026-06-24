"""Application settings, loaded from environment variables (and an optional .env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — defaults target the local docker-compose setup. Note that the
    # host-published port is 5431, but inside the compose network the app talks
    # to the "db" service on the standard 5432.
    database_url: str = (
        "postgresql+asyncpg://ollapi:REDACTED@localhost:5431/ollapi"
    )

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e2b"
    auto_pull_model: bool = True

    # Default generation settings used to seed the editable app config row.
    default_system_prompt: str = "You are a helpful assistant."
    default_temperature: float = 0.7
    default_top_p: float = 0.9
    default_num_ctx: int = 4096
    default_num_predict: int = -1  # -1 = unlimited (until model stops)


settings = Settings()
