# Anthropic API / Claude Code 集成指南


> `dcc-mcp-maya` 的厂商集成说明。此处内容从仓库根目录迁移过来，目的是让
> [`AGENTS.md`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) 成为根目录**唯一**的 agent 契约文件。
> 与厂商无关的内容应写入 `AGENTS.md`，而不是放在这里。
> `dcc-mcp-maya` 的 Anthropic 专有集成说明。
> 完整项目地图参见 [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md)。

---

## 这个项目做什么

`dcc-mcp-maya` 在 Autodesk Maya 内部直接嵌入了一个 MCP Streamable HTTP 服务。任何支持 MCP Streamable HTTP 的 Anthropic API 客户端（Claude Code、Claude Desktop 或自定义集成）都可以发现并调用 72+ 个 Maya 工具。

---

## 集成配置

### Claude Desktop
`claude_desktop_config.json` 的具体片段参见 [`docs/integrations/claude.md`](claude.md)。

### Claude Code / 自定义 Anthropic 客户端
在 MCP 客户端中配置：

```
Endpoint: http://127.0.0.1:9765/mcp
Protocol: MCP Streamable HTTP（2025-03-26 规范）
```

多实例 gateway 模式下：
```
Endpoint: http://127.0.0.1:9765/mcp
```

---

## Anthropic 专有技巧

- **工具调用与 thinking 配合：** Claude 的 extended thinking 与 `dcc-mcp-maya` 的 minimal mode 非常契合。Claude 可以先推理应加载哪个 skill，再调用 `load_skill`，最后执行具体工具。
- **Computer use 协同：** 如果你在 MCP 之外同时使用 Claude 的 computer use 能力，`capture_viewport` 在 Maya 内部提供了同样的视觉反馈回路。
- **结构化输出：** Claude 能很好地处理 `maya_success` / `maya_error` 返回的嵌套 `ToolResult` 字典。工具失败时，用 `possible_solutions` 字段引导 Claude 自行恢复。
- **长上下文：** 对于复杂的场景操作，把 `get_scene_info` 的输出作为上下文提供。层次化的 DAG 描述有助于 Claude 推理对象之间的关系。

---

## Prompt 编写建议

为 `dcc-mcp-maya` 编写 Anthropic prompt 时：

1. **说明 minimal mode 行为：** 提醒 Claude 初始只加载核心工具，必须调用 `load_skill` 才能扩展工具面。
2. **鼓励视口校验：** 加上"几何体改动后调用 `capture_viewport` 做视觉验证"。
3. **说明可取消性：** 对于异步操作，说明行为良好的 skill 会轮询 `check_maya_cancelled()`，因此 Claude 可以安全地取消长任务。

---

## 相关阅读

- [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) — 统一的 agent 导航地图；通用指引保持单一真源
- [llms.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms.txt) — 一页纸核心参考
- [llms-full.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms-full.txt) — 完整 API 参考
- [README.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/README.md) — 面向人类的安装与总览
