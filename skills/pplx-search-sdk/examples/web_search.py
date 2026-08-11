"""One-off web search with filters and typed error handling.

Usage: python web_search.py [query ...]
Needs: pip install pplx-srch-sdk; PERPLEXITY_API_KEY exported.
Exit codes: 0 = hits printed, 1 = API error.
"""

import sys

import pplx_sdk

query = " ".join(sys.argv[1:]) or "rust async runtimes"

try:
    hits = pplx_sdk.search.web(
        query,
        intent=f"Find current, authoritative pages about: {query}",
        limit=5,
        excluded_domains=["pinterest.com"],
    )
except pplx_sdk.AuthenticationError as e:
    print(f"auth failed ({e}); export PERPLEXITY_API_KEY", file=sys.stderr)
    sys.exit(1)
except pplx_sdk.APIError as e:
    print(f"search failed: {e}", file=sys.stderr)
    sys.exit(1)

# search.web returns a bare list[WebHit] - no wrapper object.
for hit in hits:
    print(f"{hit.title}\n  {hit.url}  ({hit.date or 'no date'})")
    if hit.snippet:
        print(f"  {hit.snippet[:160]}")
