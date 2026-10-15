# Model and preset mapping: Sonar -> Agent API

Read this when choosing a target model or preset for a migrated call site.

## Valid model slugs

Verify slugs against the current [model reference](https://docs.perplexity.ai/docs/agent-api/models) or `GET https://api.perplexity.ai/v1/models` with your API key before writing them into code.
Agent API slugs are provider-prefixed, e.g. `perplexity/sonar` and `openai/gpt-6-luna`.
Check the [changelog](https://docs.perplexity.ai/docs/resources/changelog) for retirement dates when choosing a model.
Do not invent slugs: there is NO `perplexity/sonar-pro` slug.

## Model mapping table

| Sonar model | Migrate to | Rationale and caveats |
|---|---|---|
| `sonar` | `preset: "fast"`, or `model: "perplexity/sonar"` + `tools: [{"type": "web_search"}]` | `fast` is the documented starting point. Output is not byte-identical and pricing differs - A/B compare quality and cost before cutover. |
| `sonar-pro` | Two options - pick per the heuristic below | Option 1, documented starting point: `preset: "fast"`. Option 2, model-slug substitution: `model: "perplexity/sonar"` + web_search. |
| `sonar-reasoning` | `preset: "low"`, or a current reasoning model + web_search | This skill's recommendation for the retired model, not a mapping specified by the migration guide. Verify the model's supported reasoning efforts and note the substitution in your migration notes. |
| `sonar-reasoning-pro` | `preset: "low"`, or a current reasoning model + web_search + a generously sized `max_output_tokens` | `low` is the documented starting point; evaluate heavier presets separately. |
| `sonar-deep-research` | `preset: "high"` | The current migration guide recommends `high` for deep research. |

The [migration guide](https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/how-to) supplies the documented preset starting points above; alternative model choices and the `sonar-reasoning` row are this skill's recommendations. None guarantees equivalent behavior or cost.

### The sonar-pro two-option rule

- **Option 1 - documented starting point: `preset: "fast"`.**
  Caveats to state inline in migration notes: `preset` is a separate request field, not a model slug; it may resolve to a third-party model; compare quality, latency, and cost; via the OpenAI SDK pass `extra_body={"preset": "fast"}` and omit `model`.
- **Option 2 - model-slug substitution: `model: "perplexity/sonar"` + `tools: [{"type": "web_search"}]`.**
  Required when the code's contract is a model slug: a `--model` CLI flag, a model allowlist, or a framework model-class bridge that takes a model string (presets do not fit there).

Selection heuristic: model-slug contract -> option 2; otherwise start with option 1, but document and evaluate the substitution.

**Preset plus search filters:** per the presets documentation, a tool you list in the request overrides only the preset's tool of the same type; the preset's other tools stay enabled.
When the flow needs guaranteed `search_domain_filter` / recency / date filters, the simplest setup to reason about is still option 2 - an explicit model plus a `web_search` tool carrying `filters` - because nothing else is bundled alongside it.

## Preset mechanics

Know these before using presets:

- Short names `fast | low | medium | high | xhigh` are the canonical preset names; `fast-search | pro-search | deep-research | advanced-deep-research | ultra` are their respective previous names.
- Preset models and tool configuration can change; consult the current [preset reference](https://docs.perplexity.ai/docs/agent-api/presets) rather than freezing a model from an old example.
- Any request field set alongside `preset` overrides the preset's value for that field (request-over-preset precedence).
  In particular, set `max_output_tokens` in the request when you need a cap.
- `instructions` alongside a preset REPLACES the preset's system prompt entirely; `""` clears it; omit the field to keep it.
- Preset tools cannot be disabled: `tools: []` does not clear them and there is no public field to disable them.
  `max_tool_calls: 0` is the blunt off-switch, but it disables ALL tools.
- Presets bundle web_search, so grounded answers work without an explicit `tools` array.
- Presets may resolve to third-party models; check `response.model` if branding or data-handling matters.
- `models` fallback list: max 5, tried in order; `response.model` echoes the served one.

## Reasoning effort

`reasoning: {"effort": ...}` enum: `minimal | low | medium | high | xhigh | max`.
On reasoning models and presets, tight `max_output_tokens` caps can be consumed by reasoning tokens before any visible text or search appears - size caps generously or omit them (see the pitfalls list in SKILL.md).
