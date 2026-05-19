# 测试策略

测试套件应该证明两个契约：

1. 正常路径会执行用户请求的 Maya 操作。
2. 失败路径会返回可预测、可行动的错误 envelope，而不是让 Maya 崩溃、
   挂住请求，或者静默成功。

## 保留

- 跨真实边界的 E2E 测试：mayapy skill 执行、MCP HTTP、插件加载/卸载、
  sidecar 生命周期、gateway discovery、readiness 和 cancellation。
- 难以在 Maya 中稳定触发的纯决策逻辑单测：环境变量解析、schema/manifest
  形状、端口选择、registry 清理、prompt guard、结果 envelope 归一化。
- 约束整个仓库不漂移的 lint 类测试：skill metadata、Python 3.7 语法、
  文档中英文 parity，以及禁用 import。

## 减少或替换

- 纯 importability 检查通常应该变成行为检查。只有 public API 兼容性或
  optional core symbol 才值得保留 import 测试。
- 只断言 `is not None`、`hasattr` 或 `"success" in result` 的测试，应该断言
  完整契约：`success`、`message`、`error`、关键 `context` 字段，以及发生或
  没有发生的 side effect。
- 逐行复刻实现的重 mock 测试，能上移就上移一层，尤其是 skill。优先调用
  script entry point，并提供一个小的 fake `maya.cmds` surface。

## 错误 Envelope 清单

每个会校验输入或触碰 Maya 状态的 skill，至少应该有一个 negative-path 测试
检查：

- `success is False`
- 稳定的 `message`
- 有用的 `error` 文本
- 当调用方可以修复请求时，包含 `context.possible_solutions`
- 校验失败后没有发生 mutation

E2E 测试也应该覆盖代表性的失败场景，而不只是成功的 Maya 操作。例如缺失
节点、非法 transform vector、语法错误、禁用任意脚本、dirty-scene
`cmds.file` prompt，以及返回结构化失败 payload 的 HTTP tool call。

## 当前缺口

- 更多 mayapy E2E 应该覆盖 scene、geometry、material、render 和 pipeline
  skill 的失败路径。
- 一旦 gateway endpoint 在 CI 中可用，HTTP E2E 应该同时覆盖 MCP
  `tools/call` 和 gateway REST 的代表性结构化失败。
- 一些旧测试仍然只证明 symbol 存在。修改相关功能时，顺手把它们转换为行为
  契约测试。
