# Verification: declaring the migration done

Read this before declaring the migration done.
Run every check; report failures instead of papering over them.

## Checklist

- [ ] Every changed file compiles or typechecks (`python -m py_compile`, `tsc --noEmit`, etc.).
- [ ] Every distinct request shape was accepted live - no 400 unknown-field errors.
- [ ] Grounding verified: `search_results` output items are present when the flow expects sources.
      Remember that offering `web_search` does not guarantee a call; citation-critical flows force it via `tool_choice`.
- [ ] Citations are sourced from the `search_results` output item, not from a top-level `citations` field or message `annotations`.
- [ ] Status branching present: code checks `response.status` (`failed`/`cancelled` arrive with HTTP 200) and handles `incomplete` + `incomplete_details.reason: "max_output_tokens"`.
- [ ] Streaming consumers handle all four terminal events plus the bare `error` event.
- [ ] Structured output (`response_format`) validates against the intended schema on a live response.
- [ ] Usage and cost keys read the Agent names: `input_tokens`, `output_tokens`, `cost.input_cost`, `cost.output_cost`, `cost.tool_calls_cost`, `cost.total_cost`.

## Live smoke pattern

- One real API call per distinct request shape (plain, streaming, structured output, function calling, preset).
- Use a small `max_output_tokens` (e.g. 64-256) and the cheapest suitable model - EXCEPT on presets and reasoning models, where tight caps get consumed by reasoning tokens before any text or search appears; there, size generously or omit the cap.
- Read `PERPLEXITY_API_KEY` from the environment; never print or log it.
- Capture one real response JSON per shape and use it for any printed sample output in docs or comments.
  Never fabricate response JSON.
- If the code needs external services or heavy dependencies (a chat bot, a database, an agent framework), extract just the migrated Perplexity call into a scratch script, smoke-test that, and note that the surrounding integration was not exercised.

## Leftover greps

Grep the final diff; every hit must be intentional legacy prose (e.g. "migrated from the Sonar API" in a changelog):

- `chat.completions`
- `choices[0]`
- `max_tokens` (as a request field; `max_output_tokens` is fine)
- `search_recency_filter` at the top level of a request body (inside `tools[web_search].filters` is fine)
- `citations` (top-level response access)
- `delta.content`
- `search_results` accessed as a top-level response field (the output item is fine)
- `sonar-` model slugs (`sonar-pro`, `sonar-reasoning`, `sonar-deep-research`)
- OpenAI SDK `base_url` values missing the trailing `/v1`

## A/B note

Agent `perplexity/sonar` output is not byte-identical to chat `sonar`, and pricing differs (see the public pricing page).
For quality-sensitive flows, A/B compare a sample of real prompts before cutover.

## When something still fails

Cross-check the live documentation - it is canonical for API facts and may be newer than this skill:
the migration guide at https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar, and the Agent API section around it (models, tools/web-search, output-control).
Via the `perplexity-docs` MCP server, search with compact queries (2-6 terms, e.g. "web_search filters recency"); without MCP, fetch the docs pages directly.
Model and preset catalogs drift fastest - re-verify slugs against GET https://api.perplexity.ai/v1/models (no auth) rather than trusting any table, including this skill's.
