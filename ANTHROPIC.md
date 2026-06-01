# ANTHROPIC.md — Anthropic API / Claude Code Integration Guide

> Anthropic-specific integration notes for `dcc-mcp-maya`.
> For the full project map, see [AGENTS.md](AGENTS.md).

---

## What This Project Does

`dcc-mcp-maya` embeds an MCP Streamable HTTP server directly inside Autodesk Maya. Any Anthropic API client (Claude Code, Claude Desktop, custom integrations) that speaks MCP Streamable HTTP can discover and invoke 198 Maya tools.

---

## Integration Setup

### Claude Desktop
See [CLAUDE.md](CLAUDE.md) for the exact `claude_desktop_config.json` snippet.

### Claude Code / Custom Anthropic Clients
Configure your MCP client with:

```
Endpoint: http://127.0.0.1:8765/mcp
Protocol: MCP Streamable HTTP (2025-03-26 spec)
```

For multi-instance gateway mode:
```
Endpoint: http://127.0.0.1:9765/mcp
```

---

## Anthropic-Specific Tips

- **Tool use with thinking:** Claude's extended thinking pairs well with `dcc-mcp-maya`'s minimal mode. Claude can first reason about which skill to load, then call `load_skill`, then execute the specific tool.
- **Computer use synergy:** If you are using Claude's computer use capability alongside MCP, `capture_viewport` provides the same visual feedback loop inside Maya.
- **Structured outputs:** Claude handles the nested `ToolResult` dicts from `maya_success` / `maya_error` gracefully. Use the `possible_solutions` field to guide Claude toward recovery when a tool fails.
- **Extended contexts:** For complex scene operations, provide `get_scene_info` output as context. The hierarchical DAG description helps Claude reason about object relationships.

---

## Prompting Recommendations

When building Anthropic prompts for `dcc-mcp-maya`:

1. **Include the minimal mode behavior:** Remind Claude that only core tools are loaded initially and it must call `load_skill` to expand the surface.
2. **Encourage viewport checks:** Add "After geometry changes, call `capture_viewport` to verify visually."
3. **Cancellation awareness:** For async operations, mention that `check_maya_cancelled()` is polled by well-behaved skills, so Claude can safely cancel long jobs.

---

## See Also

- [AGENTS.md](AGENTS.md) — Shared agent navigation map; keep common guidance single-sourced there
- [llms.txt](llms.txt) — One-page core reference
- [llms-full.txt](llms-full.txt) — Exhaustive API reference
- [README.md](README.md) — Human-facing installation and overview
