---
name: migrate-sonar-to-agent-api
description: "Migrate code from Perplexity's Sonar API (chat completions) to the Agent API (/v1/agent, responses.create). Maps endpoints, request params, model slugs (sonar, sonar-pro, sonar-reasoning, sonar-deep-research), response parsing, streaming, and citations. Use when migrating from Sonar, moving chat completions to the Agent API, replacing deprecated sonar-pro or sonar-reasoning models, or fixing 400 unknown-field errors and missing citations after a migration attempt."
when_to_use: "Any request like: migrate from Sonar, chat completions to Agent API, sonar-pro deprecated, sonar-reasoning replacement, citations missing on Agent API, top-level citations gone, 400 invalid_request unknown field on api.perplexity.ai, choices[0] to output_text, move to /v1/agent or /v1/responses, update ChatPerplexity or OpenAI SDK code pointed at Perplexity, Perplexity streaming events instead of delta.content."
argument-hint: "[path to code to migrate]"
---

# Migrate Sonar chat completions to the Perplexity Agent API

## What this skill does

Migrates a codebase from Perplexity's Sonar API (`POST /chat/completions`, `chat.completions.create()`) to the Agent API (`POST /v1/agent`, `responses.create()`).
Both APIs are live; this is a contract migration - endpoint, request body, response parsing, streaming - not a rewrite.
Start by inventorying Sonar usage:

```
python scripts/scan_sonar_usage.py [path-to-code]
```

Run it from this skill's directory (the directory containing this SKILL.md), or pass the script's full path.
It prints a file-by-file migration checklist with line numbers and the reference file that covers each finding.

