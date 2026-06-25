"""Application settings, loaded from environment variables (and an optional .env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database connection URL. Required — there is intentionally no default, so
    # that no credentials are ever hardcoded in the repo. Set DATABASE_URL in the
    # environment (or a local .env). In Docker, docker-compose builds it from the
    # POSTGRES_* variables; for local dev set it yourself, e.g.
    #   postgresql+asyncpg://<user>:<password>@localhost:5431/<db>
    # (the host-published Postgres port is 5431, mapped to container 5432).
    database_url: str

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
