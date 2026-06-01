# CLAUDE.md — Claude Desktop / Anthropic API Integration Guide

> Claude-specific integration notes for `dcc-mcp-maya`.
> For the full project map, see [AGENTS.md](AGENTS.md).

---

## What This Project Does

`dcc-mcp-maya` embeds an MCP Streamable HTTP server directly inside Autodesk Maya. Claude Desktop (or any Anthropic API client using MCP) can call 198 Maya tools over HTTP without any external gateway process.

---

## Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

**File locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

If running multi-instance mode with gateway, use the gateway port instead:
```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

Restart Claude Desktop after editing.

---

## Progressive Loading — Important for Claude

By default, `dcc-mcp-maya` starts in **minimal mode** with only 8 tools active:
- `execute_python`, `execute_mel`
- `get_scene_info`, `get_selection`, `get_session_info`
- `search_tools`, `list_skills`, `load_skill`

**All other skills appear as `__skill__<name>` stubs.** When Claude needs a tool from an unloaded skill, it should:

1. Call `load_skill("maya-primitives")` to expand the skill.
2. Then call the desired tool (e.g., `maya_primitives__create_sphere`).

This keeps the initial `tools/list` small and fast for Claude to parse.

---

## Claude-Specific Tips

- **Viewport feedback:** Ask Claude to call `capture_viewport` after geometry changes. The result is a base64-encoded PNG that Claude can "see" in the conversation.
- **Batch operations:** For multi-step workflows, use `workflow__run_chain` (bundled skill) to chain actions atomically.
- **Cancellation:** Claude can send `notifications/cancelled` for long renders. Skill scripts that poll `check_maya_cancelled()` will exit cleanly.
- **Code execution:** Prefer `search_skills` → `load_skill` → typed tools with `inputSchema`. Use `execute_python` only when no skill covers the task (bulk in-Maya loops, OpenMaya gaps, one-offs). Operators can refuse it with `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON=1` or `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1`.

---

## Quick Test Prompts

> "Create a red sphere in Maya"
> "List all cameras in the scene and select the perspective camera"
> "Capture the viewport so I can see the current state"
> "Load the maya-animation skill and set a keyframe on the sphere's translateY at frame 10"

---

## See Also

- [AGENTS.md](AGENTS.md) — Shared agent navigation map; keep common guidance single-sourced there
- [llms.txt](llms.txt) — One-page core reference
- [llms-full.txt](llms-full.txt) — Exhaustive API reference
- [README.md](README.md) — Human-facing installation and overview
