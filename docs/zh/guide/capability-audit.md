# Maya Agent 能力审计

本文档记录 Maya 适配器的领域能力与验收边界，不表示已经实现全部 Maya 命令或插件 API。复用结论前请重新确认运行时、插件版本和未解决的 issue。

## 证据等级

- **已实现**：存在已声明的类型化 action 和可执行实现。
- **单元验证**：受控测试验证了约定行为，但不代表真实主机行为。
- **主机验证**：在指定主机上执行并读回了结果。
- **受限**：依赖版本、插件、渲染器、许可证或格式。
- **缺失 / 未验证**：没有找到支持的类型化路径，或验收仍未完成。

## 领域登记

| 领域 | 已实现表面 | 缺口 / 后续验收 |
|---|---|---|
| 场景与对象发现 | `maya-scene` 提供层级、选择、类型/模式搜索、节点引用、变换、边界框和相机 | 结果未限制大小；需验证重名叶节点、实例、引用和超大场景。 |
| 参数与依赖图 | `maya-attributes` CRUD；`maya-node-graph` 图查询与编辑；`maya-cmds://` / `maya-api://` 资源发现 | 需按属性类型覆盖类型、锁定和连接约束。 introspection 或任意执行不等于类型化命令覆盖。 |
| 多边形 / NURBS 编辑 | 基础体、放样、旋转成面、数组、轴心、镜像、合并/拆分、清理和细分 | #492 仍开放；类型化 extrude/bevel/inset/boolean/edge-loop 尚未纳入审计声明。 |
| UV | UV 集创建/删除/复制、投影、展开、归一化、自动 UV 以及 UV/壳查询 | #514 修复了命名集计数和不改变活动集的壳读取；仍需 UDIM 和多形状测试。 |
| 材质与纹理 | 材质创建/赋值/读回、属性、着色组查询和预设 | #495 的纹理绑定、重载/重路径和 Arnold 烘焙仍缺失。 |
| 互操作 | 通用导入、FBX 导入/导出、OBJ 导出、Alembic 导出、USD 同步和原生资产导入 | 本批次补齐 USD 插件与原生 translator 准备；SpeedTree 的单位、轴向和材质保真仍有限。 |
| 作业与取消 | Core 作业状态、适配器 dispatcher 和取消辅助 | 原生导入是单体调用，`async` 不表示可中断；必须验证终态、内层失败和重试去重。 |
| 安装与发现 | 安装/验证/卸载、最小技能加载和类型化插件生命周期 | #491 与 #490 仍开放；需验证全新主机、包来源以及 search/load/describe/call。 |

## 第 1 批：互操作可靠性

通用导入现在会为 `.usd`、`.usda` 和 `.usdc` 准备 `mayaUsdPlugin`，选择原生 USD translator，在加载插件前拒绝目录，并继续限制返回的节点数。FBX 导入声明为异步并提供 300 秒提示。新增测试覆盖 USD 扩展名、插件顺序、缺失插件、目录拒绝和节点限制。

## SpeedTree 验收矩阵

生产交接必须包含绝对源路径、哈希、导出设置、单位/上轴、纹理、预期网格/材质、LOD 布局及风动画范围。当前仓库不提交源资产。

| 格式 | Maya 依赖 / 路径 | 必须读回 | 边界 |
|---|---|---|---|
| FBX | `fbxmaya`；需要显式选项时使用 `import_fbx` | 节点、层级、边界、UV、着色组、纹理路径和动画曲线 | 插件状态会影响结果；几何不代表运行时风或 LOD。 |
| OBJ | `objExport`；使用 `import_file` | 网格/多边形/UV 计数、边界、MTL 和纹理路径 | 几何/材质互操作与动画/程序化风分开验收。 |
| Alembic | `AbcImport`；使用 `import_file` | 网格、UV、缓存节点、采样帧变化和边界 | 着色重建与交互式 LOD 另行验收。 |
| USD | `mayaUsdPlugin`；原生 `import_file` 或代理同步 | 原生网格或明确代理 stage、单位/上轴、绑定、依赖和时间采样 | 原生转换与 stage 组合的可编辑性不同。 |

每次导入都应在一次性场景中执行，等待 Core 作业终态，再检查内层结果并执行只读校验。保存并重新打开代表性输出后才能声明 artifact 验收；合成网格只是 translator smoke，绿色 CI 也不等于授权 GUI 验收。

## 真实 SpeedTree 验收（2026-09-07）

此前验证证明了几何持久化，但没有证明完整的材质、坐标、风或 LOD 保真。OBJ/Alembic 与 FBX/USD 存在比例和轴向差异；在没有权威源尺寸/上轴契约前，不应自动归一化。仍需生产方提供运动/LOD 样本和预期帧范围。

## 官方参考

- [Autodesk Maya 命令参考](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/index.html)
- [Maya USD](https://github.com/Autodesk/maya-usd)
- [Core 公共契约](https://github.com/dcc-mcp/dcc-mcp-core/blob/main/llms.txt)
- 开放工作：[#490](https://github.com/dcc-mcp/dcc-mcp-maya/issues/490)、[#491](https://github.com/dcc-mcp/dcc-mcp-maya/issues/491)、[#492](https://github.com/dcc-mcp/dcc-mcp-maya/issues/492)、[#493](https://github.com/dcc-mcp/dcc-mcp-maya/issues/493)、[#494](https://github.com/dcc-mcp/dcc-mcp-maya/issues/494)、[#495](https://github.com/dcc-mcp/dcc-mcp-maya/issues/495)。
