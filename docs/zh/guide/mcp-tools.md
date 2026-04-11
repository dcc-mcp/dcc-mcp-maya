# AI Agent MCP Tools 使用指南

本指南面向希望通过自然语言控制 Maya 的 **AI Agent 用户**（非开发者），适用于 Claude Desktop、Cursor 或任何兼容 MCP 的客户端。

## 工作原理

`dcc-mcp-maya` 在 Maya 内运行并配置好 AI 客户端后，你可以用中文或英文描述任务。AI 模型将请求转换为一个或多个 MCP 工具调用。

你不需要知道 Action 名称 — 只需描述你想做什么。

## 示例对话

### 创建对象

> **你：** 创建一个名为 "planet" 的多边形球体，40 段，半径 3，位于原点

AI 调用 `maya_primitives__create_sphere`，参数自动填写。

---

> **你：** 创建一个 5x5 的立方体网格，每个间距 1 个单位

AI 通过 `maya_expressions__execute_python` 循环调用创建逻辑。

### 材质与着色

> **你：** 创建一个金色金属材质，应用到所有选中对象

AI 依次调用：
1. `maya_materials__create_material`（aiStandardSurface）
2. `maya_materials__set_material_attribute`（金属度=1，暖金色）
3. `maya_materials__assign_material`

---

> **你：** 让 hero_ball 对象变成红色且有光泽

### 动画

> **你：** 将 "camera1" 设置为在 120 帧内围绕原点旋转

> **你：** 将角色绑定上的所有约束烘焙为关键帧

> **你：** 将 "char_root" 的动画导出为 .anim 文件到 C:/exports/

### 场景管理

> **你：** 截取当前视口的截图

AI 调用 `maya_render__capture_viewport` 并返回图像。

---

> **你：** 将场景保存到 "C:/projects/hero_shot/v003.ma"

> **你：** 场景中有哪些对象？按类型列出。

### 绑定

> **你：** 将 "hero_mesh" 绑定到从 "root_jnt" 开始的骨骼

> **你：** 将 "hero_mesh_v1" 的蒙皮权重复制到 "hero_mesh_v2"

## 提示技巧

### 明确对象名称

不好的描述：
> 把球向上移动

好的描述：
> 将 "hero_ball" 向上移动 5 个单位（Y 轴平移 += 5）

### 指定类型

> 选择场景中所有多边形网格

> 创建一个 aiStandardSurface 材质（不是 Lambert）

### 组合操作

> 导入文件 "C:/assets/tree.fbx"，重命名为 "bg_tree_01"，放置在 (10, 0, 5)，并为其指定 "bark_mat" 材质

AI 将此分解为 4 个顺序工具调用。

### 先查询再操作

> 当前场景有什么内容？然后创建一个名为 "environment" 的组，将所有静态网格放入其中。

## 支持的 AI 客户端

| 客户端 | 状态 | 备注 |
|--------|------|------|
| [Claude Desktop](https://claude.ai/download) | ✅ 推荐 | 最佳多工具推理能力 |
| [Cursor](https://cursor.com) | ✅ | 适合脚本工作流 |
| [OpenClaw](https://github.com/loonghao/openclaw) | ✅ | 轻量级命令行客户端 |
| 任何 OpenAI 兼容客户端 | ⚠️ | 须支持 MCP Streamable HTTP |

## 注意事项

- Action 在 **Maya 主线程**执行 — 耗时较长的操作可能短暂暂停 UI
- `capture_viewport` 返回 **base64 编码的 PNG** — 并非所有客户端都能内联显示图像
- MEL/Python 执行（`execute_mel`、`execute_python`）赋予 AI 完整的 Maya 访问权限 — 请在可信环境中使用
- Maya 内可以撤销操作，但 MCP 服务器不追踪撤销历史
