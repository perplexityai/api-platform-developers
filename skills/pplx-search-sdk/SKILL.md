---
name: pplx-search-sdk
description: "Install and use pplx-srch-sdk, Perplexity's public Python Search SDK (import pplx_srch_sdk), for live web search and query-relevant page snippets from Python code. Use to search the web from a script or notebook, fan many searches out concurrently, get query-relevant excerpts from specific URLs, build multi-step research pipelines, or handle Perplexity Search API errors with typed exceptions."
when_to_use: "Any request like: search the web from Python, use the Perplexity Python SDK, pip install pplx-srch-sdk, import pplx_srch_sdk, run many web searches in parallel, fan out search queries, get query-relevant excerpts from URLs in code, batch web research in a script, async Perplexity search client, handle Perplexity search rate limits in code."
argument-hint: "[search query or URLs]"
---

# pplx_srch_sdk - Perplexity's Python Search SDK

## What this skill does

Installs and drives `pplx-srch-sdk`, Perplexity's public Python SDK for the Search API: `pplx_srch_sdk.search.web` for live web search, `pplx_srch_sdk.search.web_many` for concurrent fan-out over many queries, `pplx_srch_sdk.content.snippets` for query-relevant page excerpts.
The sync facade covers most work; `pplx_srch_sdk.AsyncPplxClient` exposes the same surface async.

## Install and auth

```sh
pip install pplx-srch-sdk
```

Python >= 3.12 on Linux (x86_64, aarch64) and macOS. Package and import share the name: `pip install pplx-srch-sdk`, then `import pplx_srch_sdk`.
Get an API key at https://www.perplexity.ai/account/api and export it:

```sh
export PERPLEXITY_API_KEY=pplx-...
```

Import succeeds without a key; the first sync-facade request raises `AuthenticationError: [401] No API key configured. Set the PERPLEXITY_API_KEY environment variable`, and `AsyncPplxClient()` raises the same error at construction (pitfall 9).

## Web search

```python
import pplx_srch_sdk

hits = pplx_srch_sdk.search.web(
    "rust async runtimes",
    limit=5,
    intent="Compare the maintained Rust async runtimes and their trade-offs",
)
for hit in hits:
    print(hit.title, hit.url)
```

`search.web` returns a bare `list[WebHit]` - no `.results` wrapper, no response envelope (pitfall 1).
Pass `intent` - one short sentence stating what the search should find or verify; it documents the objective and does not change which pages are found.
Keep queries short keyword phrases, usually 2-5 meaningful words, one topic per query; no quote marks, `site:`, or boolean `AND`/`OR` - use kwargs like `domains=[...]` and `excluded_domains=[...]` instead.
Break multi-entity questions into separate single-entity queries and send them through `web_many`, not one long combined query.
A list passed as the first argument is reformulations of ONE query, up to 10, merged into a single result list (pitfall 2).
Full kwarg table (domains, country, date bounds, `recency_filter`, token budgets): [references/search.md](references/search.md).

## Fan-out (many independent queries)

```python
results = pplx_srch_sdk.search.web_many(
    [
        "yellowstone national park visitor numbers 2025",
        "zion national park entrance fee 2026",
        "acadia national park camping reservations",
    ],
    limit_per_query=10,
)
for r in results:
    if r.ok:
        print(r.spec["query"], "->", len(r.result), "hits")
    else:
        print(r.spec["query"], "failed:", r.error)
```

`web_many` runs one independent search per query with bounded concurrency (default 5) and returns one `FanoutResult` per query, in input order.
Read `r.ok` / `r.spec` / `r.result` / `r.error` (pitfall 3); one failed query does not fail the batch.
Queries can be plain strings or per-query kwargs dicts (`{"query": ..., "domains": [...]}`); extra kwargs on the call apply to every query.
Mechanics plus the `pplx_srch_sdk.utils` helpers (partition, flatten, dedup, JSONL artifacts): [references/fanout.md](references/fanout.md).

## Snippets

```python
snips = pplx_srch_sdk.content.snippets(
    query="what's new in python 3.13",
    urls=[
        "https://docs.python.org/3/whatsnew/3.13.html",
        "https://example.com/missing",
    ],
)
for s in snips:
    print(s.url, s.error or (s.text or "")[:200])
```

One `SnippetResult` per input URL, in input order.
**Check `error` on every result before trusting `text`** - a successful call can still carry per-URL failures (pitfall 4).
Use `text`, not `content` or `summary`; elided regions inside `text` are marked with `…`.
Token budgets and URL limits: [references/content.md](references/content.md).

## Result shapes

