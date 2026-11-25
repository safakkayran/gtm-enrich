"""M5 research tests."""

from __future__ import annotations

import pytest

from gtm_enrich.models import EnrichedAccount, ProviderName, WaterfallField
from gtm_enrich.research import extract_signals, generate_research_brief, research_accounts

MIN_SIGNALS_WEBSITE = 5
MIN_FIT_SCORE = 1
MAX_FIT_SCORE = 5
EXPECTED_ACCOUNTS = 2


def _make_account(domain: str, **fields) -> EnrichedAccount:
    """Helper to create EnrichedAccount with WaterfallField values."""
    wrapped = {}
    for k, v in fields.items():
        wrapped[k] = WaterfallField(
            value=v, provider=ProviderName.WEBSITE, latency_ms=10, cost_usd=0.0
        )
    return EnrichedAccount(domain=domain, **wrapped)


@pytest.mark.asyncio
async def test_extract_signals_website():
    """Extract signals from website fields."""
    account = _make_account(
        "example.com",
        description="B2B SaaS platform for teams",
        pricing_page_url="https://example.com/pricing",
        open_roles=["Senior Engineer", "Growth Manager"],
        tech_hints=["HubSpot", "Segment", "Stripe"],
        latest_blog_titles=["Launch v2", "Hiring update"],
    )

    signals = extract_signals(account)

    assert len(signals) >= MIN_SIGNALS_WEBSITE
    texts = [s.text for s in signals]
    assert any("B2B SaaS platform" in t for t in texts)
    assert any("public pricing page" in t for t in texts)
    assert any("Senior Engineer" in t for t in texts)
    assert any("HubSpot" in t for t in texts)
    assert any("Launch v2" in t for t in texts)
    # All signals should have valid source
    assert all(s.source in ProviderName for s in signals)


@pytest.mark.asyncio
async def test_extract_signals_site_checks():
    """Extract signals from site_checks fields."""
    account = _make_account(
        "example.com",
        site_title="Example | B2B SaaS",
        has_schema_org=True,
        has_llms_txt=True,
    )

    signals = extract_signals(account)

    texts = [s.text for s in signals]
    assert any("Site title" in t for t in texts)
    assert any("Schema.org" in t for t in texts)
    assert any("llms.txt" in t for t in texts)


@pytest.mark.asyncio
async def test_extract_signals_dns_github_rss():
    """Extract signals from DNS, GitHub, RSS fields."""
    account = _make_account(
        "example.com",
        email_provider="Google Workspace",
        github_org="example",
        github_stars=420,
        github_top_repos=[{"name": "core"}, {"name": "sdk"}],
        rss_feed_title="Example Blog",
        rss_latest_items=[{"title": "Post 1"}, {"title": "Post 2"}],
    )

    signals = extract_signals(account)

    texts = [s.text for s in signals]
    assert any("Google Workspace" in t for t in texts)
    assert any("GitHub org: example" in t for t in texts)
    assert any("420" in t for t in texts)
    assert any("core, sdk" in t for t in texts)
    assert any("Example Blog" in t for t in texts)
    assert any("Post 1" in t for t in texts)


@pytest.mark.asyncio
async def test_generate_research_brief_fallback():
    """Generate fallback brief when LLM unavailable."""
    account = _make_account(
        "example.com",
        description="B2B SaaS for teams",
        tech_hints=["HubSpot", "Stripe"],
        open_roles=["Senior Engineer"],
    )

    brief = generate_research_brief(account, "B2B SaaS with sales team")

    assert brief.summary
    assert MIN_FIT_SCORE <= brief.icp_fit_score <= MAX_FIT_SCORE
    assert brief.fit_reason
    assert len(brief.angles) >= 1
    for angle in brief.angles:
        assert angle.text
        assert angle.signal_ids
        assert angle.channel in ("email", "linkedin")


@pytest.mark.asyncio
async def test_research_accounts_multiple():
    """Research multiple accounts."""
    accounts = [
        _make_account("example.com", description="Company A"),
        _make_account("test.com", description="Company B"),
    ]

    briefs = research_accounts(accounts, "B2B SaaS")

    assert len(briefs) == EXPECTED_ACCOUNTS
    assert "example.com" in briefs
    assert "test.com" in briefs
    for brief in briefs.values():
        assert brief.summary
        assert brief.icp_fit_score >= MIN_FIT_SCORE