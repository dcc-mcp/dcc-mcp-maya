# 错误码

Maya 会根据操作系统或 Maya UI 语言本地化 `maya.cmds` 异常消息。工具结果会尽量包含稳定、与语言无关的字段：

```json
{
  "success": false,
  "message": "Python execution failed",
  "error": "TypeError('必须为标志「allObjects」传递一个布尔参数')",
  "error_code": "ARG_TYPE_MISMATCH",
  "error_type": "TypeError"
}
```

Agent 应优先根据 `error_code` 分支处理，把本地化的 `error` 字符串保留给人类阅读。

| 错误码 | 含义 |
| --- | --- |
| `ARG_TYPE_MISMATCH` | Maya 命令 flag 或参数类型错误。 |
| `NODE_NOT_FOUND` | 引用的 Maya 节点不存在。 |
| `ATTRIBUTE_NOT_FOUND` | 引用的节点属性不存在。 |
| `LOCKED_ATTRIBUTE` | 目标属性被锁定或已有连接。 |
| `VERSION_MISMATCH` | 文件、插件或命令需要不同的 Maya/API 版本。 |
| `PLUGIN_NOT_LOADED` | 必需的 Maya 插件尚未加载。 |
| `FILE_NOT_FOUND` | 必需的文件路径不存在。 |
| `PERMISSION_DENIED` | 当前进程无法读取或写入目标路径/资源。 |
| `UNDO_LOCKED` | 操作被 Maya undo 状态限制阻止。 |
| `EXECUTION_TIMEOUT` | 脚本执行超过超时时间。 |
| `UNKNOWN` | 没有匹配到稳定分类；请检查 `error_type` 和 `error`。 |

当 `maya_scripting__execute_python` 的协作式超时触发时，还会返回 `context.kind == "tool-timeout"` 和 `context.elapsed_secs`。
