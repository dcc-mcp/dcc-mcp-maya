---
name: maya-plugins
description: |-
  Bootstrap stage - diagnose and manage Maya plug-ins: enumerate what Maya
  knows, load and unload them, and explain precisely why one is unusable
  (missing file, not on the search path, not loaded, or refusing to unload).
  Use when a command or node type is missing, when a plug-in fails to load,
  or before relying on a renderer or third-party integration. For running
  code rather than managing plug-ins, use maya-scripting.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: bootstrap
    version: 1.0.0
    tags:
    - maya
    - plugins
    - plug-in
    - mll
    - load-plugin
    - unload-plugin
    - dependency
    - search-path
    - diagnostics
    search-hint: |-
      plugin, plug-in, mll, bundle, load plugin, unload plugin, plugin not
      found, plugin failed to load, plugin version, plugin path, vendor,
      autoload, MAYA_PLUG_IN_PATH, search path, plugin dependency, unknown
      command, missing node type, mtoa, arnold plugin
    tools: tools.yaml
    groups: groups.yaml
---
# maya-plugins (Bootstrap stage)

Manage and diagnose Maya plug-ins. The emphasis is on **actionable failures**:
when something is unusable, the error says which of the four causes it is and
what to do about it.

## Verified Maya behaviours

Three things drive this design and are invisible under a mock (verified on Maya
2025):

- `pluginInfo` metadata flags - `path`, `version`, `vendor`, `apiVersion`,
  `unloadOk`, `name` - are only valid **while the plug-in is loaded**. Querying
  them for an unloaded plug-in raises. They are read opportunistically and
  reported as unavailable with a reason, never as a failure of the whole call.
- `pluginInfo` has **no dependency flag** at all (`dependents`, `dependencies`,
  `requires` are all rejected). Dependencies are inferred from the search path
  instead of pretending to be queryable.
- `cmds.loadPlugin(..., quiet=True)` **still raises** when the plug-in cannot be
  found - `quiet` does not suppress load errors. A failed load is therefore
  always an error, and Maya's message is surfaced verbatim.

There is also no `cmds.pluginPath` or `cmds.getenv`; the search path comes from
the `MAYA_PLUG_IN_PATH` environment variable, read through `os.environ` with a
MEL `getenv` fallback for hosted interpreters.

## Flow

1. `list_plugins` — what exists, and what is loaded.
2. `diagnose_plugin` — why a specific one is unusable.
3. `load_plugin` — load it, optionally setting `autoload`.
4. `unload_plugin` — unload it; refuses when Maya reports `unloadOk=False`
   unless `force=True`.
5. `get_plugin_path` — inspect the search path, or resolve a name to a file.

## Notes

- Loading a plug-in does not register it permanently; `autoload=True` sets the
  preference so it loads in future sessions.
- Maya drops a plug-in from `pluginInfo(listPlugins=True)` once unloaded, so a
  second unload reports "already unloaded" rather than "unknown" when the file
  is still on the search path.

## Scope

Managing plug-ins only. Running Python or MEL is `maya-scripting`.

## Scripts

- `diagnose_plugin` - Explain why a plug-in is or is not usable: path, load state and problems
- `get_plugin_path` - Report the plug-in search path and resolve a plug-in name to a file
- `list_plugins` - List Maya plug-ins with their load state and metadata
- `load_plugin` - Load a Maya plug-in, with an actionable error when it cannot be found
- `unload_plugin` - Unload a Maya plug-in, refusing when Maya reports it cannot be unloaded
