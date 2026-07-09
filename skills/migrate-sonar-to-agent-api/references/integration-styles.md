# Integration styles: raw HTTP, SDKs, and framework bridges

Read this when the code uses the OpenAI SDK, the Perplexity SDK, LangChain, LlamaIndex, or the OpenAI Agents SDK.
Rule: keep the existing integration style; migrate the contract, not the stack.

## Raw HTTP

Canonical request:

```bash
curl -s https://api.perplexity.ai/v1/agent \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "perplexity/sonar",
    "input": "What happened in AI this week?",
    "tools": [{"type": "web_search"}],
    "max_output_tokens": 512
  }'
```

Canonical response handling (Python `requests`):

```python
import os
import requests

resp = requests.post(
    "https://api.perplexity.ai/v1/agent",
    headers={"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"},
    json={
        "model": "perplexity/sonar",
        "input": "What happened in AI this week?",
        "tools": [{"type": "web_search"}],
        "max_output_tokens": 512,
    },
)
resp.raise_for_status()
data = resp.json()
if data["status"] != "completed":
    raise RuntimeError(data.get("error") or data.get("incomplete_details"))
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

## OpenAI SDK pointed at Perplexity

- `base_url` MUST be `https://api.perplexity.ai/v1` - the trailing `/v1` is required; the SDK appends `/responses` to it.
- Switch `client.chat.completions.create()` to `client.responses.create()`.
- Floor: `responses.create` requires a recent OpenAI SDK; `openai>=1.66` for Python.
- Perplexity-only fields go through `extra_body` in Python (or a type cast in TypeScript): `preset`, `max_steps`, `response_format`, `language_preference`, Perplexity tool types.
- Preset via the OpenAI SDK: pass `extra_body={"preset": "low"}` and OMIT `model`.
- Structured-output trap: do NOT use OpenAI's `text={"format": ...}` spelling - the API rejects it (400 unknown field "format").
  Send top-level `response_format` via `extra_body`.
- Perplexity-only output items (such as `search_results`) deserialize as raw dicts, not typed objects: iterate `response.output` and use `item.get("url")`-style dict access, not attribute access.
  Prefer `response.output_text` for the plain-text case.
  Avoid `model_dump()` on responses containing such items - it emits serialization warnings.

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["PERPLEXITY_API_KEY"],
    base_url="https://api.perplexity.ai/v1",
)
response = client.responses.create(
    model="perplexity/sonar",
    input="What happened in AI this week?",
    tools=[{"type": "web_search"}],
    max_output_tokens=512,
)
print(response.output_text)
sources = next(
    (item for item in response.output
     if isinstance(item, dict) and item.get("type") == "search_results"),
    None,
)
```

TypeScript (Node SDK): Perplexity-only fields ride behind a params cast, and 200-wrapped failures still need the `response.status` branch:

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.PERPLEXITY_API_KEY,
  baseURL: "https://api.perplexity.ai/v1",
});

const response = await client.responses.create({
  model: "perplexity/sonar",
  input: "Extract key facts about Perplexity AI as JSON.",
  max_output_tokens: 512,
  // Perplexity-only field: TOP-LEVEL response_format (never text.format).
  // The OpenAI types do not know it, hence the cast.
  response_format: {
    type: "json_schema",
    json_schema: { name: "company_facts", schema: { /* your JSON schema */ } },
  },
} as any);

// Failed/cancelled runs resolve normally with HTTP 200 - always branch on response.status.
if (response.status !== "completed") {
  throw new Error(
    `run ended with status ${response.status}: ` +
    JSON.stringify(response.error ?? response.incomplete_details),
  );
}
console.log(response.output_text); // exists on the Node SDK Response
```

## Perplexity SDK

- Install: `pip install perplexityai` / `npm install @perplexity-ai/perplexity_ai`.
- Switch `client.chat.completions.create()` to `client.responses.create()`.
- Same client construction, same `PERPLEXITY_API_KEY` env var.
- TYPED-KWARG TRAP: the SDK's `responses.create()` typed parameters can lag the live API surface.
  A parameter the API accepts (for example `temperature`) may raise `TypeError: ResponsesResource.create() got an unexpected keyword argument` from the SDK.
  Pass such parameters through `extra_body={"temperature": 0.2}` instead of dropping them, and always live-run the result - a clean compile does not catch this.

