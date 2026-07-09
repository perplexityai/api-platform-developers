#!/usr/bin/env python3
"""Scan a codebase for Perplexity Sonar (chat completions) usage.

Prints a migration checklist grouped by file, with the reference file that
covers each finding. Report only - it never modifies anything and never
touches the network.

Usage: python scan_sonar_usage.py [path]   (path defaults to ".")

Exit codes: 0 (clean or findings printed), 2 (bad path).
Stdlib only; Python 3.9+.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
}

SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".ipynb", ".md",
    ".mdx", ".json", ".yaml", ".yml", ".sh", ".rb", ".go", ".java", ".kt",
    ".php", ".cs", ".curl", ".txt",
}

REF = {
    "endpoint": "references/request-mapping.md (endpoint mapping)",
    "call": "references/integration-styles.md",
    "model": "references/models-and-presets.md (model mapping)",
    "param": "references/request-mapping.md (param table / REMOVE list)",
    "response": "references/response-and-streaming.md",
    "streaming": "references/response-and-streaming.md (streaming)",
}

SONAR_MODEL = r"sonar(?:-pro|-reasoning(?:-pro)?|-deep-research)?"

# (category, compiled regex, short label)
PATTERNS = [
    # Endpoints
    ("endpoint", re.compile(r"/(?:v1/)?chat/completions"), "chat completions endpoint"),
    ("endpoint", re.compile(r"/v1/sonar\b"), "legacy /v1/sonar endpoint"),
    ("endpoint",
     re.compile(r"base_?[uU][rR][lL]\s*[:=]\s*[\"']https?://api\.perplexity\.ai/?[\"']"),
     "base_url missing /v1"),
    # Call styles
    ("call", re.compile(r"\bchat\.completions\.create\b"), "chat.completions.create()"),
    ("call", re.compile(r"\bChatPerplexity\b"), "LangChain ChatPerplexity bridge"),
    ("call", re.compile(r"\bOpenAIChatCompletionsModel\b"), "Agents SDK chat-completions model class"),
    # Model slugs in string context (quoted, or model: sonar in YAML/curl)
    ("model",
     re.compile(r"[\"']" + SONAR_MODEL + r"[\"']"),
     "Sonar model slug"),
    ("model",
     re.compile(r"\bmodel[\"']?\s*[:=]\s*" + SONAR_MODEL + r"\b(?![\w/-])"),
     "Sonar model slug"),
    # Sonar-only or relocated request params
    ("param",
     re.compile(r"\b(?:search_domain_filter|search_recency_filter"
                r"|search_after_date_filter|search_before_date_filter"
                r"|last_updated_(?:after|before)_filter|web_search_options"
                r"|search_mode|disable_search|enable_search_classifier"
                r"|return_images|return_related_questions|num_search_results"
                r"|presence_penalty|frequency_penalty|top_k|max_tokens)\b"),
     "Sonar request param"),
    ("param",
     re.compile(r"[\"']messages[\"']\s*:\s*\[|\bmessages\s*=\s*\["),
     "messages array (rename to input)"),
    ("param",
     re.compile(r"\bresponse_format\b"),
     "response_format (keep TOP-LEVEL; never text.format; extra_body/TS cast on OpenAI SDK)"),
    # Response-field access
    ("response", re.compile(r"choices\[0\]|\[[\"']choices[\"']\]"), "choices[0] access"),
    ("response",
     re.compile(r"\.citations\b|\[[\"']citations[\"']\]|\.get\([\"']citations[\"']"),
     "top-level citations access"),
    ("response", re.compile(r"delta\.content|choices\[0\]\.delta|\[[\"']choices[\"']\]\[0\]\[[\"']delta[\"']\]"), "delta.content access"),
    ("response",
     re.compile(r"\.search_results\b|\[[\"']search_results[\"']\]|\.get\([\"']search_results[\"']"),
     "top-level search_results access"),
    ("response", re.compile(r"\bfinish_reason\b"), "finish_reason access"),
    ("response", re.compile(r"\b(?:prompt_tokens|completion_tokens)\b"), "usage key rename"),
]

# Streaming flags: only reported when another Sonar signal exists in the file.
STREAM_PATTERNS = [
    ("streaming", re.compile(r"\bstream\s*=\s*True\b"), "streaming consumer"),
    ("streaming", re.compile(r"[\"']stream[\"']\s*:\s*[Tt]rue|\bstream:\s*true\b"), "streaming consumer"),
]

MAX_SNIPPET = 60


def snippet(line):
    text = line.strip()
    if len(text) > MAX_SNIPPET:
        text = text[: MAX_SNIPPET - 3] + "..."
    return text


FILTER_PARAM_RX = re.compile(
    r"\b(?:search_domain_filter|search_recency_filter"
    r"|search_after_date_filter|search_before_date_filter"
    r"|last_updated_(?:after|before)_filter)\b")
NESTED_FILTERS_RX = re.compile(r"[\"']?filters[\"']?\s*[:=]|\bfilters\s*\{")


def _inside_tool_filters(lines, idx):
    """True when line idx (0-based) sits in or next to a filters block, i.e. the
    filter params are already correctly nested inside a web_search tool."""
    lo = max(0, idx - 4)
    return any(NESTED_FILTERS_RX.search(lines[j]) for j in range(lo, idx + 1))


def scan_lines(lines, loc_fmt="L{n}"):
    """Scan an iterable of lines; yield (category, location, snippet, label)."""
    lines = list(lines)
    findings = []
    stream_hits = []
    for n, line in enumerate(lines, 1):
        seen = set()
        for category, rx, label in PATTERNS:
            if (category, label) in seen:
                continue
            if rx.search(line):
                if (label == "Sonar request param" and FILTER_PARAM_RX.search(line)
                        and not re.search(r"\bmax_tokens\b|\bweb_search_options\b|\bsearch_mode\b", line)
                        and _inside_tool_filters(lines, n - 1)):
                    continue
                seen.add((category, label))
                findings.append((category, loc_fmt.format(n=n), snippet(line), label))
        for category, rx, label in STREAM_PATTERNS:
            if rx.search(line):
                stream_hits.append((category, loc_fmt.format(n=n), snippet(line), label))
                break
    return findings, stream_hits


def scan_text_file(path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings, stream_hits = scan_lines(text.splitlines())
    if findings:
        findings.extend(stream_hits)
    return findings


def scan_notebook(path):
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return []
    findings = []
    stream_hits = []
    for idx, cell in enumerate(nb.get("cells", []), 1):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        if isinstance(source, str):
            lines = source.splitlines()
        else:
            lines = [ln.rstrip("\n") for ln in source]
        f, s = scan_lines(lines, loc_fmt="cell %d, L{n}" % idx)
        findings.extend(f)
        stream_hits.extend(s)
    if findings:
        findings.extend(stream_hits)
    return findings


def iter_files(root):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SCAN_EXTENSIONS:
            yield path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan for Perplexity Sonar (chat completions) usage."
    )
    parser.add_argument("path", nargs="?", default=".", help="file or directory to scan")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"error: path does not exist: {root}", file=sys.stderr)
        return 2

    total = 0
    files_with_findings = 0
    for path in iter_files(root):
        if path.suffix.lower() == ".ipynb":
            findings = scan_notebook(path)
        else:
            findings = scan_text_file(path)
        if not findings:
            continue
        files_with_findings += 1
        total += len(findings)
        try:
            display = path.relative_to(root) if root.is_dir() else path
        except ValueError:
            display = path
        print(f"== {display} ==")
        width = max(len(c) for c, _, _, _ in findings)
        for category, loc, text, label in findings:
            print(f"  [{category:<{width}}] {loc}: {text}")
            print(f"  {'':<{width + 2}} -> {label}; see {REF[category]}")
        print()

    if total == 0:
        print("no Sonar usage found")
    else:
        plural = "s" if files_with_findings != 1 else ""
        print(f"{files_with_findings} file{plural} with Sonar usage, {total} findings total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
