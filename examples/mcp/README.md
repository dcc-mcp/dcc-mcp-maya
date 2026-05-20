# Example MCP client fragments (Maya Streamable HTTP)

- **`cursor-maya-streamable-http.json`** — merge into Cursor MCP config so the IDE can call tools on a **running** Maya plugin gateway (`http://127.0.0.1:9765/mcp` by default).

Full workflow (dev link, debugpy, gateway port): see **[`docs/guide/local-mcp-debug.md`](../../docs/guide/local-mcp-debug.md)**.

**Direct server URL:** if you deliberately start `dcc_mcp_maya.start_server(port=8765)`, use `http://127.0.0.1:8765/mcp` instead.
