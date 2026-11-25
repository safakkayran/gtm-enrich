"""Waterfall enrichment engine."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from gtm_enrich.models import (
    EnrichedAccount,
    ICPConfig,
    ProviderName,
    ProviderResult,
    RunResult,
    WaterfallConfig,
    WaterfallField,
)
from gtm_enrich.providers import (
    fetch_dns,
    fetch_github,
    fetch_rss,
    fetch_site_checks,
    fetch_website,
)
from gtm_enrich.research import research_accounts

PROVIDER_FUNCS: dict[ProviderName, Callable[[str], Any]] = {
    ProviderName.WEBSITE: fetch_website,
    ProviderName.SITE_CHECKS: fetch_site_checks,
    ProviderName.DNS: fetch_dns,
    ProviderName.GITHUB: fetch_github,
    ProviderName.RSS: fetch_rss,
}


@dataclass
class WaterfallResult:
    """Result of waterfall enrichment for a single domain."""

    domain: str
    fields: dict[str, WaterfallField]
    provider_results: list[ProviderResult]
    total_latency_ms: int
    started_at: float


def _waterfall_field_name(provider: ProviderName, field: str) -> str:
    """Generate unique field key with provider prefix."""
    return f"{provider.value}.{field}"


async def enrich_domain(
    domain: str,
    config: WaterfallConfig,
) -> WaterfallResult:
    """Run waterfall enrichment for a single domain."""
    started = time.time()
    all_fields: dict[str, WaterfallField] = {}
    provider_results: list[ProviderResult] = []

    for provider_name in config.provider_order:
        if provider_name not in PROVIDER_FUNCS:
            continue

        provider_func = PROVIDER_FUNCS[provider_name]
        result = await provider_func(domain)
        provider_results.append(result)

        if result.ok and result.fields:
            for field_name, field_value in result.fields.items():
                key = _waterfall_field_name(provider_name, field_name)
                if key not in all_fields:
                    all_fields[key] = WaterfallField(
                        value=field_value,
                        provider=provider_name,
                        latency_ms=result.latency_ms,
                        cost_usd=result.cost_usd,
                    )

    total_latency = int((time.time() - started) * 1000)
    return WaterfallResult(
        domain=domain,
        fields=all_fields,
        provider_results=provider_results,
        total_latency_ms=total_latency,
        started_at=started,
    )


def _get_waterfall_value(
    fields: dict[str, WaterfallField],
    provider: ProviderName,
    name: str,
    default=None,
):
    """Get value from waterfall fields."""
    key = _waterfall_field_name(provider, name)
    field = fields.get(key)
    return field.value if field else default


def _has_value(field: WaterfallField | None) -> bool:
    """Check if WaterfallField has a truthy value."""
    return field is not None and bool(field.value)


def _wrap_field(value: Any, provider: ProviderName, latency_ms: int = 0) -> WaterfallField | None:
    """Wrap a value in WaterfallField if not None."""
    if value is None:
        return None
    return WaterfallField(value=value, provider=provider, latency_ms=latency_ms, cost_usd=0.0)


def _score_icp(account: EnrichedAccount, icp: ICPConfig) -> tuple[int, list[str]]:
    """Score account against ICP criteria. Returns (score, reasons)."""
    score = 0
    reasons = []

    # B2B SaaS indicator: has pricing page
    if _has_value(account.pricing_page_url):
        score += icp.weight_pricing_page
        reasons.append("Has pricing page")

    # Active hiring: has open roles or careers page
    has_roles = _has_value(account.open_roles)
    has_careers = _has_value(account.careers_page_url)
    if has_roles or has_careers:
        score += icp.weight_active_hiring
        reasons.append("Active hiring signals")

    # Tech stack signals
    if _has_value(account.tech_hints):
        tech_count = len(account.tech_hints.value)
        score += min(tech_count * icp.weight_tech_per_signal, icp.max_tech_score)
        reasons.append(f"Tech stack: {', '.join(account.tech_hints.value[:3])}")

    # GitHub presence
    has_org = _has_value(account.github_org)
    has_repo = _has_value(account.github_repo)
    if has_org or has_repo:
        score += icp.weight_github
        reasons.append("GitHub presence")

    # Content marketing: recent blog posts
    if _has_value(account.latest_blog_titles):
        blog_count = len(account.latest_blog_titles.value)
        score += min(blog_count * icp.weight_blog_per_post, icp.max_blog_score)
        reasons.append(f"Active blog ({blog_count} posts)")

    # Email provider professional
    if _has_value(account.email_provider) and account.email_provider.value != "Other":
        score += icp.weight_pro_email
        reasons.append(f"Pro email: {account.email_provider.value}")

    # Site quality signals
    has_title = _has_value(account.site_title)
    has_meta = _has_value(account.meta_description)
    has_h1 = _has_value(account.h1_count) and account.h1_count.value > 0
    if has_title and has_meta and has_h1:
        score += icp.weight_site_quality
        reasons.append("Good on-page SEO")

    if _has_value(account.has_schema_org):
        score += icp.weight_schema
        reasons.append("Schema.org markup")

    if _has_value(account.has_sitemap):
        score += icp.weight_sitemap
        reasons.append("Sitemap present")

    if _has_value(account.has_llms_txt):
        score += icp.weight_llms_txt
        reasons.append("llms.txt present")

    return score, reasons


def build_enriched_account(
    domain: str,
    waterfall: WaterfallResult,
    icp: ICPConfig,
) -> EnrichedAccount:
    """Build EnrichedAccount from waterfall result."""
    fields = waterfall.fields

    # Website fields
    description = _get_waterfall_value(fields, ProviderName.WEBSITE, "description")
    pricing_page_url = _get_waterfall_value(fields, ProviderName.WEBSITE, "pricing_page_url")
    pricing_page_text = _get_waterfall_value(fields, ProviderName.WEBSITE, "pricing_page_text")
    careers_page_url = _get_waterfall_value(fields, ProviderName.WEBSITE, "careers_page_url")
    careers_page_text = _get_waterfall_value(fields, ProviderName.WEBSITE, "careers_page_text")
    open_roles = _get_waterfall_value(fields, ProviderName.WEBSITE, "open_roles", [])
    blog_page_url = _get_waterfall_value(fields, ProviderName.WEBSITE, "blog_page_url")
    latest_blog_titles = _get_waterfall_value(
        fields, ProviderName.WEBSITE, "latest_blog_titles", []
    )
    tech_hints = _get_waterfall_value(fields, ProviderName.WEBSITE, "tech_hints", [])

    # Site checks fields
    site_title = _get_waterfall_value(fields, ProviderName.SITE_CHECKS, "site_title")
    meta_description = _get_waterfall_value(fields, ProviderName.SITE_CHECKS, "meta_description")
    h1_count = _get_waterfall_value(fields, ProviderName.SITE_CHECKS, "h1_count", 0)
    has_llms_txt = _get_waterfall_value(fields, ProviderName.SITE_CHECKS, "has_llms_txt", False)
    has_sitemap = _get_waterfall_value(fields, ProviderName.SITE_CHECKS, "has_sitemap", False)
    has_schema_org = _get_waterfall_value(fields, ProviderName.SITE_CHECKS, "has_schema_org", False)

    # DNS fields
    mx_records = _get_waterfall_value(fields, ProviderName.DNS, "mx_records", [])
    email_provider = _get_waterfall_value(fields, ProviderName.DNS, "email_provider")

    # GitHub fields
    github_org = _get_waterfall_value(fields, ProviderName.GITHUB, "github_org")
    github_org_name = _get_waterfall_value(fields, ProviderName.GITHUB, "github_org_name")
    github_repo = _get_waterfall_value(fields, ProviderName.GITHUB, "github_repo")
    github_stars = _get_waterfall_value(fields, ProviderName.GITHUB, "github_stars")
    github_public_repos = _get_waterfall_value(
        fields, ProviderName.GITHUB, "github_org_public_repos"
    )
    github_top_repos = _get_waterfall_value(fields, ProviderName.GITHUB, "github_top_repos", [])

    # RSS fields
    feed_url = _get_waterfall_value(fields, ProviderName.RSS, "feed_url")
    feed_title = _get_waterfall_value(fields, ProviderName.RSS, "feed_title")
    recent_posts = _get_waterfall_value(fields, ProviderName.RSS, "recent_posts", [])

    account = EnrichedAccount(
        domain=domain,
        description=_wrap_field(description, ProviderName.WEBSITE),
        pricing_page_url=_wrap_field(pricing_page_url, ProviderName.WEBSITE),
        pricing_page_text=_wrap_field(pricing_page_text, ProviderName.WEBSITE),
        careers_page_url=_wrap_field(careers_page_url, ProviderName.WEBSITE),
        careers_page_text=_wrap_field(careers_page_text, ProviderName.WEBSITE),
        open_roles=_wrap_field(open_roles, ProviderName.WEBSITE),
        blog_page_url=_wrap_field(blog_page_url, ProviderName.WEBSITE),
        latest_blog_titles=_wrap_field(latest_blog_titles, ProviderName.WEBSITE),
        tech_hints=_wrap_field(tech_hints, ProviderName.WEBSITE),
        site_title=_wrap_field(site_title, ProviderName.SITE_CHECKS),
        meta_description=_wrap_field(meta_description, ProviderName.SITE_CHECKS),
        h1_count=_wrap_field(h1_count, ProviderName.SITE_CHECKS),
        has_llms_txt=_wrap_field(has_llms_txt, ProviderName.SITE_CHECKS),
        has_sitemap=_wrap_field(has_sitemap, ProviderName.SITE_CHECKS),
        has_schema_org=_wrap_field(has_schema_org, ProviderName.SITE_CHECKS),
        mx_records=_wrap_field(mx_records, ProviderName.DNS),
        email_provider=_wrap_field(email_provider, ProviderName.DNS),
        github_org=_wrap_field(github_org, ProviderName.GITHUB),
        github_org_name=_wrap_field(github_org_name, ProviderName.GITHUB),
        github_repo=_wrap_field(github_repo, ProviderName.GITHUB),
        github_stars=_wrap_field(github_stars, ProviderName.GITHUB),
        github_public_repos=_wrap_field(github_public_repos, ProviderName.GITHUB),
        github_top_repos=_wrap_field(github_top_repos, ProviderName.GITHUB),
        rss_feed_url=_wrap_field(feed_url, ProviderName.RSS),
        rss_feed_title=_wrap_field(feed_title, ProviderName.RSS),
        rss_latest_items=_wrap_field(recent_posts, ProviderName.RSS),
    )

    # Score ICP
    score, reasons = _score_icp(account, icp)
    account.icp_score = score
    account.icp_reasons = reasons

    return account


async def run_enrichment(
    domains: list[str],
    waterfall_config: WaterfallConfig,
    icp_config: ICPConfig,
) -> RunResult:
    """Run enrichment for multiple domains."""

    start_time = time.time()
    accounts = []
    all_provider_results = []

    for domain in domains:
        waterfall = await enrich_domain(domain, waterfall_config)
        account = build_enriched_account(domain, waterfall, icp_config)
        accounts.append(account)
        all_provider_results.extend(waterfall.provider_results)

    # Research step
    briefs = research_accounts(accounts, icp_config.description)

    total_latency = int((time.time() - start_time) * 1000)
    return RunResult(
        accounts=accounts,
        briefs=briefs,
        total_latency_ms=total_latency,
        total_cost_usd=0.0,
        provider_stats={},
        total_domains=len(domains),
        successful=sum(1 for a in accounts if a.icp_score > 0),
        provider_results=all_provider_results,
    )