# Fan-out reference

Read this when running many independent searches, or turning fan-out output into artifacts.

## `search.web_many`

```python
import pplx_srch_sdk

results = pplx_srch_sdk.search.web_many(
    [
        {"query": "python 3.13 release notes"},
        {"query": "python 3.13 whats new", "domains": ["docs.python.org"]},
    ],
    limit_per_query=10,
    concurrency=5,
)
```

- Accepts plain query strings (each becomes `{"query": s}`) or kwargs dicts forwarded to the single-shot `search.web`; spec dicts accept only kwargs `search.web` accepts.
- Extra kwargs on the `web_many` call itself are shared defaults applied to every spec; per-spec values win.
- `limit_per_query` is the per-query hit count (forwards as `limit=` to each search). Passing a conflicting `limit` alongside it raises `TypeError`.
- `concurrency` bounds simultaneous in-flight calls (default 5).
- Spec dicts are shallow-copied; mutable values like `domains=[...]` are stored by reference, so do not mutate them after dispatch.
- Keep caller-side metadata in a side dict keyed by `spec["query"]`; do not smuggle extra keys into the spec.

## FanoutResult shape

One `FanoutResult` per input query, in input order:

- `r.ok` - `True` when the call succeeded.
- `r.spec` - the request kwargs for that call (provenance).
- `r.result` - the `list[WebHit]` on success.
- `r.error` - the isolated exception on failure (a typed `pplx_srch_sdk` error; it does not raise).

There is no `.request` attribute. One failed query never fails the batch - always branch on `r.ok`.
The exception: setup problems such as a missing `PERPLEXITY_API_KEY` raise before any query is dispatched.

## Artifact pattern

Split successes from errors, flatten to rows, dedup, persist as JSONL - all helpers live in `pplx_srch_sdk.utils`:

```python
import pplx_srch_sdk
from pplx_srch_sdk.utils import dedup_by_url, flatten_fanout_rows, partition, write_jsonl

raw = pplx_srch_sdk.search.web_many(QUERIES, limit_per_query=10)
oks, errs = partition(raw, lambda r: r.ok)
rows = dedup_by_url(flatten_fanout_rows(oks))

write_jsonl("results.jsonl", rows)
write_jsonl("errors.jsonl", [e.to_dict() for e in errs])
print(f"results.jsonl\nsearch: {len(rows)} rows, {len(errs)} errors")
```

- `flatten_fanout_rows(results)` emits one dict row per hit and preserves request provenance under `row["spec"]` - read `row["spec"]["query"]`, not a top-level `row["query"]`.
- `dedup_by_url(hits)` / `dedup_by_field(hits, field)` handle dicts and typed hits uniformly; first occurrence wins. When merging variants, sort longest-`snippet`-first before deduping so the richest text survives.
- `write_jsonl(path, rows)` / `read_jsonl(path, limit=None)` / `to_jsonl(obj)` round-trip JSONL artifacts; prefer JSONL over JSON arrays so partial output stays readable.
- `preview(value, max_chars=300)` returns a JSON-compatible copy with long strings truncated - print that instead of full multi-KB results.

## Resumable batches

For pipelines that must survive interruption, `pplx_srch_sdk.utils.Checkpoint(workspace)` stores per-key JSONL fragments with atomic writes: `has(key)` to skip completed batches, `record(key, rows)` to persist one batch, `read_all()` to stream every stored row back.
Combine it with `pplx_srch_sdk.utils.fanout` (see [async.md](async.md)) for checkpointed concurrent dispatch: build one key per batch, skip keys that `has()`, and rebuild flat outputs from `read_all()` at the end.

## Keep errors visible

Never drop the error half of a fan-out - a silently failed query looks identical to a query with no results.
Persist errors next to results, and re-run only the failed specs after fixing the cause.
