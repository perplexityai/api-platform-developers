// Perplexity Agent API via the Vercel AI SDK (@ai-sdk/open-responses).
//
// Pinned, verified-compatible versions:
//   ai@7.0.93
//   @ai-sdk/open-responses@2.0.39
//
// This path is INDEPENDENT of models.dev: the model id is passed explicitly to
// the provider factory and sent straight through to Perplexity's
// Open-Responses-compatible endpoint. No provider registry or models.dev
// lookup is involved at runtime.
//
// Setup:
//   npm install ai@7.0.93 @ai-sdk/open-responses@2.0.39
//   export PERPLEXITY_API_KEY="your_key"
//
// Run:
//   node agent-api-openresponses.mjs

import { createOpenResponses } from "@ai-sdk/open-responses";
import { generateText } from "ai";

// createOpenResponses points directly at Perplexity's OpenAI-Responses-
// compatible endpoint. /v1/responses is the OpenAI-compatible alias of the
// canonical /v1/agent endpoint — both reach the Agent API. Pin the package
// version (above) so a registry/protocol change can't silently break you.
const perplexity = createOpenResponses({
  name: "perplexity",
  url: "https://api.perplexity.ai/v1/responses",
  apiKey: process.env.PERPLEXITY_API_KEY,
});

// Explicit model id routed through a single Perplexity key. Any Agent API
// model works here (openai/*, anthropic/*, google/*, xai/*, ...). The string
// is passed through to the API verbatim — it is NOT resolved via models.dev.
const MODEL = "openai/gpt-5.6-sol";

// Sources (citations) live as a `search_results` item in the response `output`
// array. @ai-sdk/open-responses does not surface them on the result object, so
// capture them in a fetch hook.
let sources = [];

const { text, response, usage } = await generateText({
  model: perplexity(MODEL),
  prompt: "What are the latest breakthroughs in fusion energy this year?",

  // Grounded web search is NOT automatic on the Agent API. Add the built-in
  // `web_search` tool to the request body via a fetch hook — the AI SDK has no
  // first-class option for Perplexity's hosted tool types.
  fetch: async (url, options) => {
    const body = JSON.parse(options.body);
    body.tools = [{ type: "web_search" }];
    const res = await fetch(url, { ...options, body: JSON.stringify(body) });

    // Read sources from the raw output array (skip for streaming, where the
    // body is an event stream rather than JSON).
    if (!body.stream) {
      const raw = await res.clone().json();
      // 200-wrapped failures: failed/cancelled runs return HTTP 200 with a
      // populated `status` and `error`. Branch on status, not the HTTP code.
      if (raw.status && raw.status !== "completed") {
        throw new Error(
          `run ended with status ${raw.status}: ` +
            JSON.stringify(raw.error ?? raw.incomplete_details),
        );
      }
      sources =
        raw.output
          ?.filter((i) => i.type === "search_results")
          .flatMap((i) => i.results) ?? [];
    }
    return res;
  },
});

console.log("STATUS:", response.status);
console.log("TEXT:", text);
console.log("USAGE:", JSON.stringify(usage));
console.log("SOURCES:");
for (const s of sources) {
  console.log(`  ${s.title} — ${s.url}`);
}
