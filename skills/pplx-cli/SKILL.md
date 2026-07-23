---
name: pplx-cli
description: "Install and use Perplexity's pplx CLI for live web search and page-content fetch from the terminal. Use to search the web, look up current information or news, fetch a URL's content as text, or install and authenticate the pplx command."
when_to_use: "Any request like: search the web for X, find the latest news about X, look up current events, use Perplexity to search, search with pplx, install the pplx CLI, set up the Perplexity CLI, fetch this URL, get the content of this page, read this webpage, restrict a web search to certain domains or dates."
argument-hint: "[search query or URL]"
---

# pplx - Perplexity's web search and content-fetch CLI

## What this skill does

Installs, authenticates, and drives Perplexity's public `pplx` CLI: `pplx search web` for live web search, `pplx content fetch` for page content.
Output contract: success = exit 0 and exactly one JSON object on stdout; failures are pitfall 4.

## Install

Skip if `pplx --version` already works (prints a calver like `2026.07.23.1784784046+c8b317a`).

```sh
curl -fsSL https://github.com/perplexityai/perplexity-cli/releases/latest/download/install.sh | sh
```

SHA-256-verified, no sudo, installs to `~/.local/bin/pplx` (override: `PPLX_INSTALL_PATH`); ensure `~/.local/bin` is on `PATH`.
Platforms: macOS arm64, Linux x86_64, Linux arm64 - only.
Update with `pplx update` (checksum-verified in-place replacement, no API key needed); `pplx update --check` only reports whether a newer release exists.

## Auth

To auth run: `pplx auth login` if not authed already (interactive, needs a terminal; keys: https://www.perplexity.ai/account/api).
In non-interactive sessions (agents, CI) export `PERPLEXITY_API_KEY` instead - `auth login` rejects piped input (pitfall 1).

The env var takes precedence over a key stored by interactive `pplx auth login` (`<config>/perplexity/credentials.json`; macOS `~/Library/Application Support`, Linux `$XDG_CONFIG_HOME` or `~/.config`).
No configured key results in an `AUTHENTICATION` error on the first real command.
Keys are redacted from all CLI output; the CLI talks to `https://api.perplexity.ai`.

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
Set `PPLX_OUTPUT_DIR` once to a workspace-appropriate path to give every command a default save dir instead of repeating `--output-dir`.
More scoping flags (`--domains`, date bounds, `--recency-filter`, `--country`, token budgets): see `pplx search web --help`.

## Fetch

```sh
pplx content fetch https://example.com/article
```

http(s) URLs only.
**Check `error` and `is_paywall` in the output before trusting `content`.**
`--no-cache` forces a live fetch (cache is on by default).
`--html` adds `raw_html` fetched live via crawler - large; combine it with `--output-dir` + `--stdout-preview`.
Saved file: `{dir}/fetch/{rand}.json`.

## When unsure

Every subcommand's `--help` prints full flag docs plus Input shape, Stdout shape, Saved file schema, and examples - consult it instead of guessing flags.

## Top pitfalls

1. **`pplx auth login` is TTY-only** (hidden interactive prompt) and hard-rejects non-interactive use - as an agent, set the `PERPLEXITY_API_KEY` env var instead. `auth logout` and `auth login <key>` do not exist.
2. **`--stdout-preview` is a no-op without a save dir.** It truncates long string fields (`...<truncated>` markers) only when the result is also saved via `--output-dir DIR` or `$PPLX_OUTPUT_DIR`; alone, you get full-size output - and hits can be multi-KB each, so a default search can return tens of KB.
3. **Extra positional queries are reformulations of the SAME search** (recall boosters for one question), not separate searches. N distinct topics = N invocations.
4. **Every failure exits 1 with empty stdout and exactly one JSON error object on stderr** (`{"error":{"code","message","command","hint"?}}`) - parse stderr, not stdout, on failure. Codes include `AUTHENTICATION`, `UNKNOWN_ARGUMENT`, `ARGUMENT_ERROR`, `BAD_REQUEST` (not exhaustive; branch on `error.code`).
5. **Date flags use MM/DD/YYYY, not ISO dates** (e.g. `--published-after-date 07/01/2026`).
6. **Don't combine `--recency-filter` with date bounds.** The server rejects `--recency-filter` + `--published-after/before-date` as `BAD_REQUEST` ("recency cannot be used together with published_after or published_before") - a wasted round trip, not caught client-side.
