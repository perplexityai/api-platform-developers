# Perplexity Agent API with the Vercel AI SDK (`@ai-sdk/open-responses`)

A runnable, copy-paste example that reaches the Perplexity [Agent API](https://docs.perplexity.ai/docs/agent-api/quickstart) from a Vercel AI SDK app through the [`@ai-sdk/open-responses`](https://ai-sdk.dev/providers/ai-sdk-providers/open-responses) provider — pinned to a verified-compatible version and independent of [models.dev](https://models.dev).

This is the Vercel AI SDK integration style for the Sonar → Agent API migration. See the parent [migration skill](../SKILL.md) for the full field-by-field procedure and the other integration styles (raw HTTP, OpenAI SDK, Perplexity SDK, framework bridges).

## Why this exists

The live docs page ([Perplexity with the Vercel AI SDK](https://docs.perplexity.ai/docs/getting-started/integrations/vercel-ai-sdk)) shows the provider setup but ships no standalone, runnable file and does not call out two things that bite people in production:

1. **Version pinning.** The `ai` and `@ai-sdk/open-responses` packages move fast. A floating install can pull a release that changes the provider protocol or the `createOpenResponses` signature. Pin both packages to a verified-compatible pair.
2. **No models.dev dependency.** `@ai-sdk/open-responses` does not use the models.dev registry at runtime — the model id you pass to the provider factory (`perplexity("openai/gpt-5.6-sol")`) is sent straight through to Perplexity's `/v1/responses` endpoint. This example makes that explicit so the Agent API path keeps working even if a registry you don't control changes.

## Verified versions

| Package | Pinned version | Notes |
|---|---|---|
| `ai` | `7.0.93` | Core AI SDK (`generateText`, `streamText`). |
| `@ai-sdk/open-responses` | `2.0.39` | Open Responses provider; talks to any Open-Responses-compatible `POST` endpoint. |

These two install and run together on Node 20+ (the packages declare `node>=22`; Node 20 works but emits an engine warning). Live-tested against `https://api.perplexity.ai/v1/responses` — the path resolves and returns a clean HTTP 401 without a key (i.e. it reaches the Agent API; no transport/DNS/registry failure).

## Setup

```bash
npm install ai@7.0.93 @ai-sdk/open-responses@2.0.39
export PERPLEXITY_API_KEY="your_api_key_here"
```

## Run

```bash
node agent-api-openresponses.mjs
```

Expected output (with a valid key):

```
STATUS: completed
TEXT: <answer text grounded in current web search results>
USAGE: {...}
SOURCES:
  <title> — <url>
  ...
```

## How it maps to the Agent API contract

| Agent API field | Where it lives in this example |
|---|---|
| `POST /v1/responses` (alias of `/v1/agent`) | `createOpenResponses({ url: "https://api.perplexity.ai/v1/responses" })` |
| `model` | `perplexity("openai/gpt-5.6-sol")` — passed through verbatim, not resolved via models.dev |
| `input` | the `prompt:` argument to `generateText` |
| `tools: [{ type: "web_search" }]` | injected in the `fetch` hook (the AI SDK has no first-class option for Perplexity's hosted tool types) |
| `output[]` walk / `output_text` | `text` from `generateText` |
| `search_results` item (citations) | read from the raw `output` array in the `fetch` hook — the provider does not surface sources on the result |
| `status` branching (200-wrapped failures) | the `fetch` hook throws if `raw.status !== "completed"` |

## Using a preset instead of a raw model

A preset bundles `web_search` (and reasoning, code execution, etc.), so you drop the `tools` injection and pass the preset in the body. The Open Responses provider has no preset option, so it also rides through the `fetch` hook:

```js
fetch: async (url, options) => {
  const body = JSON.parse(options.body);
  body.preset = "fast"; // fast | low | medium | high | xhigh
  delete body.model;     // presets resolve to their own model; omit `model`
  return fetch(url, { ...options, body: JSON.stringify(body) });
},
```

Presets map from the old Sonar models: `sonar` → `fast`, `sonar-pro` → `low`, `sonar-reasoning-pro` → `medium`, `sonar-deep-research` → `high`. See [models-and-presets.md](../references/models-and-presets.md) for the full table.

## Streaming

```js
import { streamText } from "ai";

const result = streamText({
  model: perplexity("openai/gpt-5.6-sol"),
  prompt: "What are the latest breakthroughs in fusion energy this year?",
  // reuse the same fetch hook that adds web_search
});

for await (const chunk of result.textStream) {
  process.stdout.write(chunk);
}
```

The source-reading logic in the `fetch` hook is skipped for streaming (the body is an event stream, not JSON). To get sources on a streaming run, read the final `response.completed` event's `output` array, or use a non-streaming call alongside it.

## What this does NOT depend on

- **models.dev.** The model id string is passed straight to the API. No registry lookup, no models.dev fetch at runtime. The Agent API path keeps working regardless of models.dev availability.
- **A specific bundler/framework.** The example is plain ESM and runs under `node`. Drop the same `createOpenResponses` block into a Next.js Route Handler, Server Action, or API route — create the provider on the server so `PERPLEXITY_API_KEY` never reaches the browser.

## Live-test evidence

Captured against production with no API key (proves the path resolves, not just that it compiles):

```
$ node agent-api-openresponses.mjs
REACHED_API_BUT_UNAUTHORIZED: AI_APICallError: Unauthorized
```

A clean HTTP 401 from `api.perplexity.ai/v1/responses` — not a transport, DNS, or registry error. With a valid key the run returns `status: completed`, answer text, and a populated `search_results` array.
