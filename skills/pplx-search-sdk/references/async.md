# Async reference

Read this when the sync facade is not enough: custom concurrency models, long-lived concurrent state, or fanning out over `content.snippets`.

Use the sync facade (`pplx_srch_sdk.search.*`, `pplx_srch_sdk.content.*`) by default - it handles event-loop and client lifecycle internally.

## AsyncPplxClient

```python
import asyncio

from pplx_srch_sdk import AsyncPplxClient


async def main():
    async with AsyncPplxClient() as client:
        hits = await client.search.web("python release notes", limit=10)
        print(len(hits), hits[0].url)


asyncio.run(main())
```

- Async context manager; `client.search.web` and `client.content.snippets` take exactly the same kwargs and return the same shapes as the sync facade.
- With no key configured, `AsyncPplxClient()` raises `AuthenticationError` at construction, before any request - keep client creation inside your try/except.
- There is no async `web_many` - use `pplx_srch_sdk.utils.fanout` (below) for concurrent dispatch.
- Reuse one client per script. Constructing one client per coroutine inside `asyncio.gather` leaks connections.

## Bounded fan-out with `pplx_srch_sdk.utils.fanout`

`fanout(fn, specs, concurrency=5)` runs `fn(**spec)` for every spec with bounded concurrency and per-call error isolation, returning `list[FanoutResult]` in input order (same envelope as `web_many`, see [fanout.md](fanout.md)).

It works with any async callable - `client.search.web`, `client.content.snippets`, or your own coroutine:

```python
import asyncio

from pplx_srch_sdk import AsyncPplxClient
from pplx_srch_sdk.utils import fanout

QUERY = "board members and advisors"
URLS = [...]  # your candidate URLs
URL_CHUNKS = [URLS[i : i + 20] for i in range(0, len(URLS), 20)]


async def main():
    async with AsyncPplxClient() as client:
        batches = await fanout(
            client.content.snippets,
            [{"query": QUERY, "urls": chunk} for chunk in URL_CHUNKS],
            concurrency=5,
        )
        for r in batches:
            if r.ok:
                print(len(r.spec["urls"]), "->", len(r.result), "snippets")
            else:
                print(r.spec["urls"][0], "failed:", r.error)


asyncio.run(main())
```

Each spec is shallow-copied and echoed back on `FanoutResult.spec`, so provenance survives into artifacts.

## When to drop to async

- A concurrency model the `web_many` / `fanout` defaults do not cover.
- Long-running concurrent state across multiple SDK calls inside one coroutine.
- Mixing `search.web` and `content.snippets` calls in one bounded dispatch.

Otherwise stay on the sync facade - `web_many` already gives bounded concurrent search with error isolation.
