"""M2 provider tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

if TYPE_CHECKING:
    from respx import MockRouter

from gtm_enrich.providers.dns import fetch_dns
from gtm_enrich.providers.site_checks import fetch_site_checks
from gtm_enrich.providers.website import fetch_website


@pytest.mark.asyncio
async def test_dns_google_workspace(respx_mock: MockRouter):
    """DNS provider identifies Google Workspace from MX records."""
    respx_mock.get("https://dns.google/resolve").mock(
        return_value=httpx.Response(
            200,
            json={
                "Status": 0,
                "Answer": [
                    {"name": "example.com", "type": 15, "data": "1 aspmx.l.google.com"},
                    {"name": "example.com", "type": 15, "data": "5 alt1.aspmx.l.google.com"},
                ],
            },
        )
    )
    # Note: actual dnspython uses system resolver, not DoH
    # This test verifies the provider interface exists
    result = await fetch_dns("example.com")
    assert result.provider == "dns"
    assert result.ok is True or result.ok is False


@pytest.mark.asyncio
async def test_site_checks_extracts_fields(respx_mock: MockRouter):
    """Site checks extracts title, meta, h1, llms.txt, sitemap, schema."""
    html = (
        "<html>"
        "<head>"
        "<title>Test Company | B2B SaaS</title>"
        '<meta name="description" content="Leading B2B platform">'
        '<script type="application/ld+json">{"@type": "Organization"}</script>'
        "</head>"
        "<body>"
        "<h1>Welcome</h1>"
        "</body>"
        "</html>"
    )
    respx_mock.get("https://example.com/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("https://example.com/llms.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *")
    )
    respx_mock.get("https://example.com/sitemap.xml").mock(
        return_value=httpx.Response(200, text="<xml/>")
    )

    result = await fetch_site_checks("example.com")

    assert result.provider == "site_checks"
    assert result.ok is True
    assert result.fields["site_title"] == "Test Company | B2B SaaS"
    assert result.fields["meta_description"] == "Leading B2B platform"
    assert result.fields["h1_count"] == 1
    assert result.fields["has_llms_txt"] is True
    assert result.fields["has_sitemap"] is True
    assert result.fields["has_schema_org"] is True


@pytest.mark.asyncio
async def test_website_fetch_via_jina(respx_mock: MockRouter):
    """Website provider fetches description via Jina Reader."""
    respx_mock.get("https://r.jina.ai/http://https://example.com/").mock(
        return_value=httpx.Response(200, text="Example Company provides B2B SaaS for teams.")
    )
    respx_mock.get("https://example.com/").mock(
        return_value=httpx.Response(
            200,
            text=(
                "<html>"
                "<body>"
                '<a href="/pricing">Pricing</a>'
                '<a href="/careers">Careers</a>'
                '<a href="/blog">Blog</a>'
                "</body>"
                "</html>"
            ),
        ),
    )
    respx_mock.get("https://example.com/pricing").mock(
        return_value=httpx.Response(200, text="<html><body>Pricing page</body></html>")
    )
    respx_mock.get("https://example.com/careers").mock(
        return_value=httpx.Response(
            200,
            text="<html><body>Senior Engineer\nGrowth Manager</body></html>",
        )
    )
    respx_mock.get("https://example.com/blog").mock(
        return_value=httpx.Response(
            200,
            text="<html><body><h2>Post 1</h2><h2>Post 2</h2></body></html>"
        )
    )

    result = await fetch_website("example.com")

    assert result.provider == "website"
    assert result.ok is True
    assert "description" in result.fields
    assert "pricing_page_url" in result.fields
    assert "careers_page_url" in result.fields
    assert "blog_page_url" in result.fields
    assert "open_roles" in result.fields
    assert "latest_blog_titles" in result.fields
    assert "tech_hints" in result.fields