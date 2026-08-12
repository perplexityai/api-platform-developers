"""Search, then verify the top hits with query-relevant snippets.

Usage: python snippets_verify.py [question ...]
Needs: pip install pplx-srch-sdk; PERPLEXITY_API_KEY exported.
Exit codes: 0 = snippets printed, 1 = no usable hits or API error.
"""

import sys

import pplx_srch_sdk

question = " ".join(sys.argv[1:]) or "how do rust async runtimes differ"

try:
    hits = pplx_srch_sdk.search.web(question, limit=8)
    if not hits:
        print("no hits", file=sys.stderr)
        sys.exit(1)

    # One batched call over all candidate URLs beats one call per URL.
    snips = pplx_srch_sdk.content.snippets(
        query=question,
        urls=[hit.url for hit in hits],
        max_tokens=4096,
        max_tokens_per_page=512,
    )
except pplx_srch_sdk.APIError as e:
    print(f"request failed: {e}", file=sys.stderr)
    sys.exit(1)

# Exit 0 from snippets does not mean every URL succeeded - check error per result.
usable = 0
for s in snips:
    if s.error:
        print(f"SKIP {s.url}: {s.error}", file=sys.stderr)
        continue
    usable += 1
    print(f"== {s.url} ({s.tokens_count} tokens)\n{(s.text or '')[:400]}\n")

sys.exit(0 if usable else 1)
