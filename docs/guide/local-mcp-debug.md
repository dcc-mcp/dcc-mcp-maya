# Local MCP + debugging (Maya + Cursor / Claude)

Use this after a **dev link** (`just maya-dev-build-link-core-win` / `just maya-link-win`) so an MCP host can call your live Maya, and optionally attach a **Python debugger** to the Maya process.

## 1. Start Maya and the MCP HTTP server

1. Launch Maya (or `just maya-dev-debug-win` from the repo).
2. Load **`dcc_mcp_maya`** in **Windows → Settings/Preferences → Plug-in Manager** (auto-load if you want it every session).
3. Confirm the gateway URL in the Script Editor / stdout (usually **`http://127.0.0.1:9765/mcp`** in plugin sidecar mode).

For a deliberately direct Python server, use the exact URL returned by
`start_server().mcp_url()`; its instance port is OS-assigned by default.

## 2. Connect Cursor (Streamable HTTP MCP)

1. Open **Cursor Settings → MCP** (or edit the workspace / user MCP JSON, depending on your Cursor version).
2. Add a server that uses the **HTTP** / **Streamable HTTP** transport to your Maya URL.

Copy the JSON fragment from [`examples/mcp/cursor-maya-streamable-http.json`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/mcp/cursor-maya-streamable-http.json) into your MCP configuration, or merge:

```json
{
  "mcpServers": {
    "maya-local": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

3. Restart MCP / reload the window if the host does not pick up changes.
4. In chat, use **Maya** tools (e.g. `search_tools`, `load_skill`, `execute_python`) against the live session.

If the connection fails: confirm Maya is running, the plugin is loaded, no other process owns the port, and Windows Firewall is not blocking localhost.

## 3. Connect Claude Desktop (reference)

Add to `claude_desktop_config.json` (see [`docs/integrations/claude.md`](../integrations/claude.md)):

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

## 4. Python debugging (debugpy + Cursor / VS Code)

Maya embeds CPython; **debugpy** is an optional enhancement for IDE breakpoint debugging.
The rest of `maya-dev` works without it, and `maya_dev__start_debugpy` reports `debugpy_missing` with setup guidance when it is absent.

1. Install **debugpy** into that Maya’s environment (once):

   ```text
   "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install debugpy
   ```

2. Load the `maya-dev` skill and start the listener from MCP:

   ```json
   {
     "tool": "load_skill",
     "arguments": {"skill_name": "maya-dev"}
   }
   ```

   ```json
   {
     "tool": "maya_dev__start_debugpy",
     "arguments": {
       "host": "127.0.0.1",
       "port": 5678,
       "configure_python": true,
       "log_dir": "C:/temp/maya-debugpy"
     }
   }
   ```

   The result includes `debug_session` metadata, `client_connected`, `log_uri`, and suggested `path_mappings` for attached projects.
   Use `wait_for_client=true` only when you deliberately want Maya to block until the IDE attaches.

3. In **Cursor / VS Code**, use **Run and Debug → Python: Remote Attach** with host `127.0.0.1` and port `5678`.

4. Set breakpoints in `src/dcc_mcp_maya/**/*.py` (or your skill scripts), then invoke the tool from MCP; execution should stop on breakpoints **when that code runs on the main thread** (same rules as Maya scripting).

**Rust (`dcc_mcp_core`)** debugging inside Maya is heavier (native extension); use logging, or build a small `mayapy` repro that imports `dcc_mcp_core` outside Maya for faster native debug cycles.

## 5. Distinguish startup, Home, and editor readiness

MCP readiness proves that the dispatcher can service scene calls. It does not
prove that the editor viewport is visible: Maya can serve tools while its Home
window covers the editor. Report those two observations separately; do not
change `/v1/readyz` to reject a working session just because Home is open.

For application observations and input, use the project `dcc-cua` / DCC-MCP
`ui-control` route. Report the runtime version and exact PID/HWND before the
first observation. A supplied screenshot can suggest a state, but a live action
requires a fresh observation bound to the actual process and window.

| Observed surface | Evidence | Next step |
|------------------|----------|-----------|
| Startup splash | Maya splash with a current loading stage | Observe again after an interval and compare the stage, timestamps, and process activity. |
| First-use Home | Home navigation plus the new/experienced-user choice | Complete the local welcome choice, then use the control that enters Maya. |
| Home | Recent files/project navigation and an enter-editor control | Enter the existing editor without creating or replacing a scene. |
| Editor | Visible viewport and editor controls, such as Outliner or Channel Box | Verify a typed scene query against the same instance. |
| Blocking dialog or unknown | A modal prompt, ambiguous ownership, or insufficient evidence | Report the observed blocker; do not guess a click. |

Match control roles, structure, ownership, and fresh pixels together, rather
than relying only on English labels such as `Experienced` or `Go to Maya`.
Floating overlays are not evidence of Maya's own state.

An action acknowledgement or a focused button is not a completed transition.
After entering the editor, rediscover the window: Home and the editor can have
different HWNDs in the same process. Rebind DCC-CUA, take a fresh observation,
and confirm the viewport before declaring GUI acceptance. If guarded input is
refused because the target is not foreground, stop input and use the project's
scoped native activation/recovery path. A refused `restore_activate` can still
leave the exact window restored: read fresh native state before considering the
separate `activate` operation. Do not blindly repeat the refused operation or
reuse consumed observations. Request manual focus only after the applicable
project recovery paths fail. Do not replace the route with generic computer
automation or injected Maya UI code.

A temporarily unresponsive splash is not sufficient evidence of a deadlock.
Correlate repeated observations with the same process's bootstrap stages,
sidecar registration, and read-only thread diagnostics. Record missing evidence
explicitly: a plugin name on a splash screen alone does not identify the call
that owns the elapsed startup time.

Thread diagnostics can themselves change the failure. Avoid periodic
`faulthandler.dump_traceback_later()` in Maya startup acceptance harnesses:
CPython has a [confirmed crash while traversing invalid/freed frames](https://github.com/python/cpython/issues/140815).
A Maya 2027.2/Python 3.13.9 diagnostic run hit an access violation on the
traceback timer thread; it must not be counted as proof that plugin startup
crashed. Keep ordinary crash logging enabled, preserve native crash dumps, and
compare a standard startup without the diagnostic timer. Analyze the original
exception thread using matching binaries/symbols before attributing a failure
to the last tool call or the plugin named on the splash screen.

## 6. Quick checklist

| Check | Action |
|-------|--------|
| MCP 404 / connection refused | Plugin loaded? Use gateway `9765`, or the exact direct URL reported at startup. |
| Tools missing | Minimal mode: call `load_skill("…")` first (see AGENTS.md). |
| `debugpy_missing` | Optional: install debugpy into the matching `mayapy`, then restart Maya to unlock stronger IDE attach debugging. |
| `port_in_use` | Pick another port or stop the process already listening there. |
| Breakpoints never hit | Code path must run in Maya; use `maya_dev__start_debugpy` on the Maya process you attached to. |

## Related

- [`getting-started.md`](./getting-started.md) — first-time MCP setup
- [`installation.md`](./installation.md) — `mayapy` / plugin / `userSetup.py`
- Repo **AGENTS.md** — progressive loading, affinity, cancellation
