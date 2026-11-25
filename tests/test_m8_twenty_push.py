"""M8 Twenty push tests."""

from __future__ import annotations

import json

import pytest

from gtm_enrich.models import EnrichedAccount, ProviderName, ResearchBrief, WaterfallField
from gtm_enrich.twenty_push import PushResult, TwentyClient

EXPECTED_FIT_SCORE = 4


def _make_account(domain: str, **fields) -> EnrichedAccount:
    """Helper to create EnrichedAccount with WaterfallField values."""
    wrapped = {}
    for k, v in fields.items():
        wrapped[k] = WaterfallField(
            value=v, provider=ProviderName.WEBSITE, latency_ms=10, cost_usd=0.0
        )
    return EnrichedAccount(domain=domain, **wrapped)


@pytest.mark.asyncio
async def test_twenty_client_init():
    """Test TwentyClient initialization."""
    client = TwentyClient(base_url="http://localhost:3000", api_key="test-key", rest_prefix="/rest")

    assert client.base_url == "http://localhost:3000"
    assert client.api_key == "test-key"
    assert client.rest_prefix == "/rest"


@pytest.mark.asyncio
async def test_twenty_client_headers():
    """Test auth headers."""
    client = TwentyClient(base_url="http://localhost:3000", api_key="test-key", rest_prefix="/rest")

    headers = client.headers
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_twenty_client_no_key_raises():
    """Test that missing API key raises."""
    client = TwentyClient(base_url="http://localhost:3000", api_key=None, rest_prefix="/rest")

    with pytest.raises(ValueError, match="TWENTY_API_KEY not configured"):
        _ = client.headers


@pytest.mark.asyncio
async def test_build_account_payload():
    """Test building Twenty account payload."""
    client = TwentyClient(base_url="http://localhost:3000", api_key="test-key", rest_prefix="/rest")

    account = _make_account(
        "example.com",
        description="B2B SaaS platform",
        tech_hints=["HubSpot", "Stripe"],
        open_roles=["Senior Engineer"],
    )
    account.company_name = "Example Inc"
    brief = ResearchBrief(
        summary="Test company",
        icp_fit_score=EXPECTED_FIT_SCORE,
        fit_reason="Good fit",
        angles=[],
    )

    payload = client.build_account_payload(account, brief)

    assert payload["name"] == "Example Inc"
    assert payload["domain"] == "example.com"
    assert payload["description"] == "B2B SaaS platform"
    assert "HubSpot, Stripe" in payload["techStack"]
    assert "Senior Engineer" in payload["openRoles"]
    assert "enrichedData" in payload
    enriched = json.loads(payload["enrichedData"])
    assert enriched["icp_fit_score"] == EXPECTED_FIT_SCORE


@pytest.mark.asyncio
async def test_push_result_dataclass():
    """Test PushResult dataclass."""
    result = PushResult(success=True, account_id="acc_123", details={"action": "created"})
    assert result.success is True
    assert result.account_id == "acc_123"

    result_fail = PushResult(success=False, error="API error")
    assert result_fail.success is False
    assert result_fail.error == "API error"


@pytest.mark.asyncio
async def test_twenty_client_close():
    """Test client close."""
    client = TwentyClient(base_url="http://localhost:3000", api_key="test-key", rest_prefix="/rest")

    # Access client to create it
    _ = client.client
    await client.close()
    # Should not raise