# OPENAI.md — OpenAI API / GPT Integration Guide

> OpenAI-specific integration notes for `dcc-mcp-maya`.
> For the full project map, see [AGENTS.md](AGENTS.md).

---

## What This Project Does

`dcc-mcp-maya` embeds an MCP Streamable HTTP server directly inside Autodesk Maya. Any OpenAI-powered client that speaks MCP Streamable HTTP can call 370+ Maya tools.

---

## Integration Setup

If your OpenAI client (custom chat UI, agent framework, etc.) supports MCP:

```
Endpoint: http://127.0.0.1:8765/mcp
Protocol: MCP Streamable HTTP (2025-03-26 spec)
```

For multi-instance gateway mode:
```
Endpoint: http://127.0.0.1:9765/mcp
```

---

## Function Calling Mapping

MCP tools map naturally to OpenAI function calling:

| OpenAI Concept | MCP Equivalent |
|----------------|----------------|
| `functions` list | `tools/list` endpoint |
| `function.name` | `{skill}__{script}` (e.g. `maya_scene__new_scene`) |
| `function.arguments` | JSON payload sent to `tools/call` |
| `function_call` | `tools/call` request with `_meta.progressToken` for async |

For async tools (`execution: async` in `tools.yaml`), the server returns a `job_id` immediately. Poll `jobs.get_status` to track progress — similar to OpenAI's `run` status polling.

---

## OpenAI-Specific Tips

- **System prompt:** Include a summary of [llms.txt](llms.txt) in your system prompt so the model knows the available tool surface.
- **Tool selection:** With 73+ tools, the initial `tools/list` in minimal mode is small (~8 tools). The model should learn to call `load_skill` before attempting specialized operations.
- **Async handling:** Long renders return a `job_id`. Use `jobs.get_status` with the same `job_id` to poll. Set a reasonable polling interval (2–5s).

---

## See Also

- [AGENTS.md](AGENTS.md) — Progressive disclosure map for all agent types
- [llms.txt](llms.txt) — One-page core reference
- [llms-full.txt](llms-full.txt) — Exhaustive API reference
- [README.md](README.md) — Human-facing installation and overview
