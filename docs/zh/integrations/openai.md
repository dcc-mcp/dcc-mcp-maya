# OpenAI API / GPT 集成指南


> `dcc-mcp-maya` 的厂商集成说明。此处内容从仓库根目录迁移过来，目的是让
> [`AGENTS.md`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) 成为根目录**唯一**的 agent 契约文件。
> 与厂商无关的内容应写入 `AGENTS.md`，而不是放在这里。
> `dcc-mcp-maya` 的 OpenAI 专有集成说明。
> 完整项目地图参见 [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md)。

---

## 这个项目做什么

`dcc-mcp-maya` 在 Autodesk Maya 内部直接嵌入了一个 MCP Streamable HTTP 服务。任何支持 MCP Streamable HTTP 的 OpenAI 客户端都可以调用 72+ 个 Maya 工具。

---

## 集成配置

如果你的 OpenAI 客户端（自定义聊天界面、agent 框架等）支持 MCP：

```
Endpoint: http://127.0.0.1:9765/mcp
Protocol: MCP Streamable HTTP（2025-03-26 规范）
```

多实例 gateway 模式下：
```
Endpoint: http://127.0.0.1:9765/mcp
```

---

## Function Calling 映射

MCP 工具可以自然映射到 OpenAI 的 function calling：

| OpenAI 概念 | MCP 对应物 |
|----------------|----------------|
| `functions` 列表 | `tools/list` 端点 |
| `function.name` | `{skill}__{script}`（例如 `maya_scene__new_scene`） |
| `function.arguments` | 发送到 `tools/call` 的 JSON 载荷 |
| `function_call` | `tools/call` 请求，异步时带 `_meta.progressToken` |

对于异步工具（`tools.yaml` 中标记 `execution: async`），服务会立即返回 `job_id`。轮询 `jobs_get_status` 跟踪进度 —— 类似于 OpenAI 的 `run` 状态轮询。`jobs_get_status` 需要配置 job 存储后端与异步任务能力；未配置时，异步工具会以同步方式执行。

---

## OpenAI 专有技巧

- **System prompt：** 在 system prompt 中包含 [llms.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms.txt) 的摘要，让模型知道可用的工具面。
- **工具选择：** 有 72+ 个工具，但 minimal mode 下初始 `tools/list` 很小（只有核心工具）。模型应学会在执行专项操作前先调用 `load_skill`。
- **异步处理：** 长时间渲染会返回 `job_id`。用同一个 `job_id` 调用 `jobs_get_status` 进行轮询。轮询间隔设置在合理范围（2–5 秒）。

---

## 相关阅读

- [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) — 统一的 agent 导航地图；通用指引保持单一真源
- [llms.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms.txt) — 一页纸核心参考
- [llms-full.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms-full.txt) — 完整 API 参考
- [README.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/README.md) — 面向人类的安装与总览
