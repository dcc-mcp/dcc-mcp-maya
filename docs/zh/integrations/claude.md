# Claude Desktop / Anthropic API 集成指南


> `dcc-mcp-maya` 的厂商集成说明。此处内容从仓库根目录迁移过来，目的是让
> [`AGENTS.md`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) 成为根目录**唯一**的 agent 契约文件。
> 与厂商无关的内容应写入 `AGENTS.md`，而不是放在这里。
> `dcc-mcp-maya` 的 Claude 专有集成说明。
> 完整项目地图参见 [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md)。

---

## 这个项目做什么

`dcc-mcp-maya` 在 Autodesk Maya 内部直接嵌入了一个 MCP Streamable HTTP 服务。Claude Desktop（或任何使用 MCP 的 Anthropic API 客户端）可以通过 HTTP 调用 72+ 个 Maya 工具，无需外部 gateway 进程。

---

## Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

**文件位置：**
- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`

如果使用 gateway 的多实例模式，请改用 gateway 端口：
```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

修改后重启 Claude Desktop。

---

## 渐进式加载 —— 对 Claude 很重要

默认情况下，`dcc-mcp-maya` 以 **minimal mode** 启动，只有少量内置工具处于激活状态：
- `execute_python`、`execute_mel`
- `get_scene_info`、`get_selection`、`get_session_info`
- `search_tools`、`list_skills`、`load_skill`

**其余所有 skill 以 `__skill__<name>` 桩工具的形式出现。** 当 Claude 需要某个未加载 skill 中的工具时，应：

1. 调用 `load_skill("maya-primitives")` 展开该 skill。
2. 然后调用目标工具（例如 `maya_primitives__create_sphere`）。

这样可以让初始的 `tools/list` 保持精简，便于 Claude 快速解析。

---

## Claude 专有技巧

- **视口反馈：** 要求 Claude 在几何体改动后调用 `capture_viewport`。返回结果是一张 base64 编码的 PNG，Claude 可以在对话中"看到"它。
- **取消：** 对于长时间渲染，Claude 可以发送 `notifications/cancelled`。轮询 `check_maya_cancelled()` 的 skill 脚本会干净退出。
- **代码执行：** 优先使用 `search_skills` → `load_skill` → 带 `inputSchema` 的强类型工具。只有在没有 skill 覆盖时才使用 `execute_python`（Maya 内批量循环、OpenMaya 缺口、一次性操作）。运维侧可以用 `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON=1` 或 `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1` 禁用它。

---

## 快速测试 Prompt

> "在 Maya 里创建一个红色球体"
> "列出场景中所有摄像机，并选中透视摄像机"
> "截取视口，让我看到当前状态"
> "加载 maya-animation skill，并在第 10 帧给球体的 translateY 打一个关键帧"

---

## 相关阅读

- [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) — 统一的 agent 导航地图；通用指引保持单一真源
- [llms.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms.txt) — 一页纸核心参考
- [llms-full.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms-full.txt) — 完整 API 参考
- [README.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/README.md) — 面向人类的安装与总览
