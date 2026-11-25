"""Twenty CRM push integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from gtm_enrich.config import get_settings
from gtm_enrich.models import EnrichedAccount, ResearchBrief

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class PushResult:
    """Result of pushing to Twenty CRM."""

    success: bool
    account_id: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


HTTP_NOT_FOUND = 404


class TwentyClient:
    """Client for Twenty CRM REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        rest_prefix: str | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.TWENTY_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.TWENTY_API_KEY
        self.rest_prefix = rest_prefix or settings.TWENTY_REST_PREFIX
        self._client: httpx.AsyncClient | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Auth headers."""
        if not self.api_key:
            raise ValueError("TWENTY_API_KEY not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.base_url}{self.rest_prefix}",
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def find_account_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Find existing account by domain."""
        try:
            resp = await self.client.get(
                "/accounts",
                params={"filter": json.dumps({"domain": {"equals": domain}}), "limit": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            accounts = data.get("data", [])
            return accounts[0] if accounts else None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTP_NOT_FOUND:
                return None
            raise

    async def create_account(
        self, account: EnrichedAccount, brief: ResearchBrief | None = None
    ) -> dict[str, Any]:
        """Create a new account in Twenty."""
        payload = self.build_account_payload(account, brief)
        resp = await self.client.post("/accounts", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def update_account(
        self, account_id: str, account: EnrichedAccount, brief: ResearchBrief | None = None
    ) -> dict[str, Any]:
        """Update existing account in Twenty."""
        payload = self.build_account_payload(account, brief)
        resp = await self.client.patch(f"/accounts/{account_id}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def build_account_payload(
        self, account: EnrichedAccount, brief: ResearchBrief | None = None
    ) -> dict[str, Any]:
        """Build Twenty account payload from enriched account."""
        payload: dict[str, Any] = {
            "name": account.domain,
            "domain": account.domain,
        }

        # Add enrichment data
        if account.description and account.description.value:
            payload["description"] = account.description.value

        if account.company_name:
            payload["name"] = account.company_name

        if account.tech_hints and account.tech_hints.value:
            payload["techStack"] = ", ".join(account.tech_hints.value)

        if account.open_roles and account.open_roles.value:
            payload["openRoles"] = ", ".join(account.open_roles.value)

        # Custom fields for GTM enrichment
        tech_hints_val = account.tech_hints.value if account.tech_hints else []
        payload["enrichedData"] = json.dumps({
            "icp_fit_score": brief.icp_fit_score if brief else None,
            "fit_reason": brief.fit_reason if brief else None,
            "angles": [
                {"text": a.text, "channel": a.channel.value, "signals": a.signal_ids}
                for a in (brief.angles if brief else [])
            ],
            "signals_summary": tech_hints_val[:5],
        })

        return payload

    async def push_account(
        self, account: EnrichedAccount, brief: ResearchBrief | None = None
    ) -> PushResult:
        """Push account to Twenty (upsert by domain)."""
        try:
            existing = await self.find_account_by_domain(account.domain)

            if existing:
                result = await self.update_account(existing["id"], account, brief)
                return PushResult(
                    success=True, account_id=result["id"], details={"action": "updated"}
                )

            result = await self.create_account(account, brief)
            return PushResult(success=True, account_id=result["id"], details={"action": "created"})

        except Exception as e:
            return PushResult(success=False, error=str(e))


async def push_to_twenty(
    accounts: list[EnrichedAccount],
    briefs: dict[str, ResearchBrief] | None = None,
) -> list[PushResult]:
    """Push multiple accounts to Twenty CRM."""
    briefs = briefs or {}
    client = TwentyClient()
    results = []

    try:
        for account in accounts:
            brief = briefs.get(account.domain)
            result = await client.push_account(account, brief)
            results.append(result)
    finally:
        await client.close()

    return results


async def push_results_to_twenty(
    results_file: Path,
    briefs_file: Path | None = None,
) -> list[PushResult]:
    """Push enrichment results from JSON files to Twenty."""
    with results_file.open() as f:
        data = json.load(f)

    accounts = [EnrichedAccount(**acc) for acc in data.get("accounts", [])]

    briefs: dict[str, ResearchBrief] = {}
    if briefs_file and briefs_file.exists():
        with briefs_file.open() as f:
            briefs_data = json.load(f)
        briefs = {domain: ResearchBrief(**br) for domain, br in briefs_data.items()}

    return await push_to_twenty(accounts, briefs)