# 简介

**dcc-mcp-maya** 是 [DCC-MCP](https://github.com/loonghao/dcc-mcp-core) 生态系统的 Maya 专属集成层。

它将符合标准的 **MCP Streamable HTTP 服务器**（2025-03-26 规范）直接嵌入 Maya 中运行 — 无需任何外部网关或独立的 IPC 进程。

## 适用人群

| 人群 | 使用场景 |
|------|----------|
| **Maya TD / TA** | 编写自定义 Action 脚本，供 AI Agent 通过 MCP 调用 |
| **AI 应用开发者** | 从 LLM 宿主通过 MCP 协议编程控制 Maya |
| **DCC 集成开发者** | 以 Maya 实现为参考，接入其他 DCC 软件 |

## 架构

```
┌─────────────────────────────────────────────────────────┐
│  Maya（内嵌 Python）                                     │
│                                                          │
│  import dcc_mcp_maya                                    │
│  handle = dcc_mcp_maya.start_server(port=8765)          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  McpHttpServer  (dcc-mcp-core)                  │   │
│  │  POST /mcp  ──►  ToolRegistry                   │   │
│  │  GET  /mcp  ──►  SSE 流                         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────┘
                               │  http://127.0.0.1:8765/mcp
┌─────────────────────────────▼───────────────────────────┐
│  MCP 宿主（Claude Desktop / OpenClaw / Cursor / …）      │
└─────────────────────────────────────────────────────────┘
```

## 核心概念

### Skill（技能包）

Skill 是基于目录的包，包含 Python action 脚本和 `SKILL.md` 清单文件。每个脚本会自动成为一个 MCP 工具。

```
maya-scene/
├── SKILL.md          ← 元数据：name、description、tags
└── scripts/
    ├── new_scene.py
    ├── save_scene.py
    └── list_objects.py
```

### Action 命名规则

```
{skill_name.replace("-", "_")}__{script_stem}
# 例如：maya_scene__new_scene
#       maya_primitives__create_sphere
```

### Skill 搜索路径

按优先级从高到低解析：

1. `extra_skill_paths` 参数
2. 本包内置的 `skills/` 目录
3. `DCC_MCP_MAYA_SKILL_PATHS` 环境变量（Maya 专属）
4. `DCC_MCP_SKILL_PATHS` 环境变量（全局回退）
5. 平台默认 Skill 目录

## 下一步

- [快速开始](./getting-started) — 5 分钟让 Maya 与 Claude Desktop 联通
- [Action 完整列表](./actions) — 所有内置 MCP 工具的完整目录
- [高级用法](./advanced) — 自定义 Skill、主线程调度
