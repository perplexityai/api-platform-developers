# api-platform-developers

Official Perplexity API Platform skills, published as portable [Agent Skills](https://agentskills.io).
They work in Claude Code, OpenAI Codex CLI, and any other Agent Skills client, and the repository doubles as a Claude Code plugin marketplace.
It will grow more Platform skills over time.

## Install

### Claude Code

Inside Claude Code:

```
/plugin marketplace add perplexityai/api-platform-developers
/plugin install perplexity-platform@api-platform-developers
/reload-plugins
```

Or clone the repo and load the plugin directly:

```
claude --plugin-dir .
```

Invoke a skill with `/perplexity-platform:migrate-sonar-to-agent-api [path]`.

### Codex CLI and other Agent Skills clients

Codex plugin flow (skills + docs MCP in one install): `codex plugin marketplace add perplexityai/api-platform-developers`, then install `perplexity-platform` from `/plugins`.
Or install skills only:
Project scope: copy or symlink `skills/<name>` into `<your-repo>/.agents/skills/<name>`.
User scope: copy or symlink `skills/<name>` into `~/.agents/skills/<name>`.

Or use the ecosystem installers:

- `npx skills add perplexityai/api-platform-developers` - fans out to ~70 agents.
- `gh skill add` - supports version pinning.
- Codex's `$skill-installer` with this repo's GitHub URL.

Invocation in Codex: implicit by description match, or explicit with `$migrate-sonar-to-agent-api`.

### Standalone (no plugin)

Any agent that can fetch a URL can use a skill directly - tell it:

```
Read https://raw.githubusercontent.com/perplexityai/api-platform-developers/main/skills/pplx-cli/SKILL.md, install the skill, and use it for search.
```

(The github.com blob URL works too; the raw URL skips the HTML chrome.)

## Skill catalog

| Skill | Invoke | What it does |
|---|---|---|
| migrate-sonar-to-agent-api | `/perplexity-platform:migrate-sonar-to-agent-api [path]` (Claude Code) or `$migrate-sonar-to-agent-api` (Codex) | Migrates a codebase from Sonar chat completions to the Agent API |
| pplx-cli | `/perplexity-platform:pplx-cli [query or URL]` (Claude Code) or `$pplx-cli` (Codex) | Installs and uses the `pplx` CLI for live web search and query-relevant page snippets |

Skills also auto-trigger on matching context (for example, "help me migrate from Sonar") once installed.

## Docs MCP server

Agents can search the live API documentation while migrating via the docs MCP server at https://docs.perplexity.ai/mcp.
It is wired per client:

- Claude Code: the plugin ships it in `.mcp.json` - installing the plugin is enough. Standalone: `claude mcp add --transport http perplexity-docs https://docs.perplexity.ai/mcp`.
- Codex: installing the plugin (`codex plugin marketplace add perplexityai/api-platform-developers`, then install `perplexity-platform` from `/plugins`) bundles it via `.codex-plugin/plugin.json`; the skill also declares it in `agents/openai.yaml`, and for skill-only installs you can add it globally in `~/.codex/config.toml`:

```toml
[mcp_servers.perplexity-docs]
url = "https://docs.perplexity.ai/mcp"
```

Skills never hard-depend on it; it is a freshness upgrade, not a requirement.

## Documentation

The underlying API documentation lives at [docs.perplexity.ai](https://docs.perplexity.ai).

## License

Licensed under the [Apache License 2.0](LICENSE).
