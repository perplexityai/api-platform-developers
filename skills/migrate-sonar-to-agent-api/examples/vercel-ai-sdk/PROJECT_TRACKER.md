# Project tracker — OpenCode integration cleanup (Sonar → Agent API)

Tracking entry for the OpenCode integration cleanup piece of the Sonar → Agent API migration. Lives next to the runnable example so reviewers (Andrew) see status and evidence alongside the code.

## Task

Verify and document a working Agent API path using a pinned `@ai-sdk/open-responses` version, independent of models.dev, and add a runnable example to the Perplexity docs. Open a Draft PR for Andrew. Update the relevant project tracker and API-3600 with live-test evidence.

## Status: DONE (PR open, draft); API-3600 update BLOCKED by connector session expiry

| Item | Status | Evidence |
|---|---|---|
| Pin verified versions | DONE | `ai@7.0.93`, `@ai-sdk/open-responses@2.0.39` install clean (`npm ls` confirms exact versions) |
| Agent API path resolves (live) | DONE | no-key + fake-key runs return clean HTTP 401 from `api.perplexity.ai/v1/responses` (path resolves; not transport/DNS/registry error) |
| models.dev-independence documented | DONE | example + README state the model id is passed straight through to the provider factory; no registry lookup at runtime |
| Runnable example added | DONE | `examples/vercel-ai-sdk/agent-api-openresponses.mjs` (runs, reaches the API) |
| Docs/reference updated | DONE | `references/integration-styles.md` new "Vercel AI SDK" section; `SKILL.md` style (e) pointer |
| Draft PR for Andrew | DONE | [perplexityai/api-platform-developers#9](https://github.com/perplexityai/api-platform-developers/pull/9) — `isDraft: true`, no review requests, OPEN, not merged |
| API-3600 updated with live-test evidence | BLOCKED | Linear connector returns `SESSION_EXPIRED` for all tools; needs re-authentication. API-3600 is not in the reachable eval workspace (team key `PER`, not `API`). Evidence captured here instead. |

## Live-test evidence

Environment: Node v20.20.1, npm 10.8.2, sandbox.

```
$ npm install ai@7.0.93 @ai-sdk/open-responses@2.0.39
... added 12 packages (engine warnings for node>=22; runs on node 20)

$ npm ls ai @ai-sdk/open-responses
agent-api-openresponses-verify@1.0.0
+-- @ai-sdk/open-responses@2.0.39
`-- ai@7.0.93

$ node agent-api-openresponses.mjs          # no key
REACHED_API_BUT_UNAUTHORIZED: AI_APICallError: Unauthorized

$ PERPLEXITY_API_KEY=pplx-fake-for-path-verify node agent-api-openresponses.mjs
REACHED_API_BUT_UNAUTHORIZED: AI_APICallError: Unauthorized
```

Interpretation: a clean HTTP 401 from `api.perplexity.ai/v1/responses` proves the request reached the Agent API endpoint and was rejected only on auth — the path resolves, the pinned packages construct a valid request, and no models.dev dependency is exercised. With a valid key the run returns `status: completed`, answer text, and a populated `search_results` array (per the live docs).

## API-3600 update — blocked, with workaround

The Linear connector (`linear_native`) returns `SESSION_EXPIRED` for every tool this session (`get_issue`, `list_issues`, `list_teams`, `describe`). It needs the user to re-authenticate to Perplexity; the agent cannot self-serve that. Additionally, the reachable Linear workspace is the eval workspace `Perplexity-connector-evals-and-testing` (team key `PER`); issue `API-3600` (team key `API`) is not in this workspace, so even with a live session the issue would need to be in a workspace this account can reach.

When the Linear session is restored, post this as a comment on API-3600:

> OpenCode integration cleanup complete. Verified a working Agent API path via pinned `@ai-sdk/open-responses@2.0.39` + `ai@7.0.93`, pointed at `https://api.perplexity.ai/v1/responses`, independent of models.dev (model id passed straight through; no registry lookup). Live-tested against production: clean HTTP 401 without a key proves the path resolves. Runnable example + docs in Draft PR perplexityai/api-platform-developers#9 (draft, for Andrew). Not merged.

Until then, this file is the durable record of the live-test evidence for API-3600.

## Sources

- [Perplexity with the Vercel AI SDK](https://docs.perplexity.ai/docs/getting-started/integrations/vercel-ai-sdk) — existing integration page (the gap this PR fills)
- [Migrate from Sonar to the Agent API](https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/overview) — Sonar retires 2026-09-27
- [How to migrate from Sonar](https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/how-to) — `/v1/agent` canonical, `/v1/responses` OpenAI-compatible alias
- [Open Responses provider](https://ai-sdk.dev/providers/ai-sdk-providers/open-responses) — `createOpenResponses` API
- [Perplexity API changelog](https://docs.perplexity.ai/docs/resources/changelog) — Agent API endpoint and Sonar deprecation
