# Example MCP client fragments (Maya Streamable HTTP)

- **`cursor-maya-streamable-http.json`** — merge into Cursor MCP config so the IDE can call tools on a **running** Maya instance (`http://127.0.0.1:8765/mcp` by default).

Full workflow (dev link, debugpy, gateway port): see **[`docs/guide/local-mcp-debug.md`](../../docs/guide/local-mcp-debug.md)**.

**Gateway URL:** if you use multi-instance / election, use `http://127.0.0.1:9765/mcp` instead of `8765`.
