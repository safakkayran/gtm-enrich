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

### M3 - GitHub + RSS providers
- Status: NOT STARTED

---

### M4 - Waterfall engine + run + report (REVIEW CHECKPOINT)
- Status: NOT STARTED

---

### M5 - Research step
- Status: NOT STARTED

---

### M6 - Apify provider (optional)
- Status: NOT STARTED

---

### M7 - Evals
- Status: NOT STARTED

---

### M8 - Twenty push
- Status: NOT STARTED

---

### M9 - Polish (FINAL REVIEW CHECKPOINT)
- Status: NOT STARTED

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