```python
from perplexity import Perplexity

client = Perplexity()  # reads PERPLEXITY_API_KEY
response = client.responses.create(
    model="perplexity/sonar",
    input="What happened in AI this week?",
    tools=[{"type": "web_search"}],
)
print(response.output_text)
```

## Framework bridges

First, verify which client actually calls Perplexity.
The Perplexity call may live OUTSIDE the framework as a sibling SDK client (for example, a framework driving one provider's model while a separate OpenAI-SDK client hits `api.perplexity.ai`).
Migrate the call site that hits `api.perplexity.ai` by its own style; leave framework-internal LLMs pointed at other providers untouched.

### 1. OpenAI Agents SDK

- Class swap: `agents.OpenAIChatCompletionsModel` -> `agents.OpenAIResponsesModel` (both are top-level `agents` exports), with the client `AsyncOpenAI(base_url="https://api.perplexity.ai/v1", api_key=...)`.
- Model-class bridges take a model STRING, so use `perplexity/sonar` - presets do not fit here.
- `@function_tool` registers client-side Python functions only; Perplexity hosted tools (web_search) are not reachable through it.
  Grounded search needs a direct `responses.create` call or a preset outside the agent loop.
- Caution: the SDK may attach Responses-only fields the strict API rejects (for example `text.format` when `output_type` is set) - smoke-test the real framework request, not just a bare `responses.create` call.

### 2. LangChain `ChatPerplexity` / LlamaIndex Perplexity LLM

These wrap chat completions internally; do not rewrite the framework's internals.
Options, in order of preference:

1. If the framework has an OpenAI-Responses-compatible client, point it at `https://api.perplexity.ai/v1` and use responses mode.
2. Keep the bridge on chat completions (still supported) and add a note that Agent API migration is pending framework support.
3. Replace only the Perplexity call site with a direct SDK `responses.create()` call when the framework usage is superficial.

Whichever you pick, state the choice explicitly in your migration notes.

## Function calling and tools

- Custom function shape: `{"type": "function", "name": ..., "description": ..., "parameters": {...}, "strict": true}`.
  Name and description live at the tool's top level (Responses style), NOT nested under `function` as in chat completions.
- RESERVED NAMES: custom function names colliding with built-in tool names are rejected with a 400: `web_search`, `search_web`, `people_search`, `search_people`, `fetch_url`, `finance_search`, `sandbox`.
  Other names may also be reserved; if a custom tool name 400s, rename it.
  Sonar allowed shadowing - rename such tools during migration (e.g. `web_search` -> `my_web_search`).
- The model returns a `function_call` output item (`call_id`, `name`, `arguments` JSON string).
  Reply on the next request with a `function_call_output` input item: `{"type": "function_call_output", "call_id": ..., "output": ...}`.
  Echo `name` and `thought_signature` if present on the call - some models require them on the round-trip.
- `tool_choice`: string `"none" | "auto" | "required"`, or objects: `{"name": "my_fn"}`, `{"type": "web_search"}` (forces that built-in), `{"type": "required"}`.
- `max_tool_calls: 0` disables tool calls entirely - the closest analog of `disable_search` when a preset forces tools you cannot remove (note: it disables ALL tools).
- Built-in tools, one line each:
  - `web_search` - grounded search; filters per [request-mapping.md](request-mapping.md); `max_results` <= 50.
  - `fetch_url` - fetch pages; `max_urls` 1..10; `total_budget_tokens` <= 120000.
  - `people_search` - professional profiles; bills as `search_people`.
  - `finance_search` - quotes, fundamentals, filings; replaces `search_mode: "sec"`.
  - `sandbox` - stateful Linux sandbox for code execution; drops other native tools when combined.
  - `mcp` - `server_label` (`[a-zA-Z0-9_-]{1,64}`, unique) plus an HTTPS `server_url`; max 16 servers; no approval flow; an unreachable server returns 424 `external_connector_error`; OpenAI passthrough fields like `require_approval` are tolerated.
