# sonar-demo-app (Perplexity SDK edition)

The same demo app as `../raw-http`, built on the official Perplexity Python SDK and the Sonar chat-completions surface.

## Scripts

| Script | What it does | Sonar features it uses |
|---|---|---|
| `trend_report.py` | Grounded tech-trend summary with numbered sources | `sonar-pro`, `client.chat.completions.create`, `max_tokens`, `search_recency_filter` + `search_domain_filter` kwargs, `return_related_questions`, reads `choices[0].message.content`, `completion.citations` and `completion.search_results` |
| `ask_stream.py` | Streams an answer token by token | `stream=True`, `chunk.choices[0].delta.content` |
| `extract_stats.py` | Structured company snapshot as JSON | `response_format` with `json_schema`, parses `choices[0].message.content` |

## Setup and run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export PERPLEXITY_API_KEY="pplx-..."
.venv/bin/python trend_report.py "solid state batteries"
.venv/bin/python ask_stream.py "Why is the sky blue?"
.venv/bin/python extract_stats.py "Nvidia"
```
