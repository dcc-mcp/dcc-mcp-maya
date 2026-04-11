# 什么是 dcc-mcp-maya？

`dcc-mcp-maya` 是 [DCC-MCP](https://github.com/loonghao/dcc-mcp-core) 生态系统的 **Maya 专属集成层** — 该框架让 AI Agent 通过 [Model Context Protocol](https://modelcontextprotocol.io) 控制数字内容创作（DCC）工具。

## 它解决什么问题

让 AI 模型可靠地控制 Maya 需要：

1. AI 能理解的**标准协议**（→ MCP）
2. **运行在 Maya 内部**的服务器，以便在主线程调用 `maya.cmds`
3. 覆盖常见 Maya 工作流的**预置 Action**

`dcc-mcp-maya` 通过一次 `pip install` 提供以上全部能力。

## 架构

```
┌─────────────────────────────────────────────────────────┐
│  Maya（内嵌 Python）                                      │
│                                                          │
│  import dcc_mcp_maya                                     │
│  handle = dcc_mcp_maya.start_server(port=8765)           │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  McpHttpServer  (dcc-mcp-core)                  │    │
│  │  POST /mcp  ──►  ActionRegistry                 │    │
│  │  GET  /mcp  ──►  SSE 流                         │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────┘
                           │  http://127.0.0.1:8765/mcp
┌─────────────────────────▼───────────────────────────────┐
│  MCP 客户端（Claude Desktop / Cursor / OpenClaw / …）     │
└─────────────────────────────────────────────────────────┘
```

## 核心概念

| 概念 | 说明 |
|------|------|
| **Skill（技能）** | 包含 `SKILL.md` + `scripts/` 的目录。定义一组相关 Action。 |
| **Action** | `scripts/` 下的单个 Python 脚本。注册为一个 MCP 工具。 |
| **MayaMcpServer** | 封装 `dcc-mcp-core` 的 `McpHttpServer` 的 Python 类。 |
| **SkillCatalog** | 自动发现系统，扫描目录中的 `SKILL.md` 文件。 |

## 适用人群

- **Maya TD/TA** — 编写自定义 Action 自动化流程，让 AI Agent 调用
- **AI 应用开发者** — 构建能创建和操作 Maya 场景的 Claude/GPT/Cursor 工作流
- **DCC 集成开发者** — 以此作为接入其他 DCC 工具的参考实现

## 下一步

- [快速开始](/zh/guide/getting-started) — 5 分钟内完成安装并运行首次 MCP 会话
- [Action 列表](/zh/guide/actions) — 浏览 200+ 内置 Action
- [高级用法](/zh/guide/advanced) — 自定义技能、环境变量、热重载
