# Content snippets reference

Read this when excerpting known URLs with `pplx_sdk.content.snippets`.

## Call shape

```python
import pplx_sdk

snips = pplx_sdk.content.snippets(
    query="rust async runtimes comparison",
    urls=["https://example.com/a", "https://example.com/b"],
    max_tokens=4096,
    max_tokens_per_page=1024,
)
```

Returns `list[SnippetResult]`, one per input URL, in input order.

## When to use

- Search-result text does not disambiguate a specific claim and you need focused evidence from known pages.
- Verifying candidates against stated criteria in one batched pass (pass all candidate URLs at once, not one call per URL).
- Excerpting what specific pages say about a query without pulling whole pages into context.

## Arguments

- `query` - the question the excerpts should be relevant to. One query per call; different questions need separate calls.
- `urls` - 1-50 http(s) URLs. Extra URLs are more pages to excerpt, never query rephrasings.
- `max_tokens` - total budget across all snippets, 1-16384, default 4096.
- `max_tokens_per_page` - budget per page, 1-4096, must be <= `max_tokens`, default `min(1024, max_tokens)`.

## SnippetResult shape

`{url, text?, tokens_count?, error?}`.

- Use `text`, not `content` or `summary`; missing fields read as `None`.
- Elided regions inside `text` are marked with `…`.
- **A successful call does not mean every URL succeeded.** Per-URL failures set `error` on that result and leave `text` unset - check `error` on each result before using `text`:

```python
for s in snips:
    if s.error:
        print("failed:", s.url, s.error)
        continue
    use(s.text)
```

Mapping access works the same as on hits: `s["url"]`, `dict(s)`, `s.to_dict()`; the mapping view contains only populated fields.

## Fanning out over large URL pools

For more than 50 URLs, or several different queries, chunk the URLs and dispatch with `pplx_sdk.utils.fanout` over the async client - see [async.md](async.md) for the exact pattern.
