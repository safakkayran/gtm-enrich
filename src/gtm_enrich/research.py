"""Research brief generation from enriched signals."""

from __future__ import annotations

from gtm_enrich.llm import complete_json
from gtm_enrich.models import Angle, Channel, EnrichedAccount, ProviderName, ResearchBrief, Signal


def extract_signals(account: EnrichedAccount) -> list[Signal]:
    """Extract actionable signals from enriched account."""
    signals = []
    signal_id = 0

    def add_signal(text: str, source: str) -> None:
        nonlocal signal_id
        signals.append(Signal(id=f"s{signal_id}", text=text, source=ProviderName(source)))
        signal_id += 1

    _add_website_signals(account, add_signal)
    _add_site_checks_signals(account, add_signal)
    _add_dns_signals(account, add_signal)
    _add_github_signals(account, add_signal)
    _add_rss_signals(account, add_signal)

    return signals


def _add_website_signals(account: EnrichedAccount, add_signal) -> None:
    if account.description:
        add_signal(f"Company description: {account.description.value}", "website")
    if account.pricing_page_url:
        add_signal("Has public pricing page", "website")
        if account.pricing_page_text:
            add_signal(f"Pricing details: {account.pricing_page_text.value[:200]}", "website")
    if account.careers_page_url:
        add_signal("Has careers page", "website")
    if account.open_roles and account.open_roles.value:
        add_signal(f"Open roles: {', '.join(account.open_roles.value[:5])}", "website")
    if account.tech_hints and account.tech_hints.value:
        add_signal(f"Tech stack: {', '.join(account.tech_hints.value)}", "website")
    if account.latest_blog_titles and account.latest_blog_titles.value:
        titles = account.latest_blog_titles.value[:3]
        add_signal(f"Recent blog posts: {', '.join(titles)}", "website")


def _add_site_checks_signals(account: EnrichedAccount, add_signal) -> None:
    if account.site_title:
        add_signal(f"Site title: {account.site_title.value}", "site_checks")
    if account.has_schema_org and account.has_schema_org.value:
        add_signal("Implements Schema.org structured data", "site_checks")
    if account.has_llms_txt and account.has_llms_txt.value:
        add_signal("Has llms.txt for AI crawlers", "site_checks")


def _add_dns_signals(account: EnrichedAccount, add_signal) -> None:
    if account.email_provider and account.email_provider.value:
        add_signal(f"Email provider: {account.email_provider.value}", "dns")


def _add_github_signals(account: EnrichedAccount, add_signal) -> None:
    if account.github_org and account.github_org.value:
        add_signal(f"GitHub org: {account.github_org.value}", "github")
    if account.github_stars and account.github_stars.value:
        add_signal(f"GitHub stars: {account.github_stars.value}", "github")
    if account.github_top_repos and account.github_top_repos.value:
        repos = account.github_top_repos.value[:3]
        names = [r.get("name", "") for r in repos]
        add_signal(f"Top repos: {', '.join(names)}", "github")


def _add_rss_signals(account: EnrichedAccount, add_signal) -> None:
    if account.rss_feed_title and account.rss_feed_title.value:
        add_signal(f"Active blog: {account.rss_feed_title.value}", "rss")
    if account.rss_latest_items and account.rss_latest_items.value:
        items = account.rss_latest_items.value[:3]
        titles = [i.get("title", "") for i in items]
        add_signal(f"Recent posts: {', '.join(titles)}", "rss")


RESEARCH_PROMPT = (
    "You are a GTM research analyst. Given a company's enrichment signals, "
    "produce a concise research brief and 3 outbound angles.\n\n"
    "Company: {domain}\n"
    "ICP: {icp_description}\n\n"
    "Signals:\n"
    "{signals}\n\n"
    "Output JSON with:\n"
    "- summary: 3-4 sentence company summary\n"
    "- icp_fit_score: 1-5 (5 = perfect ICP match)\n"
    "- fit_reason: 1 sentence why this score\n"
    "- angles: array of 3 objects, each with:\n"
    "  - text: the outbound angle (1-2 sentences, specific, uses signal)\n"
    '  - signal_ids: array of signal IDs cited (e.g. ["s0", "s2"])\n'
    '  - channel: "email" or "linkedin"\n\n'
    "Angles must:\n"
    "- Be specific to THIS company (use their signals)\n"
    "- Reference signal IDs in brackets\n"
    "- Be actionable for outbound\n"
    "- Vary by channel (1-2 email, 1-2 LinkedIn)"
)


def generate_research_brief(
    account: EnrichedAccount,
    icp_description: str,
) -> ResearchBrief:
    """Generate research brief and angles using LLM."""
    signals = extract_signals(account)

    if not signals:
        return ResearchBrief(
            summary="No enrichment signals available.",
            icp_fit_score=1,
            fit_reason="Insufficient data to assess ICP fit.",
            angles=[],
        )

    signals_text = "\n".join(f"- [{s.id}] {s.text} (source: {s.source.value})" for s in signals)

    prompt = RESEARCH_PROMPT.format(
        domain=account.domain,
        icp_description=icp_description,
        signals=signals_text,
    )

    try:
        return complete_json(
            schema=ResearchBrief,
            system="You are a GTM research analyst. Output valid JSON only.",
            user=prompt,
            model="nim-laguna",
        )
    except Exception:
        # Fallback: create basic brief from signals
        return _fallback_brief(account, signals, icp_description)


def _fallback_brief(
    account: EnrichedAccount,
    signals: list[Signal],
    icp_description: str,
) -> ResearchBrief:
    """Generate basic brief without LLM."""
    summary_parts = []
    if account.description:
        summary_parts.append(account.description.value[:150])
    if account.tech_hints and account.tech_hints.value:
        summary_parts.append(f"Tech: {', '.join(account.tech_hints.value[:3])}")
    if account.open_roles and account.open_roles.value:
        summary_parts.append(f"Hiring: {', '.join(account.open_roles.value[:3])}")

    summary = " ".join(summary_parts) or f"{account.domain} - enriched with {len(signals)} signals."

    # Simple scoring
    score = min(account.icp_score // 10 + 1, 5)

    angles = []
    for i, sig in enumerate(signals[:3]):
        channel = Channel.EMAIL if i % 2 == 0 else Channel.LINKEDIN
        first_word = icp_description.split(maxsplit=1)[0]
        angles.append(
            Angle(
                text=f"Saw {sig.text.lower()} - relevant for {first_word} outreach",
                signal_ids=[sig.id],
                channel=channel,
            )
        )

    return ResearchBrief(
        summary=summary,
        icp_fit_score=score,
        fit_reason=f"ICP score {account.icp_score} from {len(signals)} signals",
        angles=angles,
    )


def research_accounts(
    accounts: list[EnrichedAccount],
    icp_description: str,
) -> dict[str, ResearchBrief]:
    """Generate research briefs for multiple accounts."""
    briefs = {}
    for account in accounts:
        briefs[account.domain] = generate_research_brief(account, icp_description)
    return briefs