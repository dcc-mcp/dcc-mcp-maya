# 本地 MCP 与调试（Maya + Cursor / Claude）

在完成 **开发链接**（`just maya-dev-build-link-core-win` / `just maya-link-win`）后，用 MCP 宿主连接本机 Maya；也可选地把 **Python 调试器** 附加到 Maya 进程。

## 1. 启动 Maya 与 MCP HTTP 服务

1. 启动 Maya（或从仓库运行 `just maya-dev-debug-win`）。
2. 在 **Windows → Settings/Preferences → Plug-in Manager** 中加载 **`dcc_mcp_maya`**（需要时可设为自动加载）。
3. 在脚本编辑器 / 标准输出中确认服务 URL（默认 **`http://127.0.0.1:8765/mcp`**，除非设置了 `DCC_MCP_MAYA_PORT`）。

**多实例 / 网关：** 若插件注册了选举出的网关，聚合后的 MCP URL 常为 **`http://127.0.0.1:9765/mcp`**。请按实际运行方式（直连 Maya 还是走网关）在 MCP 客户端中填写对应 URL。

## 2. 连接 Cursor（Streamable HTTP MCP）

1. 打开 **Cursor 设置 → MCP**（或按你使用的 Cursor 版本编辑工作区 / 用户 MCP JSON）。
2. 添加使用 **HTTP** / **Streamable HTTP** 传输、指向上述 Maya URL 的服务器。

可将 [`examples/mcp/cursor-maya-streamable-http.json`](../../examples/mcp/cursor-maya-streamable-http.json) 中的 JSON 片段复制到 MCP 配置，或合并为：

```json
{
  "mcpServers": {
    "maya-local": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

3. 若宿主未加载配置，请重启 MCP / 重载窗口。
4. 在对话中使用 **Maya** 工具（如 `search_tools`、`load_skill`、`execute_python`）操作当前会话。

若连接失败：确认 Maya 已运行、插件已加载、端口未被占用，且本机防火墙未拦截 localhost。

## 3. 连接 Claude Desktop（参考）

在 `claude_desktop_config.json` 中加入（详见仓库根目录 `CLAUDE.md`）：

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

## 4. Python 调试（debugpy + Cursor / VS Code）

Maya 内嵌 CPython；可在与 Maya 版本匹配的解释器环境中安装 **debugpy** 并附加调试。

1. 向该 Maya 环境安装 **debugpy**（一次性）：

   ```text
   "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install debugpy
   ```

2. 在 **Maya 脚本编辑器**（Python）中于启动后执行一次（端口可自定）：

   ```python
   import debugpy
   debugpy.listen(("127.0.0.1", 5678))
   print("[dcc-mcp-maya] debugpy listening on 127.0.0.1:5678 — attach from IDE, then trigger your code")
   ```

   可选调用 `debugpy.wait_for_client()` 阻塞直到调试器连接（多数 MCP 驱动流程不必）。

3. 在 **Cursor / VS Code** 中使用 **Run and Debug → Python: Remote Attach**，主机 `127.0.0.1`、端口 `5678`。

4. 在 `src/dcc_mcp_maya/**/*.py`（或技能脚本）设断点，再从 MCP 触发工具；**仅当代码在 Maya 主线程执行时** 断点才会命中（与 Maya 脚本规则一致）。

**Rust（`dcc_mcp_core`）** 在 Maya 内调试成本较高（原生扩展）；可优先用日志，或在 Maya 外用小型 `mayapy` 复现导入 `dcc_mcp_core` 以加快原生调试。

## 5. 快速检查表

| 现象 | 处理 |
|------|------|
| MCP 404 / 连接被拒绝 | 插件是否加载？端口是否正确（`8765` 与 `9765`）？ |
| 看不到工具 | 极简模式：先调用 `load_skill("…")`（见 AGENTS.md）。 |
| 断点不命中 | 代码路径须在 Maya 内执行；确认已附加到正确的 Maya 进程。 |

## 相关

- [`getting-started.md`](./getting-started.md) — 首次 MCP 配置
- [`installation.md`](./installation.md) — `mayapy` / 插件 / `userSetup.py`
- 仓库 **AGENTS.md** — 渐进加载、亲和性、取消
