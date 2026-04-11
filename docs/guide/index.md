# What is dcc-mcp-maya?

`dcc-mcp-maya` is the **Maya integration layer** for the [DCC-MCP](https://github.com/loonghao/dcc-mcp-core) ecosystem — a framework that lets AI agents control Digital Content Creation (DCC) tools via the [Model Context Protocol](https://modelcontextprotocol.io).

## The Problem It Solves

Getting AI models to reliably control Maya requires:

1. A **standard protocol** the AI understands (→ MCP)
2. A **server running inside Maya** so it can call `maya.cmds` on the main thread
3. **Pre-built actions** covering common Maya workflows

`dcc-mcp-maya` delivers all three in a single `pip install`.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Maya (embedded Python)                                  │
│                                                          │
│  import dcc_mcp_maya                                     │
│  handle = dcc_mcp_maya.start_server(port=8765)           │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  McpHttpServer  (dcc-mcp-core)                  │    │
│  │  POST /mcp  ──►  ActionRegistry                 │    │
│  │  GET  /mcp  ──►  SSE stream                     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────┘
                           │  http://127.0.0.1:8765/mcp
┌─────────────────────────▼───────────────────────────────┐
│  MCP Host  (Claude Desktop / Cursor / OpenClaw / …)      │
└─────────────────────────────────────────────────────────┘
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Skill** | A directory containing `SKILL.md` + `scripts/`. Defines a group of related actions. |
| **Action** | A single Python script inside `scripts/`. Becomes one MCP tool. |
| **MayaMcpServer** | The Python class that wraps `dcc-mcp-core`'s `McpHttpServer`. |
| **SkillCatalog** | Auto-discovery system that scans directories for `SKILL.md` files. |

## Who Is This For?

- **Maya TD/TA** — Write custom Actions to automate your pipeline, then let AI agents call them.
- **AI App Developers** — Build Claude / GPT / Cursor workflows that create and manipulate Maya scenes.
- **DCC Integration Developers** — Use this as a reference implementation for other DCC tools in the MCP ecosystem.

## Next Steps

- [Getting Started](/guide/getting-started) — Install and run your first MCP session in 5 minutes
- [Available Actions](/guide/actions) — Browse the 200+ built-in actions
- [Advanced Usage](/guide/advanced) — Custom skills, environment variables, hot-reload
