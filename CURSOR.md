# CURSOR.md — Cursor Editor Integration Guide

> Cursor-specific integration notes for `dcc-mcp-maya`.
> For the full project map, see [AGENTS.md](AGENTS.md).

---

## What This Project Does

`dcc-mcp-maya` embeds an MCP Streamable HTTP server directly inside Autodesk Maya. Cursor (via its MCP server support) can invoke Maya tools while you edit code, enabling a tight feedback loop between code changes and 3D scene state.

---

## Cursor Configuration

In Cursor Settings → MCP Servers, add:

```json
{
  "maya": {
    "url": "http://127.0.0.1:8765/mcp"
  }
}
```

For multi-instance gateway mode:
```json
{
  "maya": {
    "url": "http://127.0.0.1:9765/mcp"
  }
}
```

---

## Cursor-Specific Workflows

### 1. Skill Script Development (Edit → Test → Iterate)
The ideal Cursor workflow for `dcc-mcp-maya`:

1. **Edit** a skill script in `src/dcc_mcp_maya/skills/maya-my-feature/scripts/my_tool.py`.
2. **Save** — if hot-reload is enabled (`DCC_MCP_MAYA_HOT_RELOAD=1`), the server picks up changes automatically.
3. **Test** — ask Cursor to call the tool: `"Run my_tool with radius=2"`.
4. **Verify** — `"Capture the viewport"` to see the result as a base64 PNG.

### 2. Inline Code Review for Skills
Paste a skill script into Cursor and ask:
> "Review this Maya skill script for thread safety. Does it need `affinity: main`?"

Cursor can cross-reference `tools.yaml` and the script content to validate the affinity declaration.

### 3. Refactoring Across Skills
Cursor's codebase-aware edits work well for bulk changes:
> "Update all skills that use `error_result(..., str(exc))` to use `maya_from_exception(exc, ...)` instead"

---

## Cursor-Specific Tips

- **Hot reload:** Set `DCC_MCP_MAYA_HOT_RELOAD=1` before starting the server. Cursor edits to skill scripts are reflected immediately without restarting Maya.
- **Terminal integration:** Use Cursor's integrated terminal to run `python tools/lint_skill_affinity.py` before committing new skills.
- **Composability:** Cursor can generate multi-file skill packages. Create `SKILL.md`, `tools.yaml`, `groups.yaml`, and `scripts/*.py` in a single session.

---

## See Also

- [AGENTS.md](AGENTS.md) — Progressive disclosure map for all agent types
- [llms.txt](llms.txt) — One-page core reference
- [llms-full.txt](llms-full.txt) — Exhaustive API reference
- [README.md](README.md) — Human-facing installation and overview
