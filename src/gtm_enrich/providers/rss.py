"""RSS/Atom feed provider for blog/changelog signals."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import feedparser
import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from gtm_enrich.models import ProviderName, ProviderResult

COMMON_FEED_PATHS = [
    "/feed.xml",
    "/rss.xml",
    "/atom.xml",
    "/feed",
    "/rss",
    "/blog/rss.xml",
    "/blog/feed.xml",
    "/blog/feed",
    "/changelog.xml",
    "/changelog/feed.xml",
    "/news/rss.xml",
    "/news/feed.xml",
]


OK = 200
MAX_ENTRIES = 20


async def _discover_feed(base_url: str, client: httpx.AsyncClient) -> str | None:
    """Try common feed paths and check link rel=alternate."""
    for path in COMMON_FEED_PATHS:
        url = urljoin(base_url, path)
        try:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == OK and resp.text.strip():
                parsed = feedparser.parse(resp.text)
                if parsed.entries:
                    return url
        except Exception:
            pass

    # Try homepage for link rel=alternate
    try:
        resp = await client.get(base_url, timeout=5.0)
        if resp.status_code == OK:
            tree = HTMLParser(resp.text)
            selector = 'link[rel="alternate"][type*="rss"], link[rel="alternate"][type*="atom"]'
            for link in tree.css(selector):
                href = link.attributes.get("href")
                if href:
                    return urljoin(base_url, href)
    except Exception:
        pass

    return None


async def fetch_rss(domain: str) -> ProviderResult:
    """Fetch and parse RSS/Atom feed for a domain."""
    start = time.perf_counter()
    base_url = f"https://{domain}"
    fields: dict[str, Any] = {}

    async with httpx.AsyncClient(
        headers={"User-Agent": "gtm-enrich/0.1"},
        follow_redirects=True,
    ) as client:
        feed_url = await _discover_feed(base_url, client)
        if not feed_url:
            return ProviderResult(
                provider=ProviderName.RSS,
                fields={},
                ok=False,
                error="No RSS/Atom feed found",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        fields["feed_url"] = feed_url

        try:
            resp = await client.get(feed_url, timeout=10.0)
            if resp.status_code != OK:
                return ProviderResult(
                    provider=ProviderName.RSS,
                    fields={},
                    ok=False,
                    error=f"Feed fetch failed: {resp.status_code}",
                    latency_ms=int((time.perf_counter() - start) * 1000),
                )

            parsed = feedparser.parse(resp.text)

            fields["feed_title"] = parsed.feed.get("title")
            fields["feed_description"] = parsed.feed.get("description")
            fields["feed_updated"] = parsed.feed.get("updated")

            entries = []
            for entry in parsed.entries[:MAX_ENTRIES]:
                tags = entry.get("tags", [])
                tag_terms = [t.get("term") for t in tags] if tags else []
                entries.append(
                    {
                        "title": entry.get("title"),
                        "link": entry.get("link"),
                        "published": entry.get("published") or entry.get("updated"),
                        "summary": entry.get("summary") or entry.get("description"),
                        "tags": tag_terms,
                    }
                )
            fields["recent_posts"] = entries
            fields["post_count"] = len(entries)

        except Exception as e:
            return ProviderResult(
                provider=ProviderName.RSS,
                fields={},
                ok=False,
                error=str(e),
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

    latency = int((time.perf_counter() - start) * 1000)
    return ProviderResult(
        provider=ProviderName.RSS,
        fields=fields,
        ok=True,
        error=None,
        latency_ms=latency,
    )