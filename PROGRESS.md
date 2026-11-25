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

### M1 - Core models, cache, LLM wrapper
- Status: NOT STARTED

---

### M2 - Website + site_checks + dns providers
- Status: NOT STARTED

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