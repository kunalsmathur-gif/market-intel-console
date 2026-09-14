"""Worker settings, read from environment variables (see apps/worker/.env.example).

Provider keys live only here, in the worker, never in the web app (PRD §8.1).
"""

import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

WORKER_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PRIVATE_CONFIG = WORKER_ROOT / "examples" / "private-config"


class Settings(BaseSettings):
    # env_ignore_empty: a blank line copied from .env.example (e.g. PRIVATE_CONFIG_DIR=) means "not set".
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    database_url: SecretStr | None = None

    # Prompts, the source registry and eval goldens live in a private repo. Use either a local
    # checkout (PRIVATE_CONFIG_DIR) or, on Railway, a download from GitHub at a pinned ref with a
    # read-only fine-grained token. Neither set means the public examples: tests and local runs only.
    private_config_dir: Path | None = None
    private_config_repo: str | None = None  # e.g. "kunalsmathur-gif/citebell-private"
    private_config_ref: str = "main"  # pin a commit SHA or tag in production
    private_config_token: SecretStr | None = None
    private_config_cache_dir: Path = Path(tempfile.gettempdir()) / "citebell-private-config"

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

    # The scheduler pings this every few minutes; an outside monitor alerts when the pings stop.
    healthcheck_ping_url: str | None = None
    heartbeat_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
