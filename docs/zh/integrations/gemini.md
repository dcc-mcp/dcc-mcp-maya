# Google Gemini / Vertex AI 集成指南


> `dcc-mcp-maya` 的厂商集成说明。此处内容从仓库根目录迁移过来，目的是让
> [`AGENTS.md`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) 成为根目录**唯一**的 agent 契约文件。
> 与厂商无关的内容应写入 `AGENTS.md`，而不是放在这里。
> `dcc-mcp-maya` 的 Gemini 专有集成说明。
> 完整项目地图参见 [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md)。

---

## 这个项目做什么

`dcc-mcp-maya` 在 Autodesk Maya 内部直接嵌入了一个 MCP Streamable HTTP 服务。Gemini（通过兼容 MCP 的客户端或自定义集成）可以通过 HTTP 发现并调用 72+ 个 Maya 工具。

---

## Gemini 的强项

Gemini 擅长**代码生成**与**结构化输出解析**。在使用 `dcc-mcp-maya` 时可以重点利用这两点：

### 1. Skill 脚本生成
让 Gemini 基于 `dcc_mcp_maya.api` 辅助函数生成新的 Maya skill 脚本：

```python
from dcc_mcp_maya.api import with_maya, maya_success

@with_maya
def batch_rename(prefix: str, suffix: str = "") -> dict:
    """Rename selected objects with prefix and suffix."""
    import maya.cmds as cmds
    selected = cmds.ls(selection=True) or []
    renamed = []
    for obj in selected:
        new_name = f"{prefix}{obj}{suffix}"
        renamed.append(cmds.rename(obj, new_name))
    return maya_success("Renamed objects", renamed=renamed, count=len(renamed))
```

### 2. 结构化工具结果
Gemini 对嵌套 JSON 的处理很好，可以直接解析 `maya_success` / `maya_error` 的结果：

```json
{
  "success": true,
  "message": "Created sphere",
  "context": {
    "object_name": "pSphere1",
    "radius": 1.0
  }
}
```

### 3. Skill 搜索与发现
用 Gemini 的检索能力配合内置发现工具：
- `find_skills("render batch")` → 返回带描述的匹配 skill
- `search_tools(query="bake", tags=["animation"])` → 过滤后的搜索结果

---

## 集成配置

如果你的 Gemini 客户端支持基于 HTTP 的 MCP，请配置：

```
Endpoint: http://127.0.0.1:9765/mcp
Protocol: MCP Streamable HTTP（2025-03-26 规范）
```

多实例 gateway 模式下：
```
Endpoint: http://127.0.0.1:9765/mcp
```

---

## Gemini 专有技巧

- **代码优先的工作流：** Gemini 可以一次写出完整的 skill 包。一次性生成 `SKILL.md`、`tools.yaml` 和 `scripts/*.py`，然后放进 `DCC_MCP_MAYA_SKILL_PATHS` 列出的某个目录。
- **图像理解：** 把 `capture_viewport` 返回的 base64 PNG 回喂给 Gemini，用于视觉状态验证。

---

## 相关阅读

- [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md) — 统一的 agent 导航地图；通用指引保持单一真源
- [llms.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms.txt) — 一页纸核心参考
- [llms-full.txt](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/llms-full.txt) — 完整 API 参考
- [README.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/README.md) — 面向人类的安装与总览
