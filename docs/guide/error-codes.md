# Error Codes

Maya can localize `maya.cmds` exception messages based on the OS or Maya UI language. Tool envelopes therefore include stable, locale-independent fields where possible:

```json
{
  "success": false,
  "message": "Python execution failed",
  "error": "TypeError('必须为标志「allObjects」传递一个布尔参数')",
  "error_code": "ARG_TYPE_MISMATCH",
  "error_type": "TypeError"
}
```

Agents should branch on `error_code` and keep the localized `error` string for human display.

| Code | Meaning |
| --- | --- |
| `ARG_TYPE_MISMATCH` | A Maya command flag or argument has the wrong type. |
| `NODE_NOT_FOUND` | A referenced Maya node does not exist. |
| `ATTRIBUTE_NOT_FOUND` | A referenced node attribute does not exist. |
| `LOCKED_ATTRIBUTE` | A target attribute is locked or connected. |
| `VERSION_MISMATCH` | A file, plug-in, or command requires a different Maya/API version. |
| `PLUGIN_NOT_LOADED` | A required Maya plug-in is not loaded. |
| `FILE_NOT_FOUND` | A required file path does not exist. |
| `PERMISSION_DENIED` | The process cannot read or write the requested path/resource. |
| `UNDO_LOCKED` | The operation is blocked by Maya undo-state restrictions. |
| `EXECUTION_TIMEOUT` | Script execution exceeded its timeout. |
| `UNKNOWN` | No stable classifier matched; inspect `error_type` and `error`. |

`maya_scripting__execute_python` also returns `context.kind == "tool-timeout"` with `context.elapsed_secs` when its cooperative timeout trips.
