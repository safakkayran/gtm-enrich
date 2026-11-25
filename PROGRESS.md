# PROGRESS.md

## Milestone Log

### M0 - Scaffold ✅
- uv project initialized with src layout
- Dependencies: httpx, pydantic, pydantic-settings, typer, rich, openai, python-dotenv, selectolax, feedparser, dnspython, pyyaml
- Dev dependencies: pytest, pytest-asyncio, respx, ruff
- Ruff and pytest configured
- GitHub Actions CI (ruff + pytest on push)
- .env.example with placeholders
- Trivial import test passing
- Package structure: src/gtm_enrich/
- Gate: PASSED (1 test)

---

### M1 - Core models, cache, LLM wrapper ✅
- `config.py`: Settings with pydantic-settings (LiteLLM, GitHub, Apify, Twenty, cache, concurrency)
- `models.py`: All Pydantic models (EnrichedAccount, WaterfallField, ProviderResult, Signal, Angle, ResearchBrief, EvalResult, WaterfallConfig, ICPConfig, RunResult)
- `llm.py`: CachedLLMClient with disk cache, retry on 429/5xx, JSON validation retry
- Gate: PASSED (1 test)

---

### M2 - Website + site_checks + dns providers ✅
- `website.py`: Jina Reader + httpx fallback, extracts description, pricing page, careers page, blog posts, tech hints, open roles
- `site_checks.py`: On-page SEO/technical (title, meta, h1 count, llms.txt, sitemap, schema.org)
- `dns.py`: MX record lookup with email provider identification (Google Workspace, Microsoft 365, etc.)
- `providers/__init__.py`: Exports all fetch functions
- Tests in `test_m2_providers.py` (3 tests) covering all three providers
- Gate: PASSED (4 tests)

---

### M3 - GitHub + RSS providers ✅
- `github.py`: Org lookup by domain guess, falls back to repo search; extracts stars, forks, language, license, top repos
- `rss.py`: Discovers feed via common paths + link rel=alternate; parses entries with title, link, published, summary, tags
- Tests in `test_m2_providers.py` extended (5 new tests: 2 GitHub, 3 RSS)
- Gate: PASSED (8 tests)

---

### M4 - Waterfall engine + run + report (REVIEW CHECKPOINT) ✅
- `waterfall.py`: Core engine - runs providers in priority order, first non-null wins with provenance
- `run_enrichment()`: Orchestrates multi-domain runs, builds EnrichedAccount with WaterfallField
- `report.py`: JSON/CSV output with summary stats
- `cli.py`: `gtm-enrich run` command with domain list, provider order, format options
- `models.py`: Extended with WaterfallConfig.provider_order, ICPConfig weights
- `config.py`: Default configs for waterfall and ICP
- Tests in `test_m4_waterfall.py` (3 tests: single domain, provenance, multi-domain)
- Gate: PASSED (11 tests)

---

### M5 - Research step ✅
- `research.py`: Signal extraction from all provider fields, LLM-powered research briefs with 3 outbound angles (email/LinkedIn), fallback when LLM unavailable
- `waterfall.py`: Integrated research step into run_enrichment
- Tests in `test_m5_research.py` (5 tests: signal extraction per provider, fallback brief, multi-account)
- Gate: PASSED (16 tests)

---

### M6 - Apify provider (optional)
- Status: NOT STARTED

---

### M7 - Evals ✅
- `evals.py`: Dataset-driven evaluation (CSV/JSONL), 6 rule checks + judge scores (1-5), judge model `nim-step`
- `test_m7_evals.py`: 5 tests (evaluate_angle, CSV/JSONL load, run_evals output, EvalResult model)
- Gate: PASSED (21 tests)

---

### M8 - Twenty push ✅
- `twenty_push.py`: TwentyClient with upsert by domain, payload builder, async push with batch support
- `test_m8_twenty_push.py`: 6 tests (init, headers, no-key, payload build, PushResult, close)
- Gate: PASSED (27 tests)

---

### M9 - Polish (FINAL REVIEW CHECKPOINT) ✅
- `cli.py`: Added `push` command for Twenty CRM integration
- `README.md`: Complete documentation (install, usage, providers, waterfall, evals, structure)
- Gate: PASSED (27 tests)

---

## Decisions
- Using src/ layout with package name `gtm_enrich`
- Python 3.11+ required
- LiteLLM models: nim-laguna (worker), nim-step (judge)
- GitHub provider uses unauthenticated requests (no GITHUB_TOKEN)
- Apify provider: SKIP for now
- Twenty push: copy crm-copilot's API details
- ICP: AI/devtool companies, Seed to Series C, 10-300 employees
- Eval dataset: agent picks well-known B2B SaaS

## Skipped, needs user
- None yet

## Test changes
- None yet

## Known issues
- None yet