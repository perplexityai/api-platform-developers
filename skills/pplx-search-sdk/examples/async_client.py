"""Async client with bounded custom fan-out via pplx_srch_sdk.utils.fanout.

Usage: python async_client.py
Needs: pip install pplx-srch-sdk; PERPLEXITY_API_KEY exported.
Exit codes: 0 = at least one search succeeded, 1 = all failed.
"""

import asyncio
import sys

from pplx_srch_sdk import AsyncPplxClient, PplxSdkError
from pplx_srch_sdk.utils import fanout

SPECS = [
    {"query": "python 3.13 release notes", "limit": 5},
    {"query": "python 3.14 whats new", "limit": 5, "domains": ["docs.python.org"]},
    {"query": "python packaging survey 2026", "limit": 5},
]


async def main() -> int:
    # One client for the whole script; per-coroutine clients leak connections.
    try:
        async with AsyncPplxClient() as client:
            results = await fanout(client.search.web, SPECS, concurrency=3)
    except PplxSdkError as e:
        print(f"client failed: {e}", file=sys.stderr)
        return 1

    ok = 0
    for r in results:
        if not r.ok:
            print(f"{r.spec['query']} failed: {r.error}", file=sys.stderr)
            continue
        ok += 1
        top = r.result[0] if r.result else None
        print(f"{r.spec['query']}: {len(r.result)} hits" + (f", top: {top.url}" if top else ""))
    return 0 if ok else 1


sys.exit(asyncio.run(main()))
