# Eval: migrate-sonar-to-agent-api

A hand-runnable evaluation for the `migrate-sonar-to-agent-api` skill, with a real app as the test fixture.

## What is here

| Path | What it is |
|---|---|
| `fixture/raw-http/` | A pristine, working Sonar app in raw-HTTP style (`requests` to `/chat/completions`), verified against production on 2026-07-09. It deliberately exercises the classic migration hazards: top-level `citations` and `search_results`, top-level search filters, `max_tokens`, `delta.content` streaming with the `[DONE]` sentinel, `return_related_questions`, and `response_format` structured output. |
| `fixture/perplexity-sdk/` | The same app built on the official Perplexity Python SDK (`client.chat.completions.create`), same hazards in SDK form. Also production-verified. |
| `reference-migration/<name>/` | One real migration of each fixture, produced by the skill in a live run. Model output is nondeterministic, so treat these as examples, not golden diff targets. Grade with `check.sh`, not by comparing to these directories. |
| `evals.json` | Four eval cases in the skill-creator format (prompt, expected_output, files): full migrations of both apps, an error-driven trigger, and a symptom-driven trigger. |
| `cases/` | Pre-broken inputs for the trigger eval cases: `half-migrated/` (endpoint switched, Sonar params left - reproduces the 400 unknown-field premise of case 3) and `bad-parsing/` (request migrated, response parsing still reads top-level citations - reproduces case 4). |
| `check.sh` | The grader: leftover-pattern greps, required-pattern greps, and optional live runs. Point it at one app directory at a time and pin the integration style: `./check.sh <dir> --style raw-http` or `--style sdk`. |
Code in fixtures and references is intentionally comment-free, so agents must work from the code itself rather than comment hints.

## Run the eval by hand

1. Copy the fixture to a scratch directory and make it a git repo, so the migration shows up as a clean diff:

```bash
rm -rf /tmp/sonar-eval && cp -R fixture/raw-http /tmp/sonar-eval && cd /tmp/sonar-eval   # or fixture/perplexity-sdk
git init -q && git add -A && git commit -qm "fixture: pristine Sonar app"
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
export PERPLEXITY_API_KEY="pplx-..."   # required for the skill's live verification
```

2. Confirm the fixture works before migrating (behavior baseline):

```bash
.venv/bin/python trend_report.py "quantum computing"
.venv/bin/python ask_stream.py "Why is the sky blue?"
.venv/bin/python extract_stats.py "Nvidia"
```

3. Run the migration with the skill installed (any eval case from `evals.json`, e.g. case 1):

```bash
claude   # inside /tmp/sonar-eval, with the perplexity-platform plugin installed
# then: /perplexity-platform:migrate-sonar-to-agent-api .
# or the natural-language prompt from evals.json
```

4. Grade:

```bash
cd <this-directory>
./check.sh /tmp/sonar-eval --style raw-http                       # static rubric (--style sdk for the SDK fixture)
PYTHON=/tmp/sonar-eval/.venv/bin/python ./check.sh /tmp/sonar-eval --style raw-http --live   # plus live runs
git -C /tmp/sonar-eval diff                                       # eyeball the transformation
```

5. For an A/B baseline, reset the scratch copy (`git -C /tmp/sonar-eval checkout .`) and repeat step 3 in a session WITHOUT the plugin, then grade both.

## Rubric (what `check.sh` asserts)

- No leftovers: `chat/completions`, `choices[0]`, `max_tokens`, `delta.content` chunk handling, `[DONE]`, `return_related_questions`, top-level `citations` reads.
- Required: `/v1/agent`, `max_output_tokens`, a `web_search` tool, `search_results` output-item handling, a `status` check.
- With `--live`: all three scripts run green against production.
- Judged by eye (not greppable): the related-questions feature is preserved via a workaround rather than silently dropped, and the streaming consumer exits on every terminal event, not only `response.completed`.

## Conventions note

skill-creator keeps `evals/evals.json` inside the skill directory and runs cases into a sibling `<skill>-workspace/` reviewed with its eval-viewer.
We keep the same `evals.json` shape but store evals at the repo level (`evals/<skill-name>/`), so installed skill bundles stay lean - skill installers copy the whole skill directory.
`assets/` would be the wrong bucket: per the spec it holds files a skill uses in its OUTPUT (templates, fonts), not test material.
