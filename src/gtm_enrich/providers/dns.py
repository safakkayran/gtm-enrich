"""DNS provider for MX record lookup."""

from __future__ import annotations

import time
from typing import Any

import dns.resolver

from gtm_enrich.models import ProviderName, ProviderResult

EMAIL_PROVIDERS = {
    "google.com": "Google Workspace",
    "googlemail.com": "Google Workspace",
    "outlook.com": "Microsoft 365",
    "office365.com": "Microsoft 365",
    "microsoft.com": "Microsoft 365",
    "yahoo.com": "Yahoo",
    "zoho.com": "Zoho Mail",
    "protonmail.com": "Proton Mail",
    "fastmail.com": "Fastmail",
    "icloud.com": "iCloud",
    "amazon.com": "Amazon WorkMail",
    "awsapps.com": "Amazon WorkMail",
}


OK = 200


def _identify_provider(mx_host: str) -> str | None:
    mx_lower = mx_host.lower().rstrip(".")
    for key, name in EMAIL_PROVIDERS.items():
        if key in mx_lower:
            return name
    return None


async def fetch_dns(domain: str) -> ProviderResult:
    """Look up MX records and identify email provider."""
    start = time.perf_counter()
    fields: dict[str, Any] = {}

    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx_records = sorted(
            [(r.preference, str(r.exchange).rstrip(".")) for r in answers],
            key=lambda x: x[0],
        )
        fields["mx_records"] = [f"{pref} {host}" for pref, host in mx_records]

        if mx_records:
            provider = _identify_provider(mx_records[0][1])
            fields["email_provider"] = provider or "Other"

    except dns.resolver.NXDOMAIN:
        return ProviderResult(
            provider=ProviderName.DNS,
            fields={},
            ok=False,
            error="Domain does not exist",
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
    except dns.resolver.NoAnswer:
        return ProviderResult(
            provider=ProviderName.DNS,
            fields={},
            ok=False,
            error="No MX records found",
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
    except Exception as e:
        return ProviderResult(
            provider=ProviderName.DNS,
            fields={},
            ok=False,
            error=str(e),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    latency = int((time.perf_counter() - start) * 1000)
    return ProviderResult(
        provider=ProviderName.DNS,
        fields=fields,
        ok=True,
        error=None,
        latency_ms=latency,
    )