# agent-demo-app (Perplexity SDK edition)

The same demo app as `../raw-http`, built on the official Perplexity Python SDK and the Agent API (`client.responses.create`).

## Scripts

| Script | What it does | Agent API features it uses |
|---|---|---|
| `trend_report.py` | Grounded tech-trend summary with numbered sources | `model="perplexity/sonar"`, `client.responses.create`, `max_output_tokens`, `tools=[{"type": "web_search", "filters": {...}}]` for recency/domain filtering, a prompt-delimiter recipe for related questions, reads `response.output_text` and the `search_results` output item |
| `ask_stream.py` | Streams an answer token by token | `stream=True`, typed SSE events (`response.output_text.delta`, and all terminal events) |
| `extract_stats.py` | Structured company snapshot as JSON | `response_format` with `json_schema`, `tools=[{"type": "web_search"}]`, parses `response.output_text` |

## Setup and run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export PERPLEXITY_API_KEY="pplx-..."
.venv/bin/python trend_report.py "solid state batteries"
.venv/bin/python ask_stream.py "Why is the sky blue?"
.venv/bin/python extract_stats.py "Nvidia"
```