Canonical human guide: https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar - when this skill and the live docs disagree on an API fact, the docs win; cross-check there if something looks off.
If a `perplexity-docs` MCP server is available in your session (the Claude Code plugin ships one; other clients can add https://docs.perplexity.ai/mcp), prefer its search tools for that cross-check.
Never invent model availability, limits, defaults, or API behavior: if a fact is in neither this skill nor the docs, verify it against the live API - or state that you could not.

## Step 1: classify each call site by integration style

Classify before touching code, and KEEP the style - do not "upgrade" raw HTTP to an SDK or swap SDKs.

- **(a) Raw HTTP** (`requests`, `fetch`, `curl` to `https://api.perplexity.ai/chat/completions`):
  migrate to `POST https://api.perplexity.ai/v1/agent` with the same HTTP library.
- **(b) OpenAI SDK pointed at Perplexity**:
  set `base_url="https://api.perplexity.ai/v1"` - the `/v1` is required, the SDK appends `/responses` - and switch to `client.responses.create()`.
  Perplexity-only fields (`preset`, `max_steps`, `response_format`, Perplexity tool types) go through `extra_body={...}` in Python or a type cast in TypeScript.
  Requires a recent OpenAI SDK (`openai>=1.66` for Python).
- **(c) Perplexity SDK** (`from perplexity import Perplexity` / `@perplexity-ai/perplexity_ai`):
  switch `client.chat.completions.create()` to `client.responses.create()`.
  Same client construction, same `PERPLEXITY_API_KEY` env var.
- **(d) Framework bridge** (LangChain `ChatPerplexity`, LlamaIndex Perplexity LLM, OpenAI Agents SDK):
  read [integration-styles.md](references/integration-styles.md) - it has the concrete Agents SDK class swap and the ranked options for LangChain/LlamaIndex.

**Classification trap:** the Perplexity call may live OUTSIDE the framework as a sibling SDK client.
Find which client actually hits `api.perplexity.ai` and migrate that call site by its own style.
Leave framework-internal LLMs pointed at other providers alone.

**Do NOT migrate:**

- Search API code (`client.search.create()`, `POST /search`) - a different product, unaffected.
- Code already on the Agent API (`responses.create`, `/v1/agent`, `/v1/responses`).
- Historical or factual references to "the Sonar API" as a legacy platform in prose.
- Third-party showcase code that merely describes what someone built.

## The strict-mode warning (read this first)

> **THE #1 MIGRATION FAILURE:** the Agent API rejects ANY unknown or leftover field - top-level or nested - with HTTP 400:
> `{"error":{"message":"invalid request body: json: unknown field \"X\"","type":"invalid_request","code":400,"param":"X"}}`
>
> Sonar silently dropped many params; the Agent API does not.
> Strip every field not explicitly mapped in [request-mapping.md](references/request-mapping.md), including everything on its REMOVE list.

## Top 10 pitfalls

1. **Leftover Sonar params -> 400 unknown field.**
   Strict mode (above).
   Check every request body against the param table and REMOVE list in [request-mapping.md](references/request-mapping.md).

2. **Web search is NOT automatic - and offering the tool does not guarantee the model calls it.**
   A bare model request does no search and answers ungrounded.
   Add `"tools": [{"type": "web_search"}]` (or use a preset, which bundles it).
   For citation-critical flows, force the search with `"tool_choice": {"type": "web_search"}` or use a preset.
   Even forced, an occasional run returns zero sources - handle empty `search_results` gracefully.
   Do not force `tool_choice` universally; it adds cost and latency where grounding is optional.

3. **Citations moved.**
   There is no top-level `citations` or `search_results` on Agent responses.
   Read the `search_results` OUTPUT ITEM inside `output[]`.
   Message `annotations` are often an empty array - do not rely on them for citations.

4. **200-wrapped failures.**
   Failed and cancelled runs return HTTP 200 with `status: "failed"` or `"cancelled"` and a populated `error` field.
   Always branch on `response.status`, never only on the HTTP status code.

5. **Streaming consumers must handle ALL terminals.**
   Exactly one of `response.completed`, `response.failed`, `response.incomplete`, `response.cancelled` arrives, plus a bare `error` event for transport failures.
   A consumer that only exits on `response.completed` hangs on failed runs.

6. **No `perplexity/sonar-pro` slug exists.**
   Map `sonar-pro` per the two-option rule (preset `"low"` vs `perplexity/sonar` + web_search) in [models-and-presets.md](references/models-and-presets.md).

7. **`max_output_tokens` is REQUIRED for `anthropic/*` models** (400 otherwise); values under 16 floor to 16.
   On presets and reasoning models, tight caps can be consumed by reasoning tokens before any text or search appears - size generously or omit.
   `incomplete_details.reason: "max_output_tokens"` is the truncation signal (the old `finish_reason: "length"`).

8. **OpenAI SDK traps.**
   `text={"format": ...}` is rejected - send top-level `response_format` via `extra_body`.
   Perplexity-only output items deserialize as raw dicts: use `result.get("url")`, not `result.url`, and avoid `model_dump()` on responses containing them.
   Prefer `response.output_text` for the plain-text case.

9. **Reserved custom-function names.**
   Custom tool names colliding with built-in tool names (`web_search`, `search_web`, `people_search`, `search_people`, `fetch_url`, `finance_search`, `sandbox`, and others) are rejected with a 400.
   Sonar allowed shadowing; rename during migration (e.g. `web_search` -> `my_web_search`).
   If any custom tool name 400s, rename it - other names may also be reserved.

10. **Preset mechanics.**
    `instructions` alongside a preset REPLACES the preset's system prompt (empty string clears it).
    Preset tools cannot be disabled (`tools: []` does not clear them; `max_tool_calls: 0` is the blunt all-tools off-switch).
    Request fields override preset values.
    Presets may resolve to third-party models.

## Step-by-step procedure

1. **Scan.**
   Run `python scripts/scan_sonar_usage.py [path-to-code]` from this skill's directory (the directory containing this SKILL.md), or pass the script's full path, and turn its output into a file-by-file checklist.
2. **Classify** each call site by integration style (Step 1 above).
3. **Rewrite the request** per [request-mapping.md](references/request-mapping.md):
   endpoint to `/v1/agent`; `messages` -> `input` (system prompt to `instructions` or a system input item); model slug or preset per [models-and-presets.md](references/models-and-presets.md); search filters into `tools[web_search].filters`; strip everything on the REMOVE list.
4. **Rewrite response handling** per [response-and-streaming.md](references/response-and-streaming.md):
   `output[]` walk or `output_text`; citations from the `search_results` item; usage key renames; status branching.
5. **Rewrite streaming consumers** per [response-and-streaming.md](references/response-and-streaming.md):
   typed SSE events instead of `delta.content`; handle all terminals.
6. **Migrate function calling**:
   Responses-style tool shape (top-level `name`/`description`/`parameters`), reserved-name renames, `function_call` -> `function_call_output` loop.
   Details in [integration-styles.md](references/integration-styles.md).
7. **Verify** per [verification.md](references/verification.md):
   live smoke test each distinct call shape, then grep for leftovers.
   The live run is MANDATORY when an API key is available - compile-clean SDK code can still crash on call (see the typed-kwarg trap in integration-styles.md); if you truly cannot run it, say so explicitly in your summary.

**Minimal-diff rule:** keep the author's structure, naming, and voice; do not refactor unrelated code.
When a Sonar feature has no Agent equivalent (images, related questions, academic search mode), apply the documented workaround from [request-mapping.md](references/request-mapping.md) if it is small.
For `return_related_questions` specifically, use the lightweight prompt-delimiter recipe in request-mapping.md - it fits free-text flows too.
If no workaround fits, remove the feature AND call the removal out in your migration notes; never drop user-facing output silently.

## Verification loop

- Compile or typecheck every changed file.
- Run one real request per distinct call shape against production, with a small `max_output_tokens` and a cheap model (except on presets and reasoning models - see pitfall 7).
- Capture real response JSON for any printed samples; never fabricate response JSON.
- Grep for leftovers: `chat.completions`, `choices[0]`, `max_tokens` (as a request field), top-level `search_recency_filter`, `citations`, `delta.content`, `sonar-` model slugs.
  Every hit must be intentional legacy prose.
- Full checklist in [verification.md](references/verification.md).

## Reference index

- [request-mapping.md](references/request-mapping.md) - read when rewriting a request body: full param table, the REMOVE list with workarounds, limits.
- [response-and-streaming.md](references/response-and-streaming.md) - read when rewriting response parsing or a streaming consumer: output[] walk, search_results shape, full SSE event set, error catalogue.
- [models-and-presets.md](references/models-and-presets.md) - read when choosing a target model or preset: slug mapping, preset mechanics.
- [integration-styles.md](references/integration-styles.md) - read when the code uses the OpenAI SDK, Perplexity SDK, LangChain, LlamaIndex, or the OpenAI Agents SDK.
- [verification.md](references/verification.md) - read before declaring the migration done: checklist, live smoke pattern, leftover greps.
