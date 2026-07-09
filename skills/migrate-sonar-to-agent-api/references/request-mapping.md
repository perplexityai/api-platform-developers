# Request mapping: Sonar chat completions -> Agent API

Read this when rewriting a request body.
Rule zero: the Agent API is STRICT.
Any unknown or leftover field - top-level or nested - returns HTTP 400 `{"error":{"message":"invalid request body: json: unknown field \"X\"","type":"invalid_request","code":400,"param":"X"}}`.
Strip every field you do not explicitly map below.

## Endpoint mapping

| From | To |
|---|---|
| `POST /chat/completions`, `POST /v1/sonar`, `POST /v1/chat/completions` (all live, still supported) | `POST https://api.perplexity.ai/v1/agent` |
| Perplexity SDK `client.chat.completions.create()` | `client.responses.create()` |
| OpenAI SDK `chat.completions.create()` at base `api.perplexity.ai` | OpenAI SDK `responses.create()` at base `https://api.perplexity.ai/v1` |

`/v1/agent` and `/v1/responses` are equivalent endpoints - the API surface is identical.
Use `/v1/agent` in raw HTTP and cURL code; OpenAI SDKs reach `/v1/responses` via the base_url, which is fine.
Auth is unchanged: `Authorization: Bearer $PERPLEXITY_API_KEY`.

## Web search is not automatic

A bare model request does no search and returns an ungrounded answer.
If the Sonar code relied on search (almost all does), add `"tools": [{"type": "web_search"}]` - or use a preset, which bundles tools.
Offering the tool does not guarantee the model calls it; for citation-critical flows force it with `"tool_choice": {"type": "web_search"}`.

## Request param table

| Sonar param | Agent API | Notes |
|---|---|---|
| `messages` | `input` | String for a single user turn; else array of `{role, content}` items (roles: user, assistant, system, developer). System prompt: keep as a `role:"system"` input item or move to top-level `instructions`. |
| (system message) | `instructions` or input item | With a preset, `instructions` REPLACES the preset prompt (never appends); `""` clears it. |
| `model` | `model` | New slugs - see [models-and-presets.md](models-and-presets.md). Or `preset`, or `models` (fallback list, max 5). |
| `max_tokens` / `max_completion_tokens` | `max_output_tokens` | REQUIRED when model is `anthropic/*` (else 400 "max_output_tokens is required when using Anthropic models"). Values under 16 are floored to 16. |
| `temperature`, `top_p`, `stream` | unchanged | temperature 0..2, top_p 0..1. |
| `stream_options.include_usage` | unchanged | Defaults to TRUE on both (unlike OpenAI) - do not add it "to enable usage". |
| `reasoning_effort` | `reasoning: {"effort": ...}` | Enum: `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. |
| `response_format` | `response_format` (TOP-LEVEL, same shape) | OpenAI-Responses-style `text: {"format": ...}` is REJECTED in requests (400 unknown field "format") even though responses echo `text.format`. `json_schema.name` is optional in practice today; include a 1-64 char `[A-Za-z0-9_-]` name for forward-safety. `type:"regex"` is not supported. |
| `search_domain_filter` (top-level) | `tools[web_search].filters.search_domain_filter` | Max 20 entries, each <= 253 chars, scheme-less (`example.com`, not `https://example.com`), `-` prefix denies a domain. |
| `search_recency_filter` | `tools[web_search].filters.search_recency_filter` | `hour\|day\|week\|month\|year`; mutually exclusive with the after/before date filters. |
| `search_after_date_filter`, `search_before_date_filter` | same names inside `tools[web_search].filters` | Format `MM/DD/YYYY`. |
| `last_updated_after_filter`, `last_updated_before_filter` | same names inside `tools[web_search].filters` | Format `MM/DD/YYYY`. |
| `web_search_options.search_context_size` | `tools[web_search].search_context_size` | Sits on the tool object, NOT inside `filters`. |
| `web_search_options.user_location` | `tools[web_search].user_location` | On the tool object, NOT inside `filters`. `{latitude, longitude, country, region, city}`. |
| `num_search_results` | `tools[web_search].max_results` | 1..50. |
| `tools` (custom functions) | `tools` with `{type:"function", name, description, parameters, strict}` | Name and description at the tool's top level (Responses style), not nested under `function`. Watch reserved names - see [integration-styles.md](integration-styles.md). |
| `tool_choice` | `tool_choice` | `"none"\|"auto"\|"required"` or object forms: `{"name":"my_fn"}`, `{"type":"web_search"}`, `{"type":"required"}`. |
| `parallel_tool_calls` | unchanged | Default true. |
| `language_preference` | unchanged | |
| `image_url` content part | `input_image` content part | `{"type":"input_image","image_url":"..."}` (data URI or HTTPS URL, <= 2048 chars). |

