# Response parsing, streaming, and errors: Sonar -> Agent API

Read this when rewriting response handling or a streaming consumer.

## Response mapping table

| Sonar | Agent API |
|---|---|
| `completion.choices[0].message.content` | SDK: `response.output_text`. Raw HTTP: walk `output[]` (snippet below). |
| `citations` (top-level URL list) | GONE. Use the `search_results` OUTPUT ITEM: the `output[]` item with `type:"search_results"`, shape `{type, queries: [...], results: [{id, url, title, snippet, date, last_updated, source}]}`. There is NO top-level `citations` or `search_results` on Agent responses. |
| `search_results` (top-level) | Same `search_results` output item as above. |
| message `annotations` | May carry `url_citation {url, start_index, end_index, title}` entries but is often an EMPTY array - do not rely on annotations for citations; use the `search_results` item. |
| `usage.prompt_tokens` | `usage.input_tokens` |
| `usage.completion_tokens` | `usage.output_tokens` |
| `usage.total_tokens` | `usage.total_tokens` |
| `usage.cost.{input_tokens_cost, output_tokens_cost, request_cost, total_cost}` | `usage.cost.{input_cost, output_cost, tool_calls_cost, total_cost, currency:"USD", tool_calls_cost_details}` |
| (search billing) | `usage.tool_calls_details` and `cost.tool_calls_cost_details` are keyed by billing tool names that differ from the request-side tool types: `search_web` (not web_search), `search_people` (not people_search), `fetch_url`, `finance_search`, `sandbox`. |
| `images`, `videos`, `related_questions` | GONE. Workaround: structured outputs plus prompting; for `related_questions` use the lightweight recipe in [request-mapping.md](request-mapping.md). |
| `id` | `id` (`resp_...`), plus `object:"response"`, `created_at`, `completed_at`, `status`. |
| `finish_reason` | No direct field. Check `response.status` (below) and `incomplete_details.reason` (`"max_output_tokens"` ~ finish_reason `"length"`). |

### Raw-HTTP text extraction

```python
data = resp.json()  # POST https://api.perplexity.ai/v1/agent
text = "".join(
    part["text"]
    for item in data["output"] if item["type"] == "message"
    for part in item["content"] if part["type"] == "output_text"
)
sources = next(
    (item["results"] for item in data["output"] if item["type"] == "search_results"),
    [],
)
```

### URL availability by result type

Web `search_results` items expose URLs, and `people_search_results` entries share the same result shape including `url`, `title`, `snippet`, `date`, and `last_updated` (verified against production).
`finance_results` and `sandbox_results` items carry no `url` field - code that surfaces sources must account for finance-only answers yielding zero citation URLs.

### Other output item types

`function_call` (custom tool call to execute client-side; has `call_id`, `name`, `arguments`), `fetch_url_results`, `people_search_results`, `finance_results`, `sandbox_results`, `mcp_list_tools`, `mcp_call`, `unknown` (forward-compat).
There are NO reasoning output items - reasoning appears only as `response.reasoning.*` streaming events.

## Streaming

Sonar: iterate chunks, read `chunk.choices[0].delta.content`.
Agent: typed SSE events (`data: <JSON>\n\n`), each with a `type` and a monotonic `sequence_number`.
There is no `[DONE]` sentinel.

Minimal robust consumer:

```python
stream = client.responses.create(
    model="perplexity/sonar",
    input="...",
    tools=[{"type": "web_search"}],
    stream=True,
)
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.completed":
        break
    elif event.type in ("response.failed", "response.incomplete", "response.cancelled", "error"):
        raise RuntimeError(f"stream ended: {event.type}")
```

Raw-HTTP SSE consumer (same terminal rules; use this when the code streams with `requests`/`fetch` instead of an SDK):

