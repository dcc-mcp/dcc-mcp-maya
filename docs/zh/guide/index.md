# 简介

**dcc-mcp-maya** 是 [DCC-MCP](https://github.com/loonghao/dcc-mcp-core) 生态系统的 Maya 专属集成层。

它让 Maya 通过符合标准的 **MCP Streamable HTTP** 表面对外服务。插件部署默认使用 Rust `dcc-mcp-server` sidecar 作为标准运行时：HTTP 与 gateway 工作留在 Maya 进程外，场景操作再通过 Maya-safe Qt bridge 调度回 Maya。

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
│  dcc_mcp_maya_plugin.py                                 │
│  Qt dispatcher + sidecar bridge                         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  DccServerBase + McpHttpServer                  │   │
│  │  POST /mcp  ──►  ToolRegistry / tools/call      │   │
│  │  GET  /mcp  ──►  SSE 流                         │   │
│  │  /v1/*       ─►  readiness, search, resources   │   │
│  └──────────────────────┬──────────────────────────┘   │
│                         │ HostExecutionBridge          │
│  ┌──────────────────────▼──────────────────────────┐   │
│  │  MayaHost / dispatcher / skill executor         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────┘
                               │  http://127.0.0.1:9765/mcp
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

### 渐进式加载

本包内置 24 个 Maya Skill 包。Minimal mode 启动时只加载核心 bootstrap 与 scene 工具；未加载的 Skill 仍可通过 `dcc_capability_manifest`、`search_skills` 或 `search_tools` 发现。

只有任务需要某个领域能力时再加载对应 Skill：

```python
load_skill("maya-primitives")
```

### Skill 搜索路径

按优先级从高到低解析：

1. `extra_skill_paths` 参数
2. 本包内置的 `skills/` 目录
3. `DCC_MCP_MAYA_SKILL_PATHS` 环境变量（Maya 专属）
4. `DCC_MCP_SKILL_PATHS` 环境变量（全局回退）
5. 平台默认 Skill 目录

每个环境变量条目都是一个 skill 搜索根目录：它可以直接是 skill 包，也可以是多个
子 skill 包的父目录。Rez 包通常在 `package.py` 中追加 `{root}/skills`；环境变化后，
Maya 需要重启或重新注册，gateway search 与 `load_skill` 才会看到新的路径。

## 下一步

- [快速开始](./getting-started) — 5 分钟让 Maya 与 Claude Desktop 联通
- [MCP Tools 指南](./mcp-tools) — 面向用户的示例与 Skill 路由建议
- [高级用法](./advanced) — 自定义 Skill、主线程调度、`defer=True` 长任务执行
- [单机多实例部署](./multi-instance) — 在同一台工作站上运行多个 Maya 实例
