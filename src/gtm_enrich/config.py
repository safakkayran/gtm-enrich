"""Configuration settings for gtm-enrich."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from gtm_enrich.models import ICPConfig, ProviderName, WaterfallConfig

DEFAULT_PROVIDER_ORDER = [
    ProviderName.WEBSITE,
    ProviderName.SITE_CHECKS,
    ProviderName.DNS,
    ProviderName.GITHUB,
    ProviderName.RSS,
]


DEFAULT_ICP_CONFIG = ICPConfig(
    description="B2B SaaS with sales team + active hiring",
    positive_signals=[
        "pricing_page",
        "active_hiring",
        "tech_stack_signals",
        "github_presence",
        "active_blog",
        "professional_email",
    ],
    negative_signals=[
        "no_website",
        "personal_email",
        "no_tech_stack",
        "stale_content",
    ],
)


DEFAULT_WATERFALL_CONFIG = WaterfallConfig(
    provider_order=DEFAULT_PROVIDER_ORDER,
)


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LiteLLM
    LLM_MODEL: str = Field(default="nim-laguna", description="Worker model alias")
    LLM_JUDGE_MODEL: str = Field(default="nim-step", description="Judge model alias")
    LITELLM_BASE_URL: str = Field(
        default="http://127.0.0.1:4000", description="LiteLLM proxy base URL"
    )
    LITELLM_API_KEY: str | None = Field(default=None, description="LiteLLM master key")

    # GitHub
    GITHUB_TOKEN: str | None = Field(default=None, description="GitHub PAT for API")
    APIFY_TOKEN: str | None = Field(default=None, description="Apify API token")
    APIFY_MAX_ITEMS: int = Field(default=20, description="Max items per Apify run")

    # Twenty CRM (for push)
    TWENTY_BASE_URL: str = Field(default="http://localhost:3000")
    TWENTY_API_KEY: str | None = Field(default=None)
    TWENTY_REST_PREFIX: str = Field(default="/rest")

    # Cache
    CACHE_DIR: Path = Field(default=Path(".cache/gtm_enrich"))

    # Concurrency
    MAX_CONCURRENCY: int = Field(default=4)

    # Evals
    EVAL_DATASET_PATH: Path = Field(default=Path("evals/dataset.csv"))
    EVAL_BANNED_PATH: Path = Field(default=Path("evals/banned.txt"))

    # Output
    OUTPUT_DIR: Path = Field(default=Path("out"))


def get_default_waterfall_config() -> WaterfallConfig:
    return DEFAULT_WATERFALL_CONFIG


def get_default_icp_config() -> ICPConfig:
    return DEFAULT_ICP_CONFIG


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()