# Cursor 编辑器集成指南


> `dcc-mcp-maya` 的厂商集成说明。此处内容从仓库根目录迁移过来，目的是让
> [`AGENTS.md`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) 成为根目录**唯一**的 agent 契约文件。
> 与厂商无关的内容应写入 `AGENTS.md`，而不是放在这里。
> `dcc-mcp-maya` 的 Cursor 专有集成说明。
> 完整项目地图参见 [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md)。

---

## 这个项目做什么

`dcc-mcp-maya` 在 Autodesk Maya 内部直接嵌入了一个 MCP Streamable HTTP 服务。Cursor 通过其 MCP server 支持，可以在你编辑代码的同时调用 Maya 工具，从而在代码改动与 3D 场景状态之间形成紧密的反馈回路。

---

## Cursor 配置

在 Cursor Settings → MCP Servers 中添加：

```json
{
  "maya": {
    "url": "http://127.0.0.1:9765/mcp"
  }
}
```

多实例 gateway 模式下：
```json
{
  "maya": {
    "url": "http://127.0.0.1:9765/mcp"
  }
}
```

---

## Cursor 专有工作流

### 1. Skill 脚本开发（编辑 → 测试 → 迭代）
`dcc-mcp-maya` 在 Cursor 中的理想工作流：

1. **编辑** skill 脚本 `src/dcc_mcp_maya/skills/maya-my-feature/scripts/my_tool.py`。
2. **保存** —— 如果开启了热重载（`DCC_MCP_MAYA_HOT_RELOAD=1`），服务会自动拾取改动。
3. **测试** —— 让 Cursor 调用该工具：`"Run my_tool with radius=2"`。
4. **验证** —— `"Capture the viewport"`，以 base64 PNG 形式查看结果。

### 2. Skill 的即时代码评审
把 skill 脚本粘贴进 Cursor 并提问：
> "评审这个 Maya skill 脚本的线程安全性。它需要 `affinity: main` 吗？"

Cursor 可以交叉比对 `tools.yaml` 与脚本内容，来校验 affinity 声明。

### 3. 跨 Skill 重构
Cursor 具备代码库感知的编辑能力，适合批量改动：
> "把所有使用 `error_result(..., str(exc))` 的 skill 改成使用 `maya_from_exception(exc, ...)`"

---

## Cursor 专有技巧

- **热重载：** 启动服务前设置 `DCC_MCP_MAYA_HOT_RELOAD=1`。Cursor 对 skill 脚本的改动会立即生效，无需重启 Maya。
- **终端集成：** 用 Cursor 的集成终端在提交新 skill 前运行 `python tools/lint_skill_affinity.py`。
- **可组合性：** Cursor 可以生成多文件 skill 包。在一次会话内创建 `SKILL.md`、`tools.yaml`、`groups.yaml` 和 `scripts/*.py`。

---

## 相关阅读

- [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) — 统一的 agent 导航地图；通用指引保持单一真源
- [llms.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms.txt) — 一页纸核心参考
- [llms-full.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms-full.txt) — 完整 API 参考
- [README.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/README.md) — 面向人类的安装与总览
