# Search reference

Read this when composing `pplx_srch_sdk.search.web` queries or filters.

## Call shape

```python
import pplx_srch_sdk

hits = pplx_srch_sdk.search.web(
    "python 3.13 release notes",
    limit=10,
    domains=["docs.python.org"],
    excluded_domains=["dev.to"],
    country="US",
)
```

Returns a bare `list[WebHit]`.

## Kwargs

| Kwarg | Type | Meaning |
|---|---|---|
| `queries` (positional) | `str` or `list[str]` | The query, or up to 10 reformulation variants of one query (see below) |
| `reformulations` | `list[str]` | Alternate reformulations when the positional is a single string |
| `intent` | `str` | One short sentence stating what the search should find or verify; does not change which pages are found, but sharpens which text comes back for each hit |
| `limit` | `int` | Maximum total results for the whole request (default 10 per query; the server silently clamps oversized values instead of rejecting them) |
| `country` | `str` | Country code, such as `"US"` |
| `domains` | `list[str]` | Only these domains; always a list, even for one domain |
| `excluded_domains` | `list[str]` | Drop these domains |
| `published_after_date` / `published_before_date` | `str` | Publication-date bounds, MM/DD/YYYY |
| `updated_after_date` / `updated_before_date` | `str` | Last-updated bounds, MM/DD/YYYY |
| `recency_filter` | `str` | Relative window: `"hour"`, `"day"`, `"week"`, `"month"`, `"year"` |
| `max_tokens` / `max_tokens_per_page` | `int` | Response token budgets, total and per page |
| `search_context_size` | `str` | `"low"`, `"medium"`, `"high"`; omit when passing explicit token budgets |

## Query style

- Short keyword phrases, usually 2-5 meaningful words, one topic per query: `"inflation rate Canada"`, not `"What is the inflation rate in Canada?"`.
- No quote marks, exact-phrase syntax, `site:`, or boolean `AND`/`OR`/`NOT` - the engine treats them as literal words; use `domains` / `excluded_domains` kwargs instead.
- Multi-entity questions become separate single-entity queries (`"Brand A protein powder review"` and `"Brand B protein powder review"`), fanned out via `web_many`.
- On non-trivial searches, add `intent=` - one short sentence on what to find or verify; it sharpens the returned text for each hit without changing which pages are found.
- For time-sensitive topics, put the explicit date in the query text (`"CPI report March 2026"`); reserve the date kwargs for requests that explicitly bound the result window.

## Query variants vs independent queries

A list as the first argument sends ONE request whose extra strings are reformulations of the same question; the return is a single merged `list[WebHit]`:

```python
hits = pplx_srch_sdk.search.web([
    "python 3.13 release notes",
    "python 3.13 whats new",
])
```

- At most 10 variants, all rewordings of a single intent - never a batch of different questions.
- `limit` caps the whole merged result set, not each variant, so a small `limit` on many variants defeats the reformulation; omit it and the default scales with the variant count.
- Looking up several different things = `web_many([...], limit_per_query=...)`, one independent search each. See [fanout.md](fanout.md).

## Date and recency filters

- Explicit bounds are MM/DD/YYYY strings such as `"3/1/2025"`; padding is optional. Use a pair to bound a range or a single side for an open cutoff.
- The publication-date range and the last-updated range can be combined.
- `recency_filter` can combine with the last-updated range but NOT with `published_after_date`/`published_before_date` - the server rejects that combination.

```python
hits = pplx_srch_sdk.search.web(
    "transformer architecture attention mechanism",
    published_after_date="3/1/2025",
    published_before_date="3/5/2025",
)
```

## WebHit shape

Each hit has `{url, title, domain, snippet, date?, last_updated?}`.

- `snippet` is always a string and is the text field for the hit; empty string when no text is available.
- `date` is the publication date; `last_updated` is the last-modified date. Both optional; missing fields read as `None`.
- Hits support attribute reads (`hit.url`), mapping access (`hit["url"]`, `{**hit}`, `hit.get("date")`, `hit.keys()`), and `dict(hit)` / `hit.to_dict()` for JSON-serializable rows. The mapping view contains only populated fields.
