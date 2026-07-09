# Model and preset mapping: Sonar -> Agent API

Read this when choosing a target model or preset for a migrated call site.

## Valid model slugs

`GET https://api.perplexity.ai/v1/models` (no auth required) is authoritative - always verify slugs there before writing them into code.
Agent API slugs are provider-prefixed, e.g. `perplexity/sonar`, `openai/gpt-5.1`, `anthropic/claude-sonnet-4-5`, `google/gemini-3-flash-preview`.
Do not invent slugs: there is NO `perplexity/sonar-pro` slug.

## Model mapping table

| Sonar model | Migrate to | Rationale and caveats |
|---|---|---|
| `sonar` | `model: "perplexity/sonar"` + `tools: [{"type": "web_search"}]`, or `preset: "fast"` | Closest by name. CAUTION: output is not byte-identical to chat `sonar` and pricing differs (see the public pricing page) - A/B compare quality and cost before cutover. |
| `sonar-pro` | Two options - pick per the heuristic below | Option 1, behavioral match: `preset: "low"` (pro-search, multi-step search). Option 2, lighter direct substitution: `model: "perplexity/sonar"` + web_search. |
| `sonar-reasoning` | `preset: "low"`, or a reasoning model (e.g. `openai/gpt-5.1` + `reasoning: {"effort": "medium"}` + web_search) | Retired; do not carry the name forward. Note the substitution in your migration notes. |
| `sonar-reasoning-pro` | `preset: "low"` (closest), or a reasoning model + `reasoning: {"effort": "medium"}` + web_search + a generously sized `max_output_tokens` | `medium` is a strictly heavier, costlier tier - offer it only as an explicit upgrade. |
| `sonar-deep-research` | `preset: "medium"` (deep-research) | The medium (deep-research) preset is the closest published equivalent of sonar-deep-research. `high` is a costlier upgrade, not an equivalent; offer it only as an explicit upsell note. |

### The sonar-pro two-option rule

- **Option 1 - behavioral match: `preset: "low"`.**
  Caveats to state inline in migration notes: `preset` is a separate request field, not a model slug; it may resolve to a third-party model (`response.model` can echo e.g. a `google/*` model); higher latency and cost per call; via the OpenAI SDK pass `extra_body={"preset": "low"}` and omit `model`.
- **Option 2 - lighter substitution: `model: "perplexity/sonar"` + `tools: [{"type": "web_search"}]`.**
  Required when the code's contract is a model slug: a `--model` CLI flag, a model allowlist, or a framework model-class bridge that takes a model string (presets do not fit there).
  Also preferred for lightweight or high-frequency call sites where pro-search depth is not the point.

Selection heuristic: model-slug contract -> option 2; hardcoded single model where search depth matters -> option 1; otherwise either, but document the substitution.

**Preset plus search filters:** per the presets documentation, a tool you list in the request overrides only the preset's tool of the same type; the preset's other tools stay enabled.
When the flow needs guaranteed `search_domain_filter` / recency / date filters, the simplest setup to reason about is still option 2 - an explicit model plus a `web_search` tool carrying `filters` - because nothing else is bundled alongside it.

## Preset mechanics

Know these before using presets:

- Short names `fast | low | medium | high | xhigh` are the canonical preset names; `fast-search | pro-search | deep-research | advanced-deep-research` are accepted as previous names for the first four.
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
