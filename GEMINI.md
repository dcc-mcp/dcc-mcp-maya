# GEMINI.md — Google Gemini / Vertex AI Integration Guide

> Gemini-specific integration notes for `dcc-mcp-maya`.
> For the full project map, see [AGENTS.md](AGENTS.md).

---

## What This Project Does

`dcc-mcp-maya` embeds an MCP Streamable HTTP server directly inside Autodesk Maya. Gemini (via an MCP-compatible client or custom integration) can discover and invoke 198 Maya tools over HTTP.

---

## Gemini-Specific Strengths

Gemini excels at **code generation** and **structured output parsing**. Leverage these when working with `dcc-mcp-maya`:

### 1. Skill Script Generation
Ask Gemini to generate new Maya skill scripts using the `dcc_mcp_maya.api` helpers:

```python
from dcc_mcp_maya.api import with_maya, maya_success

@with_maya
def batch_rename(prefix: str, suffix: str = "") -> dict:
    """Rename selected objects with prefix and suffix."""
    import maya.cmds as cmds
    selected = cmds.ls(selection=True) or []
    renamed = []
    for obj in selected:
        new_name = f"{prefix}{obj}{suffix}"
        renamed.append(cmds.rename(obj, new_name))
    return maya_success("Renamed objects", renamed=renamed, count=len(renamed))
```

### 2. Structured Tool Results
Gemini handles nested JSON well. Parse `maya_success` / `maya_error` results directly:

```json
{
  "success": true,
  "message": "Created sphere",
  "context": {
    "object_name": "pSphere1",
    "radius": 1.0
  }
}
```

### 3. Skill Search & Discovery
Use Gemini's search capability with the built-in discovery tools:
- `find_skills("render batch")` → returns matching skills with descriptions
- `search_tools(query="bake", tags=["animation"])` → filtered search

---

## Integration Setup

If your Gemini client supports MCP over HTTP, configure:

```
Endpoint: http://127.0.0.1:8765/mcp
Protocol: MCP Streamable HTTP (2025-03-26 spec)
```

For multi-instance gateway mode:
```
Endpoint: http://127.0.0.1:9765/mcp
```

---

## Gemini-Specific Tips

- **Code-first workflows:** Gemini can write complete skill packages. Generate `SKILL.md`, `tools.yaml`, and `scripts/*.py` in one shot, then place them in a directory listed in `DCC_MCP_MAYA_SKILL_PATHS`.
- **Batch reasoning:** Use `workflow__run_chain` to chain multiple tool calls. Gemini can plan the chain and validate intermediate results.
- **Image understanding:** Feed `capture_viewport` base64 PNGs back to Gemini for visual state verification.

---

## See Also

- [AGENTS.md](AGENTS.md) — Shared agent navigation map; keep common guidance single-sourced there
- [llms.txt](llms.txt) — One-page core reference
- [llms-full.txt](llms-full.txt) — Exhaustive API reference
- [README.md](README.md) — Human-facing installation and overview
