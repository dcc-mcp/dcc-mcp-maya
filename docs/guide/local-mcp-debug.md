# Local MCP + debugging (Maya + Cursor / Claude)

Use this after a **dev link** (`just maya-dev-build-link-core-win` / `just maya-link-win`) so an MCP host can call your live Maya, and optionally attach a **Python debugger** to the Maya process.

## 1. Start Maya and the MCP HTTP server

1. Launch Maya (or `just maya-dev-debug-win` from the repo).
2. Load **`dcc_mcp_maya`** in **Windows → Settings/Preferences → Plug-in Manager** (auto-load if you want it every session).
3. Confirm the server URL in the Script Editor / stdout (default **`http://127.0.0.1:8765/mcp`** unless `DCC_MCP_MAYA_PORT` is set).

**Multi-instance / gateway:** if the plugin registered an elected gateway, the aggregated MCP URL is often **`http://127.0.0.1:9765/mcp`**. Point your MCP client at the URL that matches how you run (direct Maya vs gateway).

## 2. Connect Cursor (Streamable HTTP MCP)

1. Open **Cursor Settings → MCP** (or edit the workspace / user MCP JSON, depending on your Cursor version).
2. Add a server that uses the **HTTP** / **Streamable HTTP** transport to your Maya URL.

Copy the JSON fragment from [`examples/mcp/cursor-maya-streamable-http.json`](../../examples/mcp/cursor-maya-streamable-http.json) into your MCP configuration, or merge:

```json
{
  "mcpServers": {
    "maya-local": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

3. Restart MCP / reload the window if the host does not pick up changes.
4. In chat, use **Maya** tools (e.g. `search_tools`, `load_skill`, `execute_python`) against the live session.

If the connection fails: confirm Maya is running, the plugin is loaded, no other process owns the port, and Windows Firewall is not blocking localhost.

## 3. Connect Claude Desktop (reference)

Add to `claude_desktop_config.json` (see [CLAUDE.md](../../CLAUDE.md)):

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

## 4. Python debugging (debugpy + Cursor / VS Code)

Maya embeds CPython; you can attach **debugpy** from the same interpreter family as your Maya version.

1. Install **debugpy** into that Maya’s environment (once):

   ```text
   "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install debugpy
   ```

2. In **Maya Script Editor** (Python), run once after startup (pick a free port):

   ```python
   import debugpy
   debugpy.listen(("127.0.0.1", 5678))
   print("[dcc-mcp-maya] debugpy listening on 127.0.0.1:5678 — attach from IDE, then trigger your code")
   ```

   Optionally call `debugpy.wait_for_client()` to block until the debugger attaches (not usually needed for MCP-driven flows).

3. In **Cursor / VS Code**, use **Run and Debug → Python: Remote Attach** with host `127.0.0.1` and port `5678`.

4. Set breakpoints in `src/dcc_mcp_maya/**/*.py` (or your skill scripts), then invoke the tool from MCP; execution should stop on breakpoints **when that code runs on the main thread** (same rules as Maya scripting).

**Rust (`dcc_mcp_core`)** debugging inside Maya is heavier (native extension); use logging, or build a small `mayapy` repro that imports `dcc_mcp_core` outside Maya for faster native debug cycles.

## 5. Quick checklist

| Check | Action |
|-------|--------|
| MCP 404 / connection refused | Plugin loaded? Correct port (`8765` vs `9765`)? |
| Tools missing | Minimal mode: call `load_skill("…")` first (see AGENTS.md). |
| Breakpoints never hit | Code path must run in Maya; use `debugpy` on the Maya process you attached to. |

## Related

- [`getting-started.md`](./getting-started.md) — first-time MCP setup
- [`installation.md`](./installation.md) — `mayapy` / plugin / `userSetup.py`
- Repo **AGENTS.md** — progressive loading, affinity, cancellation
