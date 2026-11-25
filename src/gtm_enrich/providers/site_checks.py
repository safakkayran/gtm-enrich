"""On-page site checks provider (SEO/technical audit)."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from gtm_enrich.models import ProviderName, ProviderResult
from gtm_enrich.providers.website import _fetch_direct

OK = 200


async def fetch_site_checks(domain: str) -> ProviderResult:
    """Run on-page SEO/technical checks."""
    start = time.perf_counter()
    base_url = f"https://{domain}"
    fields: dict[str, Any] = {}

    async with httpx.AsyncClient(
        headers={"User-Agent": "gtm-enrich/0.1"},
        follow_redirects=True,
    ) as client:
        html = await _fetch_direct(base_url, client)
        if not html:
            return ProviderResult(
                provider=ProviderName.SITE_CHECKS,
                fields={},
                ok=False,
                error="Failed to fetch homepage",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        tree = HTMLParser(html)

        # Title
        title_tag = tree.css_first("title")
        fields["site_title"] = title_tag.text().strip() if title_tag else None

        # Meta description
        meta_desc = tree.css_first('meta[name="description"]')
        fields["meta_description"] = (
            meta_desc.attributes.get("content", "").strip() if meta_desc else None
        )

        # H1 count
        h1_count = len(tree.css("h1"))
        fields["h1_count"] = h1_count

        # llms.txt
        llms_url = urljoin(base_url, "/llms.txt")
        resp = await client.get(llms_url, timeout=5.0)
        fields["has_llms_txt"] = resp.status_code == OK

        # Sitemap
        sitemap_url = urljoin(base_url, "/sitemap.xml")
        resp = await client.get(sitemap_url, timeout=5.0)
        fields["has_sitemap"] = resp.status_code == OK

        # Schema.org JSON-LD
        has_schema = False
        for script in tree.css('script[type="application/ld+json"]'):
            if script.text().strip():
                has_schema = True
                break
        fields["has_schema_org"] = has_schema

    latency = int((time.perf_counter() - start) * 1000)
    return ProviderResult(
        provider=ProviderName.SITE_CHECKS,
        fields=fields,
        ok=True,
        error=None,
        latency_ms=latency,
    )