# sonar-demo-app

A small demo app built on the Perplexity Agent API (`/v1/agent`).

## Scripts

| Script | What it does | Agent API features it uses |
|---|---|---|
| `trend_report.py` | Grounded tech-trend summary with numbered sources | `perplexity/sonar` + `web_search` tool, system+user `input` items, `max_output_tokens`, `tools[web_search].filters.search_recency_filter` + `search_domain_filter`, related-questions prompt recipe, reads `output[]` `message`/`search_results` items |
| `ask_stream.py` | Streams an answer token by token | `stream: true`, typed SSE events (`response.output_text.delta`, `response.completed`, ...) |
| `extract_stats.py` | Structured company snapshot as JSON | `response_format` with `json_schema`, `web_search` tool, parses `output[]` `message` item |

Note: `return_related_questions` has no Agent API equivalent, so `trend_report.py` uses the prompt-delimiter recipe (asks the model to end its answer with a "Related questions:" section, then splits on that marker) instead of a dedicated field.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export PERPLEXITY_API_KEY="pplx-..."
```

## Run

```bash
.venv/bin/python trend_report.py "quantum computing"
.venv/bin/python ask_stream.py "Why is the sky blue?"
.venv/bin/python extract_stats.py "Nvidia"
```
