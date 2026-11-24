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
- GITHUB_TOKEN available (yes/no):
- Apify: use it (yes/SKIP):
  - Actor id (from the Apify Store page):
  - Actor pricing model (pay per result / pay per event / usage; must NOT be monthly rental):
  - Example input JSON from the actor page:
  - Which fields of the output we use:
- Twenty push: same API details as crm-copilot (copy that section here, or SKIP):
- ICP description for `icp.yaml` (2-3 sentences), positive signals, negative signals:
- 30-50 public company domains for the eval dataset (or "agent picks well-known B2B SaaS"):