```python
resp = requests.post(
    "https://api.perplexity.ai/v1/agent",
    headers={"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"},
    json={"model": "perplexity/sonar", "input": "...",
          "tools": [{"type": "web_search"}], "stream": True},
    stream=True,
)
resp.raise_for_status()
for line in resp.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue  # blank keep-alive lines between events
    event = json.loads(line[len("data: "):])  # each event is one single-line JSON
    if event["type"] == "response.output_text.delta":
        print(event["delta"], end="", flush=True)
    elif event["type"] == "response.completed":
        break
    elif event["type"] in ("response.failed", "response.incomplete", "response.cancelled", "error"):
        raise RuntimeError(f"stream ended: {event['type']}")
```

Wire notes: every event arrives as a single `data: <one-line JSON>` line followed by a blank line; there is no `event:` field line and no `[DONE]` sentinel.

MANDATORY: handle ALL terminals.
Exactly one of `response.completed`, `response.failed`, `response.incomplete`, `response.cancelled` arrives, plus a bare `error` event for transport failures.
A consumer that only exits on `response.completed` hangs (or silently drops errors) on failed runs.

Lifecycle order: `response.created` -> `response.in_progress` -> [tool/reasoning legs, `response.output_item.added`, `response.output_text.delta` ...] -> `response.output_text.done` -> `response.output_item.done` -> terminal.
Reasoning and tool progress arrive as `response.reasoning.started/stopped` and `response.reasoning.search_queries/search_results` events; `response.output_item.added` for a `function_call` already carries `call_id`, `name`, and `arguments`.
Terminal snapshot events (`completed`/`incomplete`) carry the full `response` object including usage, unless `stream_options.include_usage:false`.
`stream_options.include_usage` defaults to TRUE (opposite of OpenAI).
Treat unrecognized event types as ignorable (`response.unknown` exists by design).

## Error handling

Envelope: `{"error": {"message": str, "type": str, "code": int, "param"?: str}}`; the HTTP status matches `code`.

| HTTP | type | When |
|---|---|---|
| 400 | `invalid_request`, `invalid_model`, `invalid_parameter`, `invalid_date_format`, `invalid_search_domain_filter`, ... | Unknown field (with `param`), bad model slug, bad filter, missing `max_output_tokens` on `anthropic/*`, reserved function name, expired reconnect cursor. |
| 401/403 | `forbidden` | Bad or blocked key. |
| 404 | `not_found` | Unknown response id (also returned for other accounts' ids and `store:false` responses). |
| 413 | `payload_too_large` | Body > 32 MiB. |
| 424 | `external_connector_error` | MCP server unreachable. |
| 429 | `request_rate_limit_exceeded` | Rate limit; retry with backoff; `X-RateLimit-*` headers present. |
| 5xx | `internal_error`, `bad_gateway`, `upstream_structured_output_failed`, `gateway_timeout` | Retry-worthy. |

CRITICAL: cancelled and model-error runs return HTTP 200.
The Response object arrives with `status: "cancelled"` or `"failed"` and a populated `error` field.
Always branch on `response.status`, not on the HTTP code:

```python
if response.status == "completed":
    ...
elif response.status == "incomplete":
    ...  # incomplete_details.reason == "max_output_tokens" ~ finish_reason "length"
elif response.status in ("failed", "cancelled"):
    raise RuntimeError(response.error)
```

`status` enum: `completed | failed | incomplete | in_progress | queued | cancelled`.
`incomplete` plus `incomplete_details.reason: "max_output_tokens"` replaces Sonar's `finish_reason: "length"` - raise `max_output_tokens` or handle truncation.

## Background / async runs

- `background: true` with `stream: false` returns immediately with `status: "queued"`; poll `GET /v1/responses/{id}` and branch on `status` (remember 200-wrapped failures above).
- A GET of an `in_progress` run returns `output: []`.
  Partials are only available via SSE reconnect: `GET /v1/responses/{id}?stream=true&starting_after=<sequence_number>`.
  On a 400 cursor-expired error, fall back to a plain GET.
- There is no documented cancel endpoint for background runs today; do not promise background cancellation.
