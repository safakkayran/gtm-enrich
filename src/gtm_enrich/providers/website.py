"""Website provider using Jina Reader with httpx fallback."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from gtm_enrich.models import ProviderName, ProviderResult

JINA_BASE = "https://r.jina.ai/http://"
OK = 200
MIN_ROLE_LEN = 5
MAX_ROLE_LEN = 100
MIN_TITLE_LEN = 10
MAX_TITLE_LEN = 200
MAX_ROLES = 20
MAX_TITLES = 10


async def _fetch_jina(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch via Jina Reader."""
    try:
        resp = await client.get(JINA_BASE + url, timeout=15.0, follow_redirects=True)
        if resp.status_code == OK and resp.text.strip():
            return resp.text
    except Exception:
        pass
    return None


async def _fetch_direct(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch directly with httpx and parse with selectolax."""
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == OK:
            return resp.text
    except Exception:
        pass
    return None


def _extract_text(html: str) -> str:
    """Extract clean text from HTML."""
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript"):
        tag.decompose()
    text = tree.body.text() if tree.body else ""
    return re.sub(r"\s+", " ", text).strip()


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract all href links from HTML."""
    tree = HTMLParser(html)
    links = []
    for a in tree.css("a[href]"):
        href = a.attributes.get("href", "")
        if href:
            links.append(urljoin(base_url, href))
    return links


def _find_pricing_link(links: list[str]) -> str | None:
    for link in links:
        lower = link.lower()
        if any(kw in lower for kw in ["/pricing", "/plans", "/price"]):
            return link
    return None


def _find_careers_link(links: list[str]) -> str | None:
    for link in links:
        lower = link.lower()
        if any(kw in lower for kw in ["/careers", "/jobs", "/join", "/hiring"]):
            return link
    return None


def _find_blog_link(links: list[str]) -> str | None:
    for link in links:
        lower = link.lower()
        if any(kw in lower for kw in ["/blog", "/news", "/changelog", "/updates"]):
            return link
    return None


def _extract_tech_hints(html: str) -> list[str]:
    """Extract technology hints from script src domains."""
    tree = HTMLParser(html)
    hints = set()
    known = {
        "hubspot": "HubSpot",
        "segment": "Segment",
        "intercom": "Intercom",
        "stripe": "Stripe",
        "clay": "Clay",
        "attio": "Attio",
        "salesforce": "Salesforce",
        "marketo": "Marketo",
        "pardot": "Pardot",
        "ga4": "Google Analytics",
        "gtm": "Google Tag Manager",
        "hotjar": "Hotjar",
        "fullstory": "FullStory",
        "amplitude": "Amplitude",
        "mixpanel": "Mixpanel",
        "posthog": "PostHog",
    }
    for script in tree.css("script[src]"):
        src = script.attributes.get("src", "").lower()
        for key, name in known.items():
            if key in src:
                hints.add(name)
    return sorted(hints)


def _extract_open_roles(html: str) -> list[str]:
    """Extract job titles from careers page."""
    tree = HTMLParser(html)
    roles = []
    text = tree.body.text() if tree.body else ""
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if (
            any(
                kw in line.lower()
                for kw in [
                    "engineer",
                    "manager",
                    "director",
                    "lead",
                    "head",
                    "growth",
                    "revops",
                    "marketing ops",
                    "sales",
                ]
            )
            and MIN_ROLE_LEN < len(line) < MAX_ROLE_LEN
        ):
            roles.append(line)
    return roles[:MAX_ROLES]


async def _fetch_description(base_url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch and extract description from homepage."""
    jina_text = await _fetch_jina(base_url, client)
    if jina_text:
        return jina_text[:2000]
    html = await _fetch_direct(base_url, client)
    if html:
        return _extract_text(html)[:2000]
    return None


async def _process_pricing(links: list[str], client: httpx.AsyncClient) -> dict[str, Any]:
    pricing = _find_pricing_link(links)
    if not pricing:
        return {}
    p_html = await _fetch_direct(pricing, client)
    if p_html:
        return {"pricing_page_url": pricing, "pricing_page_text": _extract_text(p_html)[:1500]}
    return {"pricing_page_url": pricing}


async def _process_careers(links: list[str], client: httpx.AsyncClient) -> dict[str, Any]:
    careers = _find_careers_link(links)
    if not careers:
        return {}
    c_html = await _fetch_direct(careers, client)
    if c_html:
        return {
            "careers_page_url": careers,
            "careers_page_text": _extract_text(c_html)[:1500],
            "open_roles": _extract_open_roles(c_html),
        }
    return {"careers_page_url": careers}


async def _process_blog(links: list[str], client: httpx.AsyncClient) -> dict[str, Any]:
    blog = _find_blog_link(links)
    if not blog:
        return {}
    b_html = await _fetch_direct(blog, client)
    if b_html:
        tree = HTMLParser(b_html)
        titles = []
        for h in tree.css("h1, h2, h3, article h2"):
            t = h.text().strip()
            if MIN_TITLE_LEN < len(t) < MAX_TITLE_LEN:
                titles.append(t)
        return {"blog_page_url": blog, "latest_blog_titles": titles[:MAX_TITLES]}
    return {"blog_page_url": blog}


async def fetch_website(domain: str) -> ProviderResult:
    """Fetch website and extract structured data."""
    start = time.perf_counter()
    base_url = f"https://{domain}"
    fields: dict[str, Any] = {}

    async with httpx.AsyncClient(
        headers={"User-Agent": "gtm-enrich/0.1"},
        follow_redirects=True,
    ) as client:
        description = await _fetch_description(base_url, client)
        if not description:
            return ProviderResult(
                provider=ProviderName.WEBSITE,
                fields={},
                ok=False,
                error="Failed to fetch homepage",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        fields["description"] = description

        html = await _fetch_direct(base_url, client)
        if not html:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderResult(
                provider=ProviderName.WEBSITE,
                fields=fields,
                ok=True,
                error=None,
                latency_ms=latency,
            )

        links = _extract_links(html, base_url)

        fields.update(await _process_pricing(links, client))
        fields.update(await _process_careers(links, client))
        fields.update(await _process_blog(links, client))
        fields["tech_hints"] = _extract_tech_hints(html)

    latency = int((time.perf_counter() - start) * 1000)
    return ProviderResult(
        provider=ProviderName.WEBSITE,
        fields=fields,
        ok=True,
        error=None,
        latency_ms=latency,
    )