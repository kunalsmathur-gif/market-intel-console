"""Worker settings, read from environment variables (see apps/worker/.env.example).

Provider keys live only here, in the worker, never in the web app (PRD §8.1).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

WORKER_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PRIVATE_CONFIG = WORKER_ROOT / "examples" / "private-config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: SecretStr | None = None

    # Prompts, the source registry and eval goldens live in a private repo.
    # Unset means the public examples, which are only good for tests and local runs.
    private_config_dir: Path | None = None

    gemini_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None

    # Model per pipeline step as "provider:model". Placeholders until the bake-off
    # (PRD §8.12) picks per step; each step can name a backup from another vendor.
    llm_classify: str = "gemini:gemini-2.5-flash-lite"
    llm_extract: str = "gemini:gemini-2.5-flash-lite"
    llm_verify: str = "gemini:gemini-2.5-flash"
    llm_write: str = "gemini:gemini-2.5-flash-lite"
    llm_qa: str = "gemini:gemini-2.5-flash-lite"
    llm_classify_backup: str | None = None
    llm_extract_backup: str | None = None
    llm_verify_backup: str | None = None
    llm_write_backup: str | None = None
    llm_qa_backup: str | None = None
    llm_timeout_seconds: float = 60.0

    # Pinged after each scheduled run so an outside monitor alerts when a run doesn't check in.
    healthcheck_ping_url: str | None = None

    @property
    def resolved_private_config_dir(self) -> Path:
        return self.private_config_dir or EXAMPLE_PRIVATE_CONFIG

    @property
    def using_example_config(self) -> bool:
        return self.private_config_dir is None


@lru_cache
def get_settings() -> Settings:
    return Settings()
