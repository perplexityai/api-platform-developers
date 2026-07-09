# sonar-demo-app

A small demo app built on the Perplexity Sonar API (chat completions).

## Scripts

| Script | What it does | Sonar features it uses |
|---|---|---|
| `trend_report.py` | Grounded tech-trend summary with numbered sources | `sonar-pro`, system+user `messages`, `max_tokens`, top-level `search_recency_filter` + `search_domain_filter`, `return_related_questions`, reads `choices[0].message.content`, top-level `citations` and `search_results` |
| `ask_stream.py` | Streams an answer token by token | `stream: true`, `delta.content` chunks, `data: [DONE]` sentinel |
| `extract_stats.py` | Structured company snapshot as JSON | `response_format` with `json_schema`, parses `choices[0].message.content` |

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
