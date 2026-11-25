"""GitHub provider for org/repo signals."""

from __future__ import annotations

import time
from typing import Any

import httpx

from gtm_enrich.models import ProviderName, ProviderResult

GITHUB_API = "https://api.github.com"
OK = 200
RATE_LIMITED = 403


async def _github_get(client: httpx.AsyncClient, path: str) -> dict | list | None:
    url = f"{GITHUB_API}{path}"
    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == OK:
            return resp.json()
        if resp.status_code == RATE_LIMITED:
            # Rate limited
            return None
    except Exception:
        pass
    return None


async def fetch_github(domain: str) -> ProviderResult:
    """Fetch GitHub signals for a domain."""
    start = time.perf_counter()
    fields: dict[str, Any] = {}

    # Try to find org from domain - common patterns
    org_guess = domain.split(".", maxsplit=1)[0]

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "gtm-enrich/0.1",
            "Accept": "application/vnd.github+json",
        },
        follow_redirects=True,
    ) as client:
        # Search for org
        org_data = await _github_get(client, f"/orgs/{org_guess}")
        if not org_data:
            # Try searching repos
            search = await _github_get(
                client,
                f"/search/repositories?q={domain}+in:description,readme&sort=stars&per_page=5",
            )
            if search and search.get("items"):
                repo = search["items"][0]
                fields["github_repo"] = repo["full_name"]
                fields["github_stars"] = repo["stargazers_count"]
                fields["github_forks"] = repo["forks_count"]
                fields["github_description"] = repo.get("description")
                fields["github_language"] = repo.get("language")
                fields["github_updated_at"] = repo.get("updated_at")
                license_obj = repo.get("license")
                fields["github_license"] = license_obj.get("name") if license_obj else None
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderResult(
                provider=ProviderName.GITHUB,
                fields=fields,
                ok=bool(fields),
                error="No GitHub org/repo found" if not fields else None,
                latency_ms=latency,
            )

        # Found org
        fields["github_org"] = org_data.get("login")
        fields["github_org_name"] = org_data.get("name")
        fields["github_org_description"] = org_data.get("description")
        fields["github_org_public_repos"] = org_data.get("public_repos")
        fields["github_org_followers"] = org_data.get("followers")
        fields["github_org_created_at"] = org_data.get("created_at")
        fields["github_org_location"] = org_data.get("location")
        fields["github_org_blog"] = org_data.get("blog")

        # Get org repos (top 5 by stars)
        repos = await _github_get(client, f"/orgs/{org_guess}/repos?sort=stars&per_page=5")
        if repos:
            fields["github_top_repos"] = [
                {
                    "name": r["name"],
                    "stars": r["stargazers_count"],
                    "forks": r["forks_count"],
                    "language": r.get("language"),
                    "description": r.get("description"),
                }
                for r in repos[:5]
            ]

    latency = int((time.perf_counter() - start) * 1000)
    return ProviderResult(
        provider=ProviderName.GITHUB,
        fields=fields,
        ok=True,
        error=None,
        latency_ms=latency,
    )