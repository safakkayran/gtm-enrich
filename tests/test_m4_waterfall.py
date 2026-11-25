"""M4 waterfall engine tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

if TYPE_CHECKING:
    from respx import MockRouter

from gtm_enrich.config import get_default_icp_config
from gtm_enrich.models import ProviderName, WaterfallConfig
from gtm_enrich.waterfall import run_enrichment

EXPECTED_DOMAINS = 2


@pytest.mark.asyncio
async def test_waterfall_single_domain(respx_mock: MockRouter):
    """Waterfall enriches a single domain with all providers."""
    # Website - use direct fetch (Jina might not match URL exactly)
    respx_mock.get("https://example.com/").mock(
        return_value=httpx.Response(
            200,
            text=(
                "<html>"
                "<head><title>Example</title></head>"
                "<body>"
                "Example B2B SaaS company"
                '<a href="/pricing">Pricing</a>'
                '<a href="/careers">Careers</a>'
                '<a href="/blog">Blog</a>'
                "</body>"
                "</html>"
            ),
        ),
    )
    respx_mock.get("https://example.com/pricing").mock(
        return_value=httpx.Response(200, text="<html><body>Pricing</body></html>")
    )
    respx_mock.get("https://example.com/careers").mock(
        return_value=httpx.Response(200, text="<html><body>Senior Engineer</body></html>")
    )
    respx_mock.get("https://example.com/blog").mock(
        return_value=httpx.Response(200, text="<html><body><h2>Post 1</h2></body></html>")
    )

    # Site checks
    respx_mock.get("https://example.com/llms.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *")
    )
    respx_mock.get("https://example.com/sitemap.xml").mock(
        return_value=httpx.Response(200, text="<xml/>")
    )

    # DNS - will fail gracefully (no real DNS)
    # GitHub - will fail gracefully (404)
    respx_mock.get("https://api.github.com/orgs/example").mock(
        return_value=httpx.Response(404)
    )
    # RSS - not in provider_order, so won't be called
    # No need to mock RSS endpoints

    config = WaterfallConfig(provider_order=[ProviderName.WEBSITE, ProviderName.SITE_CHECKS])
    icp = get_default_icp_config()

    result = await run_enrichment(["example.com"], config, icp)

    assert result.total_domains == 1
    assert len(result.accounts) == 1
    account = result.accounts[0]
    assert account.domain == "example.com"
    assert account.description is not None
    assert "Example B2B SaaS" in account.description.value
    assert account.icp_score > 0
    assert "Has pricing page" in account.icp_reasons


@pytest.mark.asyncio
async def test_waterfall_provenance_first_wins(respx_mock: MockRouter):
    """First provider in waterfall wins for each field."""
    # First provider (website) returns description
    respx_mock.get("https://r.jina.ai/http://https://example.com/").mock(
        return_value=httpx.Response(200, text="From Website Provider")
    )
    respx_mock.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="<html><body>Home</body></html>")
    )

    # Second provider (site_checks) also has a title
    respx_mock.get("https://example.com/llms.txt").mock(return_value=httpx.Response(404))
    respx_mock.get("https://example.com/sitemap.xml").mock(return_value=httpx.Response(404))

    config = WaterfallConfig(provider_order=[ProviderName.WEBSITE, ProviderName.SITE_CHECKS])
    icp = get_default_icp_config()

    result = await run_enrichment(["example.com"], config, icp)

    account = result.accounts[0]
    # Website provider should win for description
    assert account.description is not None
    assert account.description.provider == ProviderName.WEBSITE


@pytest.mark.asyncio
async def test_waterfall_multiple_domains(respx_mock: MockRouter):
    """Waterfall handles multiple domains."""
    for domain in ["example.com", "test.com"]:
        respx_mock.get(f"https://r.jina.ai/http://https://{domain}/").mock(
            return_value=httpx.Response(200, text=f"{domain} description")
        )
        respx_mock.get(f"https://{domain}/").mock(
            return_value=httpx.Response(200, text=f"<html><body>{domain}</body></html>")
        )
        respx_mock.get(f"https://{domain}/llms.txt").mock(return_value=httpx.Response(404))
        respx_mock.get(f"https://{domain}/sitemap.xml").mock(return_value=httpx.Response(404))

    config = WaterfallConfig(provider_order=[ProviderName.WEBSITE, ProviderName.SITE_CHECKS])
    icp = get_default_icp_config()

    result = await run_enrichment(["example.com", "test.com"], config, icp)

    assert result.total_domains == EXPECTED_DOMAINS
    assert len(result.accounts) == EXPECTED_DOMAINS
    assert result.accounts[0].domain == "example.com"
    assert result.accounts[1].domain == "test.com"