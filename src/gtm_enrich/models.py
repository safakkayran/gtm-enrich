"""Pydantic models for gtm-enrich."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProviderName(StrEnum):
    WEBSITE = "website"
    SITE_CHECKS = "site_checks"
    GITHUB = "github"
    RSS = "rss"
    DNS = "dns"


class Channel(StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"


@dataclass
class ProviderResult:
    """Result from a single provider fetch."""

    provider: ProviderName
    fields: dict[str, Any]
    ok: bool
    error: str | None
    latency_ms: int
    cost_usd: float = 0.0


class WaterfallField(BaseModel):
    """A field enriched via waterfall with provenance."""

    value: Any
    provider: ProviderName
    latency_ms: int
    cost_usd: float


class EnrichedAccount(BaseModel):
    """Company account enriched through the waterfall."""

    domain: str
    company_name: str | None = None
    description: WaterfallField | None = None
    pricing_page_url: WaterfallField | None = None
    pricing_page_text: WaterfallField | None = None
    careers_page_url: WaterfallField | None = None
    careers_page_text: WaterfallField | None = None
    open_roles: WaterfallField | None = None
    blog_page_url: WaterfallField | None = None
    latest_blog_titles: WaterfallField | None = None
    tech_hints: WaterfallField | None = None
    site_title: WaterfallField | None = None
    meta_description: WaterfallField | None = None
    h1_count: WaterfallField | None = None
    has_llms_txt: WaterfallField | None = None
    has_sitemap: WaterfallField | None = None
    has_schema_org: WaterfallField | None = None
    github_org: WaterfallField | None = None
    github_org_name: WaterfallField | None = None
    github_repo: WaterfallField | None = None
    github_stars: WaterfallField | None = None
    github_public_repos: WaterfallField | None = None
    github_top_repos: WaterfallField | None = None
    github_recent_activity: WaterfallField | None = None
    rss_feed_url: WaterfallField | None = None
    rss_feed_title: WaterfallField | None = None
    rss_latest_items: WaterfallField | None = None
    mx_records: WaterfallField | None = None
    email_provider: WaterfallField | None = None
    icp_score: int = 0
    icp_reasons: list[str] = Field(default_factory=list)
    enriched_at: datetime = Field(default_factory=datetime.utcnow)

    def get_field(self, name: str) -> WaterfallField | None:
        return getattr(self, name, None)

    def set_field(
        self,
        name: str,
        value: Any,
        provider: ProviderName,
        latency_ms: int,
        cost_usd: float = 0.0,
    ) -> None:
        if getattr(self, name, None) is None:
            setattr(
                self,
                name,
                WaterfallField(
                    value=value,
                    provider=provider,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd,
                ),
            )


class Signal(BaseModel):
    """A single signal extracted from enrichment for research."""

    id: str
    text: str
    source: ProviderName


class Angle(BaseModel):
    """An outbound angle with signal citations."""

    text: str
    signal_ids: list[str]
    channel: Channel


class ResearchBrief(BaseModel):
    """LLM-generated research brief and angles for an account."""

    summary: str
    icp_fit_score: int = Field(ge=1, le=5)
    fit_reason: str
    angles: list[Angle]


class EvalResult(BaseModel):
    """Result of evaluating a single angle."""

    angle: str
    company: str
    rule_checks: dict[str, bool]
    judge_scores: dict[str, int] | None = None
    judge_reason: str | None = None
    passed: bool = False


class WaterfallConfig(BaseModel):
    """Waterfall configuration for field enrichment."""

    provider_order: list[ProviderName]
    fields: dict[str, list[ProviderName]] = Field(default_factory=dict)


class ICPConfig(BaseModel):
    """Ideal Customer Profile configuration."""

    description: str
    positive_signals: list[str]
    negative_signals: list[str]

    # Weights for scoring
    weight_pricing_page: int = 10
    weight_active_hiring: int = 15
    weight_tech_per_signal: int = 3
    max_tech_score: int = 15
    weight_github: int = 10
    weight_blog_per_post: int = 2
    max_blog_score: int = 10
    weight_pro_email: int = 5
    weight_site_quality: int = 5
    weight_schema: int = 3
    weight_sitemap: int = 2
    weight_llms_txt: int = 2


class RunResult(BaseModel):
    """Result of a run command."""

    accounts: list[EnrichedAccount]
    briefs: dict[str, ResearchBrief]  # domain -> brief
    total_latency_ms: int
    total_cost_usd: float
    provider_stats: dict[str, dict]  # provider -> {hits, misses, total_latency, total_cost}
    total_domains: int = 0
    successful: int = 0
    provider_results: list[ProviderResult] = Field(default_factory=list)