"""Report generation (JSON/CSV)."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from gtm_enrich.models import EnrichedAccount, ProviderResult, RunResult, WaterfallField


def _extract_value(obj: Any) -> Any:
    """Extract value from WaterfallField or return as-is."""
    if isinstance(obj, WaterfallField):
        return obj.value
    return obj


def _flatten_account(account: EnrichedAccount) -> dict[str, Any]:
    """Flatten account for CSV export."""
    data = account.model_dump()
    # Extract values from WaterfallField objects
    for key, value in data.items():
        data[key] = _extract_value(value)
    # Flatten nested structures for CSV
    if data.get("github_top_repos"):
        data["github_top_repos"] = json.dumps(data["github_top_repos"])
    if data.get("rss_latest_items"):
        data["rss_latest_items"] = json.dumps(data["rss_latest_items"])
    if data.get("tech_hints") and isinstance(data["tech_hints"], list):
        data["tech_hints"] = "; ".join(data["tech_hints"])
    if data.get("open_roles") and isinstance(data["open_roles"], list):
        data["open_roles"] = "; ".join(data["open_roles"])
    if data.get("latest_blog_titles") and isinstance(data["latest_blog_titles"], list):
        data["latest_blog_titles"] = "; ".join(data["latest_blog_titles"])
    if data.get("mx_records") and isinstance(data["mx_records"], list):
        data["mx_records"] = "; ".join(data["mx_records"])
    if data.get("icp_reasons") and isinstance(data["icp_reasons"], list):
        data["icp_reasons"] = "; ".join(data["icp_reasons"])
    return data


def write_json(accounts: list[EnrichedAccount], path: Path) -> None:
    """Write accounts as JSON Lines."""
    with path.open("w") as f:
        for account in accounts:
            f.write(account.model_dump_json() + "\n")


def write_csv(accounts: list[EnrichedAccount], path: Path) -> None:
    """Write accounts as CSV."""
    if not accounts:
        return

    flattened = [_flatten_account(a) for a in accounts]
    fieldnames = list(flattened[0].keys())

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened)


def write_run_result(result: RunResult, output_dir: Path, format: str = "json") -> None:
    """Write run result to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if format == "json":
        write_json(result.accounts, output_dir / "accounts.jsonl")
    elif format == "csv":
        write_csv(result.accounts, output_dir / "accounts.csv")
    elif format == "both":
        write_json(result.accounts, output_dir / "accounts.jsonl")
        write_csv(result.accounts, output_dir / "accounts.csv")

    # Write summary
    summary = {
        "total_domains": result.total_domains,
        "successful": result.successful,
        "total_latency_ms": result.total_latency_ms,
        "provider_stats": _provider_stats(result.provider_results),
    }
    with (output_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)


def _provider_stats(results: list[ProviderResult]) -> dict[str, dict[str, Any]]:
    """Aggregate provider statistics."""
    stats: dict[str, dict[str, Any]] = {}
    for r in results:
        key = r.provider.value
        if key not in stats:
            stats[key] = {"calls": 0, "success": 0, "total_latency_ms": 0, "errors": []}
        stats[key]["calls"] += 1
        if r.ok:
            stats[key]["success"] += 1
        stats[key]["total_latency_ms"] += r.latency_ms
        if r.error:
            stats[key]["errors"].append(r.error)
    return stats