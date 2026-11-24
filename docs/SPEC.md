# gtm-enrich: SPEC

**Pitch:** A waterfall enrichment and account-research CLI. Give it a list of company domains; it tries free sources in order, records which source answered and what it cost, writes an LLM research brief and an outbound angle per account, and pushes results to Twenty CRM. Ships with an eval harness that scores the generated angles.

Package name: `gtm_enrich`. CLI name: `gtm-enrich`.

## Architecture

```
accounts.csv (domain[, company_name])
   │
   ▼
waterfall: for each field, try providers in order, stop at first good value
   providers: website (Jina Reader / httpx) → github → apify (optional) → rss/news (optional)
   │
   ▼
EnrichedAccount (+ provenance: which provider, latency, cost_usd)
   │
   ├── signals.py   (pure Python: hiring, recent posts, tech hints, site checks)
   ├── research.py  (LLM: brief + 3 angles, each angle cites a signal id)
   ▼
out/accounts.jsonl, out/accounts.csv, out/report.md  ──> optional push to Twenty (reuse adapter pattern)
evals/: score angles (rules + LLM judge), compare prompt versions and models
```

## Providers (all free; each is a class with `name`, `fields_provided`, `fetch(domain) -> ProviderResult`)
- `website`: fetch homepage plus `/about`, `/pricing`, `/careers`, `/blog` if present. Use Jina Reader (`https://r.jina.ai/<url>`, free, no key needed for low volume) with fallback to direct `httpx` + `selectolax` or `beautifulsoup4` text extraction. Extract: description, pricing page present, careers page present, open role titles if listed, latest blog post titles, tech hints from HTML (script src domains like hubspot, segment, intercom, stripe).
- `site_checks`: free on-page checks from the HTML already fetched: title, meta description, h1 count, `llms.txt` present, sitemap present, schema.org JSON-LD present. Inspired by open-source SEO audit skills; output is a list of observations usable as outbound angles. No external API.
- `github`: GitHub REST API (free; optional `GITHUB_TOKEN`). Find org by domain or name, get public repo count, top repos by stars, recent activity date. Never fetch member emails.
- `apify` (optional, only if `APIFY_TOKEN` set): run **one actor id the user provides** via Apify's run-sync REST endpoint. Hard guard: `APIFY_MAX_ITEMS` (default 20) and a per-run item cap. Log estimated cost from the run's usage fields if present. **Use only the actor id and input JSON in `docs/ANSWERS.md`; do not guess.**
- `rss`: if the site exposes an RSS/Atom feed, parse latest 5 items with `feedparser`.
- `dns`: MX record lookup with `dnspython` to report the email provider (Google Workspace, Microsoft 365, other). No SMTP probing.
- Optional `agent_reach` note in README: users with Agent-Reach installed can swap the website provider for its channels. Do not add it as a dependency.

Each provider result: `ProviderResult(provider, fields: dict, ok: bool, error: str | None, latency_ms: int, cost_usd: float)`. Free providers report `cost_usd=0`.

## Waterfall
`waterfall.py`: config in `waterfall.yaml`: for each target field, an ordered list of providers. Run providers concurrently per account with `asyncio` + a semaphore (`MAX_CONCURRENCY`, default 4). Per-domain on-disk cache so re-runs are free. Output keeps provenance for every field.

## Research
`research.py`: one LLM call per account: input is the enriched account and the signals list with ids (`S1`, `S2`...). Output `ResearchBrief(summary, icp_fit_score 1-5, fit_reason, angles: list[Angle(text, signal_ids, channel: email|linkedin)])`. Prompt in `prompts/research_v1.md`. Code-level guard: drop any angle whose `signal_ids` reference a signal that does not exist.

ICP config in `icp.yaml` (user editable): target description, positive signals, negative signals. The README example ICP: B2B SaaS with a sales team and active hiring.

## Evals (the "eval harness" selling point)
- `evals/dataset.csv`: 30 to 50 public companies (domains only; real public companies are fine, no personal data).
- Rule checks per angle: under 60 words, cites at least one existing signal, contains a concrete detail (a number, product name, page or role title found in signals), no banned phrases (`evals/banned.txt`: "I hope this finds you well", "synergy", "game-changer", "quick question", etc.), no em dash.
- LLM judge (`LLM_JUDGE_MODEL`, must differ from `LLM_MODEL`): scores specificity 1-5 and plausibility 1-5 with a short reason, JSON output.
- `gtm-enrich eval --prompt research_v1 --prompt research_v2 --model worker`: prints a comparison table (pass rate per rule, mean judge scores, hallucination drops) and writes `evals/results/*.json` and `evals/REPORT.md`.
- Ship `research_v2.md` as an improved prompt so the README can show a before/after table.

## CLI
- `gtm-enrich run accounts.csv [--out out/] [--no-llm] [--providers website,github]`
- `gtm-enrich report out/accounts.jsonl` → markdown report with fill rate per field, provider hit rate, total cost, avg latency.
- `gtm-enrich push out/accounts.jsonl` → upsert companies plus a note with the brief to Twenty (reuse the same REST knowledge as crm-copilot; ask the user to paste the field names again or copy from crm-copilot).
- `gtm-enrich eval ...` as above.
- `gtm-enrich doctor` → which providers are configured and reachable.

## Milestones
- **M0 Scaffold:** as in crm-copilot (uv, ruff, pytest, CI, `.env.example`, `PROGRESS.md`).
- **M1 Core models, cache, LLM wrapper.**
- **M2 Website + site_checks + dns providers.** Tests with saved HTML fixtures in `tests/fixtures/` (write small fake HTML pages, do not commit scraped copyrighted pages).
- **M3 GitHub + RSS providers.** respx mocks.
- **M4 Waterfall engine + `run` (with `--no-llm`) + `report` (REVIEW CHECKPOINT).** Tests: provider order, stop-at-first-good, provenance recorded, cache prevents second fetch.
- **M5 Research step.** Tests: invalid signal ids dropped, JSON retry.
- **M6 Apify provider (optional).** Use the actor id and input from `docs/ANSWERS.md`; if it says SKIP, skip M6 and note it. Mocked tests plus one real small run by the user.
- **M7 Evals.** Dataset, rules, judge, comparison command, v2 prompt, REPORT.md with real numbers from the user's run.
- **M8 Twenty push.**
- **M9 Polish (FINAL REVIEW CHECKPOINT):** README (pitch, diagram, quickstart, provider table with cost column showing $0, sample report, eval before/after table, design decisions: waterfall with provenance, caching, cost guards, why no SMTP verification), `demo.tape`.

## Done means
Offline tests green, CI green, a real run on 20 accounts produces `out/report.md`, eval report with real numbers committed, README complete.
