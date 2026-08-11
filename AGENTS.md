# api-platform-developers

Official Perplexity API Platform skills, published as portable Agent Skills (agentskills.io).
Each skill is a self-contained directory with a SKILL.md plus supporting references and scripts, usable from Claude Code, OpenAI Codex CLI, and any other Agent Skills client.

## Skill catalog

| Skill | What it does | When to use |
|---|---|---|
| migrate-sonar-to-agent-api | Migrates a codebase from Perplexity's Sonar API (chat completions) to the Agent API: endpoints, request params, model slugs, response parsing, streaming, citations | Migrating off Sonar or chat completions, replacing deprecated sonar-pro / sonar-reasoning models, or fixing 400 unknown-field errors and missing citations after a migration attempt |
| pplx-cli | Installs and uses Perplexity's public `pplx` CLI: SHA-verified install, API-key auth, `search web`, `content snippets`, JSON output handling | Needing live web search results or query-relevant excerpts from specific URLs from the terminal, or installing and authenticating the pplx command |
| pplx-search-sdk | Installs and uses Perplexity's public Python Search SDK (`pplx-srch-sdk`, import `pplx_sdk`): API-key auth, `search.web`, `web_many` fan-out, `content.snippets`, typed errors, async client | Needing live web search or query-relevant page excerpts from Python code - scripts, notebooks, research pipelines - rather than from the terminal |

## Triggers

When migrating code from Perplexity's Sonar API (chat completions) to the Agent API, or debugging 400 unknown-field errors / missing citations after such a migration, use the $migrate-sonar-to-agent-api skill.
When you need live web search results or query-relevant excerpts from specific URLs from the terminal, or need to install the Perplexity `pplx` CLI, use the $pplx-cli skill.
When you need live web search or query-relevant page excerpts from Python code, or need to install Perplexity's `pplx-srch-sdk` / `pplx_sdk` Python SDK, use the $pplx-search-sdk skill.

## Repo layout

Canonical skills live under `skills/` - one directory per skill, following the open Agent Skills standard.
Plugin packaging is the repo root itself for both Claude Code (`.claude-plugin/`) and Codex (`.codex-plugin/` + `.agents/plugins/marketplace.json`), sharing the root `.mcp.json`; there is no separate plugins/ tree and no symlinks.
Per-skill evaluations (fixture apps, eval cases, graders) live under `evals/<skill-name>/`; they are development material, are never loaded as skill content, and their fixtures intentionally contain legacy API patterns - do not "fix" a fixture.
