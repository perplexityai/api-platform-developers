"""Fan out independent queries, split successes from errors, dedup, write JSONL.

Usage: python fanout_research.py
Needs: pip install pplx-srch-sdk; PERPLEXITY_API_KEY exported.
Exit codes: 0 = artifacts written (even with per-query errors), 1 = every query failed.
"""

import json
import sys

import pplx_sdk
from pplx_sdk.utils import dedup_by_url, flatten_fanout_rows, partition, preview, write_jsonl

QUERIES = [
    {"query": "yellowstone national park visitor numbers 2025"},
    {"query": "zion national park entrance fee 2026"},
    {"query": "acadia camping reservations", "domains": ["nps.gov"]},
]

# Per-query failures land on r.error; only setup problems (e.g. missing key) raise.
try:
    raw = pplx_sdk.search.web_many(QUERIES, limit_per_query=10, concurrency=5)
except pplx_sdk.PplxSdkError as e:
    print(f"fan-out failed: {e}", file=sys.stderr)
    sys.exit(1)

oks, errs = partition(raw, lambda r: r.ok)
if not oks:
    for r in errs:
        print(f"{r.spec['query']} failed: {r.error}", file=sys.stderr)
    sys.exit(1)

# One row per hit, request kwargs preserved under row["spec"].
rows = dedup_by_url(flatten_fanout_rows(oks))

write_jsonl("results.jsonl", rows)
write_jsonl("errors.jsonl", [{"spec": dict(r.spec), "error": str(r.error)} for r in errs])

print(f"results.jsonl: {len(rows)} rows, errors.jsonl: {len(errs)} errors")
print(json.dumps(preview(rows[:3]), indent=2))