## REMOVE list (any leftover = 400)

| Sonar param | Action | Workaround |
|---|---|---|
| `disable_search` | REMOVE | Omit the `web_search` tool. With a preset, preset tools stay enabled - there is no public field to disable them; `max_tool_calls: 0` disables ALL tool calls. |
| `enable_search_classifier` | REMOVE | Provide `web_search` and let the model decide when to call it. |
| `search_mode: "sec"` | REMOVE | Use the `finance_search` tool instead. |
| `search_mode: "academic"` | REMOVE | No equivalent. |
| `return_images`, `image_domain_filter`, `image_format_filter` | REMOVE | Prompt for image URLs plus a structured-output schema. |
| `return_related_questions` | REMOVE | Do not silently drop this user-facing feature - see the recipe below the table. |
| `presence_penalty`, `frequency_penalty` | REMOVE | No equivalent. They may appear as echo-only zeros in responses; they are not settable. |
| `stop` | REMOVE | No equivalent. |
| `top_k` | REMOVE | No equivalent. |
| `n` | REMOVE | Only single-sample; run N requests if needed. |
| `logprobs`, `top_logprobs` | REMOVE | Some such fields are accepted but have no effect; do not carry them over. |
| `web_search_options.search_type` / pro search | REMOVE | Use `max_steps` (1..100) or a preset for multi-step behavior. |
| `search_language_filter` | REMOVE | No equivalent. |
| `return_videos`, `num_images`, `num_videos`, `media_response` | REMOVE | No equivalent. |
| `search_mode`, `web_search_options` (the container fields themselves) | REMOVE | Contents relocate per the table above; the containers must not remain. |
| `file_url` / `pdf_url` / `video_url` content parts | REMOVE | No public equivalent on the Agent API. |

### Related-questions recipe (`return_related_questions` replacement)

The feature is user-facing output - keep it working instead of deleting it:

- **Free-text flows (lightweight, preferred):** append one instruction to the prompt, e.g. `End with a section titled "Related questions:" listing 3 short follow-up questions.`, then split the answer on that delimiter.
  No schema, no extra call.
- **Structured flows:** add a `related_questions: string[]` property to the existing `response_format` JSON schema.
- **Last resort:** a second cheap request (`perplexity/sonar`, no tools, small `max_output_tokens`) that generates follow-ups from the final answer.

Only remove the feature if none of these fit, and call the removal out in the migration notes - never drop it silently.

## New Agent-only request fields worth adopting

- `preset` - a named configuration bundling model, tools, and behavior; see [models-and-presets.md](models-and-presets.md).
- `models` - fallback list, max 5, tried in order; `response.model` echoes the served one.
- `max_steps` - 1..100, caps multi-step agentic behavior.
- `max_tool_calls` - `0` disables all tool calls.
- `previous_response_id` - chains turns; requires the prior response to have `status:"completed"` and the same account; works even with `store:false`.
- `background` - `true` returns immediately with `status:"queued"`; see [response-and-streaming.md](response-and-streaming.md).
- `metadata` - max 16 keys, key <= 64 chars, value <= 512 chars.
- `store` - `false` hides the response from GET but it remains valid as `previous_response_id`.
- `truncation` - `auto|disabled`.

## Limits

| Limit | Value / behavior |
|---|---|
| Request body | <= 32 MiB, else 413 `payload_too_large` |
| `search_domain_filter` | <= 20 entries, scheme-less, <= 253 chars each |
| `models` fallback chain | <= 5 |
| `metadata` | <= 16 keys; key <= 64; value <= 512 |
| MCP servers | <= 16 |
| `fetch_url` tool | `max_urls` 1..10; `total_budget_tokens` <= 120000 |
| `max_output_tokens` | floor 16 |
| `max_steps` | 1..100 |
| Rate limits | Vary by tier; on 429 (`request_rate_limit_exceeded`) retry with backoff and honor the `X-RateLimit-*` headers |