- `search.web(...)` -> `list[WebHit]`; each hit has `{url, title, domain, snippet, date?, last_updated?}`. `snippet` is the text field for the hit and is an empty string when no text is available; `date` is the publication date and `last_updated` the last-modified date. Ignore `summary` - the SDK folds any longer context into `snippet` and clears it.
- Typed records support attribute reads (`hit.url`), mapping access (`hit["url"]`, `{**hit}`, `hit.keys()`), and `dict(hit)` / `hit.to_dict()` for JSON-serializable rows. Missing optional fields read as `None`; the mapping view contains only populated fields.
- `search.web_many(...)` -> `list[FanoutResult]`; each exposes `.ok` (success flag), `.spec` (the request kwargs), `.result` (the `list[WebHit]` on success), `.error` (the isolated exception). There is no `.request` attribute.
- `content.snippets(...)` -> `list[SnippetResult]`; each has `{url, text?, tokens_count?, error?}`.

## Errors

Every SDK exception derives from `pplx_srch_sdk.PplxSdkError`; API failures raise subclasses of `pplx_srch_sdk.APIError`: `AuthenticationError` (401), `ForbiddenError` (403), `NotFoundError` (404), `NotAcceptableError` (406), `RateLimitError` (429), `BadRequestError` and `ValidationError` (400), `InternalServerError` (5xx), `ConnectError` (network failure).

```python
try:
    hits = pplx_srch_sdk.search.web("query", limit=5)
except pplx_srch_sdk.RateLimitError:
    ...  # back off, then retry
except pplx_srch_sdk.APIError as e:
    print(e)  # message starts with the HTTP status, e.g. "[400] ..."
```

Inside `web_many`, per-query API errors land on `FanoutResult.error` instead of raising; a missing API key still raises `AuthenticationError` immediately, before any query is dispatched.

## Async

```python
import asyncio
import pplx_srch_sdk


async def main():
    async with pplx_srch_sdk.AsyncPplxClient() as client:
        hits = await client.search.web("python 3.13 release notes", limit=10)
        print(len(hits), hits[0].url)


asyncio.run(main())
```

Drop to `AsyncPplxClient` for a custom concurrency model or long-lived concurrent state; there is no async `web_many` - use `pplx_srch_sdk.utils.fanout` with `client.search.web` (see [references/async.md](references/async.md)).
Reuse one client per script (pitfall 7).

## Top pitfalls

1. **`search.web` returns a bare `list[WebHit]`.** There is no `.results` wrapper or response envelope: `hits[0].url` works directly, `hits.results` is an `AttributeError`.
2. **A list passed to `web()` is reformulations of ONE query, not a batch.** Up to 10 variants merge into a single result list, and `limit` caps that whole merged set, not each variant. N distinct questions = `web_many` with `limit_per_query`.
3. **`FanoutResult` exposes `spec`/`result`/`error`/`ok`.** `r.result` is the hit list and `r.spec` the request kwargs; there is no `.request` attribute. Always branch on `r.ok` - per-query failures ride the batch as `r.error`, they do not raise.
4. **A successful `content.snippets` call does not mean every URL succeeded.** Per-URL failures set `results[i].error` and leave `text` unset; check `error` on each result before using `text`.
5. **`recency_filter` cannot combine with the publication-date range.** The server rejects `recency_filter` together with `published_after_date`/`published_before_date` - a wasted round trip, not caught client-side.
6. **Date filter kwargs use MM/DD/YYYY strings, not ISO dates** (e.g. `published_after_date="7/1/2026"`); padding is optional.
7. **Do not construct one `AsyncPplxClient` per coroutine inside `asyncio.gather`.** That leaks connections - reuse one client, or stay on `web_many` / `pplx_srch_sdk.utils.fanout`.
8. **A conflicting `limit` alongside `limit_per_query` on `web_many` raises `TypeError`.** Equal values are accepted but redundant; prefer `limit_per_query` alone, which forwards as `limit=` to each single search.
9. **A missing key fails at call time, not import time.** `import pplx_srch_sdk` succeeds without `PERPLEXITY_API_KEY`; the first sync-facade call raises `AuthenticationError` with a `[401]` message, and `AsyncPplxClient()` raises the same error eagerly at construction - wrap client creation, not just the awaited calls (as [examples/async_client.py](examples/async_client.py) does).

## Reference index

- [references/search.md](references/search.md) - read when composing queries or filters: full `search.web` kwarg table, query-style rules, date filters, `WebHit` shape.
- [references/fanout.md](references/fanout.md) - read when running many queries: `web_many` mechanics, `FanoutResult` handling, `pplx_srch_sdk.utils` helpers for artifacts and dedup.
- [references/content.md](references/content.md) - read when excerpting known URLs: `content.snippets` token budgets, per-URL error handling.
- [references/async.md](references/async.md) - read when using `AsyncPplxClient` or `pplx_srch_sdk.utils.fanout` directly.

Runnable examples (each needs `PERPLEXITY_API_KEY` exported):

- [examples/web_search.py](examples/web_search.py) - one-off web search with filters and typed error handling.
- [examples/fanout_research.py](examples/fanout_research.py) - fan out queries, split successes from errors, dedup, write JSONL artifacts.
- [examples/snippets_verify.py](examples/snippets_verify.py) - search, then verify hits with query-relevant snippets.
- [examples/async_client.py](examples/async_client.py) - async client with bounded custom fan-out.
