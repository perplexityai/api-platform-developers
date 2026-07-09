#!/usr/bin/env bash
# Grader for the migrate-sonar-to-agent-api eval.
# Usage:
#   ./check.sh <dir-with-migrated-app> [--style raw-http|sdk] [--live]
#   PYTHON=/path/to/python ./check.sh <dir> --style raw-http --live
#
# --style pins the endpoint invariant: raw-http requires the /v1/agent literal,
# sdk requires responses.create. Without --style either is accepted (a notice is printed).
# Exit code 0 = migration passes the rubric; non-zero = defects found.

set -u
TARGET="${1:?usage: check.sh <dir-with-migrated-app> [--style raw-http|sdk] [--live]}"
shift
STYLE=""
LIVE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --style) STYLE="${2:?--style needs raw-http or sdk}"; shift 2 ;;
    --live) LIVE="--live"; shift ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
done
PY="${PYTHON:-python3}"
fail=0

hit() {
  grep -RnE "$1" "$TARGET" --include='*.py' \
    --exclude-dir='.venv' --exclude-dir='venv' --exclude-dir='__pycache__' \
    --exclude-dir='.git' --exclude-dir='node_modules' --exclude-dir='site-packages' \
    2>/dev/null
}

echo "== Leftover Sonar patterns (each must be absent from *.py) =="
ABSENT=(
  'chat/completions'
  "choices\\[0\\]|\\[[\"']choices[\"']\\]"
  "(^|[^_a-zA-Z])max_tokens\\b"
  'delta\.content|choices.*delta'
  '\[DONE\]'
  'return_related_questions'
  "\\[[\"']citations[\"']\\]|\\.citations\\b|get\\([\"']citations[\"']"
  "[\"']sonar(-[a-z]+)*[\"']"
)
for pat in "${ABSENT[@]}"; do
  if hit "$pat" >/dev/null; then
    echo "FAIL leftover: $pat"
    hit "$pat" | head -3
    fail=1
  else
    echo "  ok: no $pat"
  fi
done

echo
echo "== Required Agent API patterns (each must be present in *.py) =="
case "$STYLE" in
  raw-http) ENDPOINT_PAT='v1/agent' ;;
  sdk) ENDPOINT_PAT='responses\.create' ;;
  '') ENDPOINT_PAT='v1/agent|responses\.create'
      echo "  note: no --style given; accepting either endpoint form (pass --style raw-http|sdk to pin it)" ;;
  *) echo "unknown --style: $STYLE (want raw-http or sdk)"; exit 2 ;;
esac
PRESENT=(
  "$ENDPOINT_PAT"
  'max_output_tokens'
  "[\"']web_search[\"']"
  'search_results'
  "[\"']status[\"']|\\.status\\b"
)
for pat in "${PRESENT[@]}"; do
  if hit "$pat" >/dev/null; then
    echo "  ok: found $pat"
  else
    echo "FAIL missing: $pat"
    fail=1
  fi
done

if [ "$LIVE" = "--live" ]; then
  echo
  echo "== Live runs (needs PERPLEXITY_API_KEY and a python with the app's deps) =="
  for cmd in 'trend_report.py "quantum computing"' 'ask_stream.py "Why is the sky blue? One sentence."' 'extract_stats.py "Nvidia"'; do
    script="${cmd%% *}"
    if [ ! -f "$TARGET/$script" ]; then
      echo "  skip: $script not present"
      continue
    fi
    if (cd "$TARGET" && eval "\"$PY\" $cmd" >/tmp/eval-run.out 2>&1); then
      echo "  ok: $script ran ($(wc -l </tmp/eval-run.out | tr -d ' ') lines of output)"
    else
      echo "FAIL live run: $script"
      tail -5 /tmp/eval-run.out
      fail=1
    fi
  done
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS: migration meets the rubric."
else
  echo "FAIL: defects above."
fi
exit "$fail"
