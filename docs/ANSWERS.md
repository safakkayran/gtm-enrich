# ANSWERS.md

Fill this in BEFORE starting the loop and save it as `docs/ANSWERS.md` in the repo.
Delete the sections for other repos. Write "SKIP" for anything you want the agent to leave out.
The agent may only use external API details written here or in SPEC.

## Common (all repos)
- GitHub repo URL: https://github.com/safakkayran/gtm-enrich
- Git push works from the server (yes/no): yes (HTTPS via gh auth)
- `node --version` output (or "not installed"): v26.12.1
- LiteLLM base URL (e.g. http://localhost:4000): http://127.0.0.1:4000
- Model alias for generation (LLM_MODEL): nim-laguna
- Model alias for evals judge (LLM_JUDGE_MODEL, must differ): nim-step

---

## gtm-enrich
- GITHUB_TOKEN available (yes/no): no (unauthenticated requests for public data; lower rate limits)
- Apify: use it (yes/SKIP): SKIP
  - Actor id (from the Apify Store page):
  - Actor pricing model (pay per result / pay per event / usage; must NOT be monthly rental):
  - Example input JSON from the actor page:
  - Which fields of the output we use:
- Twenty push: same API details as crm-copilot (copy that section here, or SKIP):
  - Base URL: http://localhost:3000
  - API key: [from .env TWENTY_API_KEY]
  - Auth header: Authorization: Bearer ***
  - REST prefix: `/rest`
  - Companies: GET /rest/companies?filter=name[eq]:"<name>", POST /rest/companies, PATCH /rest/companies/{id}
  - Opportunities: GET /rest/opportunities?filter=companyId[eq]:"<companyId>",stage[neq]:"CUSTOMER", POST /rest/opportunities, PATCH /rest/opportunities/{id}
  - Notes: POST /rest/notes with bodyV2.markdown, POST /rest/noteTargets with noteId, opportunityId, companyId
  - Tasks: POST /rest/tasks, POST /rest/taskTargets with taskId, opportunityId, companyId
  - Stage values: NEW, SCREENING, MEETING, PROPOSAL, CUSTOMER
- ICP description for `icp.yaml` (2-3 sentences), positive signals, negative signals:
  description: >
    Seed to Series C AI or AI-devtool companies (B2B, 10-300 employees) that are
    building or scaling a go-to-market team. Ideal accounts have a product-led or
    developer-led motion that is starting to add sales, and need someone to build
    GTM automation, data enrichment and CRM workflows.

  positive_signals:
    - open roles for GTM engineer, growth engineer, RevOps, marketing ops, or first sales hires
    - recent funding announcement (last 12 months)
    - product is AI-native, an LLM tool, an AI agent platform, or a developer tool
    - public GitHub org with active repos (recent commits) or an open-source product
    - pricing page with self-serve tier plus "contact sales" or enterprise tier
    - active blog or changelog (posts in the last 60 days)
    - modern GTM stack hints on site (HubSpot, Segment, Intercom, Clay, Attio, Stripe)

  negative_signals:
    - enterprise company over 1000 employees
    - agency, consultancy or services business
    - no product or pricing page
    - no hiring and no blog activity in the last 6 months
    - B2C consumer app with no B2B motion
    - crypto-only or trading product with no AI component

- 30-50 public company domains for the eval dataset (or "agent picks well-known B2B SaaS"): agent picks well-known B2B SaaS