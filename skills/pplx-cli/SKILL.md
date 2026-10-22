---
name: pplx-cli
description: "Install and use Perplexity's pplx CLI for live web search, query-relevant page snippets, and the API changelog. Use to search the web, get excerpts from URLs, check Perplexity API changes and deprecations before recommending an integration, or install and authenticate pplx."
when_to_use: "Any request like: search the web for X, find the latest news about X, look up current events, use Perplexity to search, search with pplx, install the pplx CLI, set up the Perplexity CLI, get query-relevant excerpts from specific URLs, what do these pages say about X, restrict a web search to certain domains or dates, what changed in the Perplexity API, check recent API deprecations or model updates."
argument-hint: "[search query, URL, or API changelog question]"
---

# pplx - Perplexity's web search, page-snippets, and API changelog CLI

## What this skill does

Installs and drives Perplexity's public `pplx` CLI: `pplx search web` for live web search, `pplx content snippets` for query-relevant page excerpts, and `pplx changelog` for public API updates without authentication.
Output contract: success = exit 0 and exactly one JSON object on stdout; failures are pitfall 4.

## Install

Skip if `pplx --version` already works (prints a calver like `2026.07.30.1785394496+1b7382b`).

```sh
curl -fsSL https://github.com/perplexityai/perplexity-cli/releases/latest/download/install.sh | sh
```

SHA-256-verified, no sudo, installs to `~/.local/bin/pplx` (override: `PPLX_INSTALL_PATH`); ensure `~/.local/bin` is on `PATH`.
Platforms: macOS arm64, Linux x86_64, Linux arm64 - only.
Update with `pplx update` (checksum-verified in-place replacement, no API key needed); `pplx update --check` only reports whether a newer release exists.

## Auth

