# gtm-enrich

Waterfall enrichment pipeline for B2B accounts: multi-provider enrichment, signal-based research, LLM eval harness, optional Twenty CRM push.

## Features

- **Waterfall Enrichment**: Website, Site Checks, DNS, GitHub, RSS providers tried in priority order
- **Signal Extraction**: Automatic signals from enrichment data (hiring, tech stack, pricing, blog, etc.)
- **Research Briefs**: LLM-generated summaries with ICP fit scores and 3 outbound angles per account
- **Eval Harness**: Dataset-driven evaluation (CSV/JSONL) with judge model scoring 6 quality rules
- **Twenty CRM Push**: Upsert accounts by domain with enriched data and angles
- **CLI**: Simple commands for run, push, and version

## Installation

```bash
uv sync --dev
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```bash
# LiteLLM (free NVIDIA NIM tiers)
LLM_MODEL=nim-laguna
LLM_JUDGE_MODEL=nim-step
LITELLM_BASE_URL=http://127.0.0.1:4000

# GitHub (optional, for higher rate limits)
GITHUB_TOKEN=

# Twenty CRM
TWENTY_BASE_URL=http://localhost:3000
TWENTY_API_KEY=your_api_key
TWENTY_REST_PREFIX=/rest
```

## Usage

### Run enrichment

```bash
# Single domain
gtm-enrich run example.com

# Multiple domains
gtm-enrich run "example.com,test.com,acme.com"

# From file (one domain per line)
gtm-enrich run domains.txt

# Custom output format
gtm-enrich run example.com --format both --output ./results

# Custom provider order
gtm-enrich run example.com --providers "website,dns,github"

# Custom ICP description
gtm-enrich run example.com --icp "B2B SaaS with 50+ employees"
```

Outputs:
- `out/accounts.json` — full enriched accounts with provenance
- `out/briefs.json` — research briefs per domain
- `out/accounts.csv` — flattened CSV (if `--format csv` or `both`)

### Push to Twenty CRM

```bash
# Push enrichment results
gtm-enrich push out/accounts.json

# Push with research briefs
gtm-enrich push out/accounts.json --briefs out/briefs.json
```

### Run evaluations

```bash
# Create dataset (CSV or JSONL)
# CSV columns: company,angle,channel,expected_pass
# JSONL: {"company": "...", "angle": "...", "channel": "email", "expected_pass": "true"}

# Run evals
gtm-enrich eval evals/dataset.csv --output evals/results.json
```

## Providers

| Provider | Data | Auth |
|----------|------|------|
| Website | Description, pricing page, careers, blog, tech hints | Jina Reader (free) + httpx fallback |
| Site Checks | Title, meta, H1, schema.org, sitemap, llms.txt | None |
| DNS | MX records, email provider (Google/Microsoft/other) | None |
| GitHub | Org, stars, public repos, top repos, languages | Optional GITHUB_TOKEN |
| RSS | Feed URL, title, latest items | None |

## Waterfall Logic

1. Providers tried in order: `website → site_checks → dns → github → rss`
2. First non-null value wins for each field
3. Provenance tracked: provider, latency, cost
4. Research step runs after all providers complete

## Research Brief

Per account, generates:
- **Summary**: 2-3 sentence company overview
- **ICP Fit Score**: 1-5 with reasoning
- **3 Outbound Angles**: Email/LinkedIn with signal citations `[s0]`, `[s1]`

## Eval Rules (6 checks)

1. `specific_to_company` — References specific details
2. `cites_signals` — Explicitly cites signal IDs
3. `actionable` — Clear next step / CTA
4. `appropriate_tone` — Professional, not spammy
5. `channel_fit` — Suits email vs LinkedIn
6. `no_hallucination` — No invented facts

## Project Structure

```
src/gtm_enrich/
├── cli.py          # CLI commands (run, push, version)
├── config.py       # Settings, default configs
├── models.py       # Pydantic models
├── llm.py          # Cached LLM client (disk cache, retry)
├── providers/
│   ├── __init__.py
│   ├── website.py
│   ├── site_checks.py
│   ├── dns.py
│   ├── github.py
│   └── rss.py
├── waterfall.py    # Core enrichment engine
├── research.py     # Signal extraction + LLM briefs
├── evals.py        # Dataset-driven evaluation
├── report.py       # JSON/CSV output
└── twenty_push.py  # Twenty CRM integration
```

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| M0 | Scaffold (uv, deps, CI) | ✅ |
| M1 | Config, Models, LLM cache | ✅ |
| M2 | Website, Site Checks, DNS | ✅ |
| M3 | GitHub, RSS | ✅ |
| M4 | Waterfall engine, CLI run | ✅ |
| M5 | Research (signals, briefs) | ✅ |
| M6 | Apify (skipped) | ⏭️ |
| M7 | Evals (judge model) | ✅ |
| M8 | Twenty CRM push | ✅ |
| M9 | Polish, README, final | ✅ |

## Tests

```bash
bash scripts/gate.sh
# Runs: ruff check . && pytest -q
```

## License

MIT