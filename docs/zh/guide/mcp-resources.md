# Maya MCP 资源

Issue [#187](https://github.com/loonghao/dcc-mcp-maya/issues/187) 把
`dcc-mcp-maya` 接到 `dcc-mcp-core` 0.15.0 提供的 Rust
[`ResourceRegistry`][resource-handle]。开箱后，MCP 客户端会看到：

* **`scene://current`** —— 当前 Maya 场景的 JSON 快照
  （`pid`、`dcc`、`scene`、`selection`、`frame`、`frame_range`、
  `up_axis`、`units`、`version` 等）。Maya `scriptJob` 事件触发刷新；
  500 ms 节流，吸收批量导入引发的 `DagObjectCreated` 风暴。
* **`maya-cmds://help/<command>`** —— 任意 Maya 命令的
  `cmds.help(command, language="python")` 输出。
* **`maya-cmds://flags/<command>`** —— 通过
  `cmds.help(command, flags=True)` 列出该命令的所有 flag。
* **`maya-api://signatures/<class>`** ——
  `maya.api.OpenMaya` / `OpenMayaAnim` / `OpenMayaUI` 类的公共方法索引
  （例如 `maya-api://signatures/MFnMesh`）。
* **`maya-project://current`** —— 当前 Maya workspace 的根目录与
  `fileRule` 列表。

[resource-handle]: https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt

## 节流策略：`scene://current` 不会变贵

Maya 的 `DagObjectCreated` **每个节点触发一次**。导入 1000 个节点的
角色会连续触发 1000 次，没有节流时服务器会推 1000 帧
`notifications/resources/updated` SSE。

Maya 适配器用 lead-edge + trail-edge 计时器把这种风暴折叠到
**每 500 ms 至多一次发布**：

| 场景                       | 发布次数（典型）             |
|----------------------------|------------------------------|
| 单次编辑（重命名一个节点） | 1 次（lead-edge）            |
| 50 节点导入（50 ms）       | 1 次（500 ms 后 trail-edge） |
| 1000 节点导入（2 s）       | ≈5 次（每 500 ms 一次）      |
| 连续编辑风暴               | ≈2 次/秒（稳态）             |

构造 [`MayaResourceBinder`](#python-api) 时通过 `throttle_secs=...`
覆盖默认 0.5 秒。

## 配置

| 变量                          | 默认 | 效果                                            |
|-------------------------------|------|-------------------------------------------------|
| `DCC_MCP_MAYA_RESOURCES`      | `1`  | 设为 `0` 完全关闭 Maya 资源发布功能。           |

关闭后 `scene://current` 维持 core 默认的
`{"status": "no_scene_published"}`，三个 `maya-*://` scheme 也不会注册。
适合让嵌入宿主自己驱动 `scene://current`。

## Python API

```python
from dcc_mcp_maya import (
    MayaResourceBinder,    # SOLID 组合根
    install_resources,     # 一行式辅助
    SCHEME_MAYA_CMDS,
    SCHEME_MAYA_API,
    SCHEME_MAYA_PROJECT,
    DEFAULT_SCENE_EVENTS,        # 我们 hook 的 scriptJob 事件元组
    DEFAULT_SCENE_THROTTLE_SECS, # 节流默认值
)
```

`install_resources(server)` 在 `MayaMcpServer.register_builtin_actions`
里随 `register_project_tools` 自动调用。默认的快照源是
`MayaContextSnapshotProvider.collect`，与 `/v1/context` REST 端点
共用同一份场景状态。

## 现状：prompts（来自 examples / workflows）

core 0.15.0 已声明 `prompts: {listChanged: true}` 能力，
`prompts/list` 返回空数组。PR #373 实现了从 SKILL.md `examples` /
`workflows` 推导 prompt 的逻辑，但 0.15.0 wheel 仍然返回 `[]`。
等 core 把消费路径打通（0.15.1+），随 Maya 内置的 skill 自带的
`examples` 字段会自动出现在 `prompts/list` 里——Maya 侧无需改动。

## 参考

* [`AGENTS.md`](../../../AGENTS.md) —— SOLID binder 范式总览
  （`ReadinessBinder` / `ProjectToolsIntegration` / `MayaResourceBinder`）。
* [`docs/zh/guide/scene.md`](./scene.md) —— 现有的场景信息工具表面，
  与 `scene://current` 同源。
