# 本地 MCP 与调试（概要）

完整步骤（Cursor MCP、`debugpy` 附加、网关端口）见英文页 **[Local MCP + debugging](/guide/local-mcp-debug)**（与代码库同步更新）。

**默认 MCP 地址：**

- 单机 Maya：`http://127.0.0.1:8765/mcp`
- 多实例网关（若启用）：`http://127.0.0.1:9765/mcp`

**Cursor：** 将仓库内 `examples/mcp/cursor-maya-streamable-http.json` 中的 `mcpServers` 片段合并进 Cursor 的 MCP 配置（字段名以你本机 Cursor 版本为准）。

**详细说明（英文）：** [Local MCP + debugging](/guide/local-mcp-debug)

**Windows 一键链编：** `just maya-dev-debug-win`（见 `tools/maya-dev-build-link-core-win.ps1`）。