Only search and snippets need an API key. For API updates, go directly to [API changelog](#api-changelog).

To auth run: `pplx auth login` if not authed already (interactive, needs a terminal; keys: https://www.perplexity.ai/account/api).
In non-interactive sessions (agents, CI) export `PERPLEXITY_API_KEY` instead - `auth login` rejects piped input (pitfall 1).

The env var takes precedence over a key stored by interactive `pplx auth login` (`<config>/perplexity/credentials.json`; macOS `~/Library/Application Support`, Linux `$XDG_CONFIG_HOME` or `~/.config`).
No configured key results in an `AUTHENTICATION` error on search or snippets.
Keys are redacted from all CLI output; search and snippets use `https://api.perplexity.ai`.

## API changelog

When asked what changed in the Perplexity API, or when recent capabilities, model updates, or deprecations affect an integration recommendation, read the changelog before giving guidance:

```sh
pplx changelog
pplx changelog --limit 20
```

The command reads the public docs RSS feed at `https://docs.perplexity.ai/docs/resources/changelog/rss.xml` without credentials. It works before `pplx auth login`; do not request an API key for it.

If `pplx changelog --help` reports an unknown command, run `pplx update`. If it is still unavailable, read `https://docs.perplexity.ai/docs/resources/changelog` directly.

- Stdout: `{entries: [{headline, tags, url, date, content}]}`. `tags` is an array of strings; the other entry fields are strings.
- Default: up to five entries. `--limit` accepts integers from 1 through 20 and returns only as many entries as the feed contains.
- Preserve feed order, which follows the changelog page. `date` is the feed-reported date normalized to RFC 3339, not necessarily the original publication date.
- `content` is HTML. A leading bold headline is lifted into `headline`; when absent, the feed title is used and the body stays intact.
- Summarize relevant entries and cite their `url` values. For older history, follow the full changelog page; the feed is a limited window, so an absent entry does not establish that a feature is unavailable.
- On failure, use the stderr error contract below: `CHANGELOG_FETCH_FAILED` means check connectivity and retry; `FEED_PARSE_FAILED` means update the CLI or consult the changelog page. An out-of-range `--limit` returns `VALUE_VALIDATION`. Report a failed read as unavailable evidence, not as "no updates."

## Search

```sh
pplx search web "kubernetes pod OOMKilled causes"
```

Stdout: `{hits: [{url, title, domain, snippet?, ...}], total, saved_to?}`.
To keep tokens down, save-and-preview - the extra positional here is a rewording of the same question (pitfall 3):

```sh
pplx search web "kubernetes pod OOMKilled causes" "why does k8s keep killing my pod with OOMKilled" \
  -n 5 --output-dir out --stdout-preview=200
```

That keeps stdout to a few KB, with `saved_to` (plus `truncated` when any field was actually cut) and the full JSON at `out/web/{rand}.json` (written only after a successful request) - read the file when the preview is not enough.
Set `PPLX_OUTPUT_DIR` once to a workspace-appropriate path to give search and snippets a default save dir instead of repeating `--output-dir`.
More scoping flags (`--domains`, date bounds, `--recency-filter`, `--country`, token budgets): see `pplx search web --help`.

## Snippets

```sh
pplx content snippets "<query>" <url>... [--max-tokens N] [--max-tokens-per-page N]
```

1-50 http(s) URLs; here the extra positionals are ADDITIONAL PAGES to excerpt, not query rephrasings (the opposite of `search web`, pitfall 3).
Stdout: `{results: [{url, text?, tokens_count?, error?}], saved_to?}` - one result per URL.
**Check `error` on every result before trusting `text`** - exit 0 means the request succeeded, not that every URL did (pitfall 7); a failed URL has `error` set and no `text`.
Elided regions inside `text` are marked with `…`.
Token budgets: `--max-tokens` = total across all snippets, 1-16384, default 4096; `--max-tokens-per-page` = per page, 1-4096, must be <= `--max-tokens`, default `min(1024, max_tokens)`.
Saved file: `{dir}/snippets/{rand}.json`.
The query is positional-only: `-q`/`--query` and `--no-cache` are `UNKNOWN_ARGUMENT` parse errors here.
Binaries v0.2.2 and older fail with an unknown-command error on `content snippets` - run `pplx update` first.
`content fetch` is removed; use `content snippets`.

## When unsure

Consult each subcommand's `--help` instead of guessing flags. Search and snippets also document input, stdout, saved-file shapes, and examples there. Changelog output is already JSON; it has no `--json` or `--output-dir` flag.

## Top pitfalls

1. **`pplx auth login` is TTY-only** (hidden interactive prompt) and hard-rejects non-interactive use - as an agent, set the `PERPLEXITY_API_KEY` env var instead. `auth logout` and `auth login <key>` do not exist.
2. **`--stdout-preview` is a no-op without a save dir.** It truncates long string fields (`...<truncated>` markers) only when the result is also saved via `--output-dir DIR` or `$PPLX_OUTPUT_DIR`; alone, you get full-size output - and hits can be multi-KB each, so a default search can return tens of KB.
3. **Extra positional queries on `search web` are reformulations of the SAME search** (recall boosters for one question), not separate searches. N distinct topics = N invocations. On `content snippets` extra positionals are more URLs, never rephrasings.
4. **Every failure exits 1 with empty stdout and exactly one JSON error object on stderr** (`{"error":{"code","message","command","hint"?}}`) - parse stderr, not stdout, on failure. Codes include `AUTHENTICATION`, `UNKNOWN_ARGUMENT`, `ARGUMENT_ERROR`, `BAD_REQUEST` (not exhaustive; branch on `error.code`).
5. **Date flags use MM/DD/YYYY, not ISO dates** (e.g. `--published-after-date 07/01/2026`).
6. **Don't combine `--recency-filter` with date bounds.** The server rejects `--recency-filter` + `--published-after/before-date` as `BAD_REQUEST` ("recency cannot be used together with published_after or published_before") - a wasted round trip, not caught client-side.
7. **Exit 0 from `content snippets` does not mean every URL succeeded.** Per-URL failures ride a successful response as `results[i].error`; check it on each result before using `text`.
