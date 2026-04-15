# Skill Hot-Reload in dcc-mcp-maya

Automatic file hot-reload for Maya MCP skills — modify `SKILL.md` or script files and see changes instantly without restarting the MCP server.

## Quick Start

### Enable hot-reload when starting the server

```python
import dcc_mcp_maya

# Method 1: via function parameter
handle = dcc_mcp_maya.start_server(enable_hot_reload=True)

# Method 2: via environment variable
import os
os.environ["DCC_MCP_MAYA_HOT_RELOAD"] = "1"
handle = dcc_mcp_maya.start_server()
```

### Control hot-reload via Maya menu

In interactive Maya mode, the "DCC MCP" menu includes:

```
DCC MCP
├── Show MCP URL
├── Restart MCP Server
├── Stop MCP Server
├── Enable/Disable Hot Reload  ← NEW
└── Open MCP in Browser
```

Click to toggle hot-reload on/off without restarting.

### Manual control from Python

```python
import dcc_mcp_maya

server = dcc_mcp_maya.start_server()

# Enable hot-reload
if server.enable_hot_reload(debounce_ms=300):
    print("Hot-reload enabled")

# Check status
stats = server.hot_reload_stats
print(f"Watching {len(stats['watched_paths'])} directories")
print(f"Total reloads: {stats['reload_count']}")

# Disable hot-reload
server.disable_hot_reload()
```

## Configuration

### Debounce delay

When a file is saved, it may trigger multiple low-level filesystem events. The debounce mechanism coalesces these into a single reload. Customize the delay:

```python
# Via environment variable (milliseconds)
os.environ["DCC_MCP_MAYA_HOTRELOAD_DEBOUNCE_MS"] = "250"

# Via function parameter
server.enable_hot_reload(debounce_ms=250)
```

**Recommended values:**
- `150ms` — Very responsive, may cause redundant reloads on slow drives
- `300ms` — Default, balanced for most setups
- `500ms` — Tolerates network shares, slower feedback

### Watched directories

Hot-reload monitors these locations (in priority order):

1. Built-in skills shipped with dcc-mcp-maya (`src/dcc_mcp_maya/skills/`)
2. `DCC_MCP_MAYA_SKILL_PATHS` environment variable
3. `DCC_MCP_SKILL_PATHS` environment variable (global fallback)
4. Bundled skills from dcc-mcp-core (diagnostics, workflow, git-automation)
5. Platform default skills directory

## What gets monitored

Hot-reload triggers when these files change:

- ✅ `SKILL.md` — Skill metadata (name, description, tools list)
- ✅ Script files (`.py`, `.mel`, `.lua`, etc.) — Tool implementations
- ✅ `metadata/depends.md` — Skill dependencies
- ✅ Directory creation — New skills detected automatically

Files that don't trigger reload:

- ❌ `.md` files (except `SKILL.md` and `depends.md`)
- ❌ `.txt`, `.json`, `.yaml` config files
- ❌ Binary files

## How it works

1. **Filesystem monitoring**: Uses platform-native APIs
   - **Linux**: inotify
   - **macOS**: FSEvents
   - **Windows**: ReadDirectoryChangesW

2. **Debouncing**: Rapid successive events are coalesced (default 300ms)

3. **Background thread**: All I/O happens on a background thread, never blocking Maya

4. **Transaction semantics**: Failed reloads keep the old version online

## Troubleshooting

### Hot-reload doesn't seem to work

1. Check if it's enabled:
   ```python
   import dcc_mcp_maya.server as srv
   print(srv._server_instance.is_hot_reload_enabled)
   ```

2. Verify watched directories:
   ```python
   stats = srv._server_instance.hot_reload_stats
   print(f"Watching: {stats['watched_paths']}")
   ```

3. Check Maya script editor for errors (DEBUG level logs)

### Reload count not increasing

- Ensure you're modifying files in watched directories
- Try manual reload:
  ```python
  count = srv._server_instance._hot_reloader.reload_now()
  print(f"Manually reloaded {count} skills")
  ```

### Performance impact

Hot-reload has minimal overhead:

- **CPU**: < 1% (background thread)
- **Memory**: ~2MB (SkillWatcher state)
- **Latency**: 300ms + skill load time (~100-500ms per skill)

## Limitations & Future Work

### Current (v0.3.0)

- ✅ Filesystem monitoring for Python/MEL/Lua scripts
- ✅ Debounce & background threading
- ✅ Transaction-safe unload/load
- ✅ Environment variable & menu control

### Planned (P2)

- ⏳ Incremental reload (only changed skills, not full rescan)
- ⏳ Failure retry with exponential backoff
- ⏳ Performance metrics collection (reload duration, success rate)
- ⏳ Web UI status page with reload history

### Not supported

- ❌ Code injection/live patching (requires full unload/reload)
- ❌ State preservation across reloads (skill state is reset)
- ❌ Partial file changes (entire skill is reloaded on any change)

## Related

- **dcc-mcp-core**: [SkillWatcher](https://github.com/loonghao/dcc-mcp-core/blob/main/crates/dcc-mcp-skills/src/watcher.rs) (Rust implementation)
- **Requires**: dcc-mcp-core >= 0.12.24 with SkillWatcher support
- **Tests**: `tests/test_hotreload.py`

## Contributing

Found issues or want to improve hot-reload? See [dcc-mcp-maya issues](https://github.com/loonghao/dcc-mcp-maya/issues).
