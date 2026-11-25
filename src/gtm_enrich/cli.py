"""CLI commands for gtm-enrich."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from gtm_enrich import __version__
from gtm_enrich.config import get_default_icp_config, get_default_waterfall_config, get_settings
from gtm_enrich.models import ProviderName
from gtm_enrich.report import write_run_result
from gtm_enrich.twenty_push import push_results_to_twenty
from gtm_enrich.waterfall import run_enrichment

app = typer.Typer(
    name="gtm-enrich",
    help="Waterfall enrichment and account research CLI for GTM teams",
    add_completion=False,
)
console = Console()

DOMAINS_HELP = "Comma-separated domains or path to file with one domain per line"
OUTPUT_HELP = "Output directory"
FORMAT_HELP = "Output format: json, csv, both"
PROVIDERS_HELP = "Comma-separated provider order"
ICP_HELP = "ICP description"


def _parse_domains(domains: str) -> list[str]:
    """Parse comma-separated domains or read from file."""
    path = Path(domains)
    if path.exists():
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return [d.strip() for d in domains.split(",") if d.strip()]


def _parse_provider_order(order: str) -> list[ProviderName]:
    """Parse comma-separated provider names."""
    provider_map = {p.value: p for p in ProviderName}
    return [provider_map[p.strip()] for p in order.split(",") if p.strip() in provider_map]


@app.command()
def run(
    domains: Annotated[str, typer.Argument(help=DOMAINS_HELP)],
    output: Annotated[str, typer.Option("-o", "--output", help=OUTPUT_HELP)] = "out",
    format: Annotated[str, typer.Option("-f", "--format", help=FORMAT_HELP)] = "json",
    providers: Annotated[str, typer.Option("--providers", help=PROVIDERS_HELP)] = (
        "website,site_checks,dns,github,rss"
    ),
    icp_desc: Annotated[str, typer.Option("--icp", help=ICP_HELP)] = (
        "B2B SaaS with sales team + active hiring"
    ),
):
    """Run waterfall enrichment on domains."""
    get_settings()  # validate settings
    domain_list = _parse_domains(domains)
    provider_order = _parse_provider_order(providers)

    console.print(f"[bold]Enriching {len(domain_list)} domain(s)...[/bold]")
    console.print(f"Providers: {', '.join(p.value for p in provider_order)}")

    waterfall_config = get_default_waterfall_config()
    waterfall_config.provider_order = provider_order

    icp_config = get_default_icp_config()
    icp_config.description = icp_desc

    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running enrichment...", total=len(domain_list))
            result = await run_enrichment(domain_list, waterfall_config, icp_config)
            progress.update(task, completed=len(domain_list))

        output_dir = Path(output)
        write_run_result(result, output_dir, format)

        console.print(
            f"[green]✓[/green] Enriched {result.successful}/{result.total_domains} domains"
        )
        console.print(f"[green]✓[/green] Results written to {output_dir}")

        for account in result.accounts:
            score = account.icp_score
            reasons = ", ".join(account.icp_reasons) if account.icp_reasons else "No signals"
            console.print(f"  {account.domain}: ICP score {score} ({reasons})")

    asyncio.run(_run())


@app.command()
def version():
    """Show version."""
    console.print(f"gtm-enrich {__version__}")


@app.command()
def push(
    results: Annotated[str, typer.Argument(help="Path to enrichment results JSON")],
    briefs: Annotated[
        str | None,
        typer.Option("--briefs", "-b", help="Path to research briefs JSON"),
    ] = None,
):
    """Push enrichment results to Twenty CRM."""
    get_settings()  # validate settings

    results_path = Path(results)
    briefs_path = Path(briefs) if briefs else None

    if not results_path.exists():
        console.print(f"[red]Results file not found: {results_path}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Pushing to Twenty CRM from {results_path}...[/bold]")

    async def _push():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Pushing accounts...", total=None)
            push_results = await push_results_to_twenty(results_path, briefs_path)
            progress.update(task, description=f"Completed {len(push_results)} accounts")

        success_count = sum(1 for r in push_results if r.success)
        fail_count = len(push_results) - success_count

        console.print(f"[green]✓[/green] Pushed {success_count}/{len(push_results)} accounts")
        if fail_count:
            console.print(f"[red]✗[/red] Failed: {fail_count}")
            for r in push_results:
                if not r.success:
                    console.print(f"  {r.error}")

    asyncio.run(_push())


if __name__ == "__main__":
    app()