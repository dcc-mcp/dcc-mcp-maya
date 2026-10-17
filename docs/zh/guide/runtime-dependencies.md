# Maya 运行时依赖

Maya 提供 Python 解释器。Adapter 的必需运行时依赖仅包括标准库、Maya/插件拥有的模块和自家的 DCC-MCP Core/server。构建与开发依赖单独管理。可执行的仓库规则见 [AGENTS.md](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/AGENTS.md#adapter-runtime-dependency-boundary)。

## 版本检查不再引入运行时包

`_version_contract.py` 是兼容 Python 3.7、导入开销很小的独立模块。它只处理精确包版本的标识与排序，以及本仓库固定的稳定版 `>= minimum, < maximum` 范围，**不是**通用 requirement、marker、resolver 或 specifier 库。构建工具仍使用 `packaging`。实现根据 [Python 版本规范](https://packaging.python.org/en/latest/specifications/version-specifiers/) 独立编写。

已有 ASCII 公共版本输入保持原含义：任意长度数字 release 与尾零相等；前导零和 `v` 归一化；epoch；alpha/beta/rc 别名；pre/dev/post 组合；`0.20.0-1` 这类隐式 post；local 标签的大小写、分隔符与数字归一化。解析匹配完整输入，格式错误时拒绝，不截取数字前缀。epoch 和 local 标签继续参与来源标识相等比较。

`1.0+K` 等非 ASCII local 标签会被拒绝。packaging 24.0 的 Unicode 大小写匹配曾意外接受这些规范以外的字符串，26.3 已拒绝它们。这是明确的严格化差异；规范规定的 ASCII 拼写仍受支持。

| 使用位置 | 操作与兼容策略 |
| --- | --- |
| `headless.serve_headless` | 按精确版本排序检查原有 `0.19.64` 下限。该版本的 rc/dev 仍低于下限，post/local 仍高于下限；更晚版本的 prerelease 仍按顺序高于此历史下限。 |
| 安装生命周期与 setup 验证 | 统一稳定版范围 `>=0.20.0,<0.21.0`。范围内 final/post/local 可接受，全部 pre/dev 拒绝。 |
| 内嵌 Core 来源校验 | 精确标识相等比较，包括 epoch/local；保留重复元数据头、不可变快照、路径与哈希校验。 |
| 启动诊断 | 归一化与数字排序；非法值仍不导致启动失败，并保持确定性排序。 |
| 模块组装器 | 仅构建时使用 `packaging` 验证 wheel 元数据并排序 PyPI 候选。逐项跳过非法/pre/dev 候选，避免一个候选使整个查询退回最低版本。 |

显式的 stable-only 安装策略与 0.9.36 ZIP 内的 `packaging 24.0` 一致。此前 pip 安装的无上界 `packaging>=21.3` 会使行为随环境改变：26.3 自动接受 `0.20.1rc1` 这类范围内部的预发布版本。此类 pip 环境现在会一致地拒绝它们。这是有意的兼容策略统一，不代表历史上所有 `packaging` 版本行为相同。headless 的排序策略保持不变。

Core 当前公开的 `SemVer` 有意忽略预发布后缀，其私有辅助函数也会截断 release 分量，两者都不能安全替代精确元数据标识。未来可将此独立模块迁移到 Core 公开、轻量导入的 API；各 adapter 不应自行扩展通用解析器。

## 门禁与分发大小

- `test_version_contract.py` 使用仅开发环境中的 `packaging` 作差分参考，检查精确版本归一化、排序、相等与稳定范围，包括别名和非法输入。
- `test_adapter_runtime_dependencies.py` 检查必需依赖、运行时 extra 声明及 adapter/bootstrap 导入，区分宿主拥有的模块、现有有限范围内的可选 debugger/YAML/metadata 回退与强制第三方依赖。
- Release 和 Mayapy CI 对真实 portable/pipeline ZIP 运行 `test_offline_module_bootstrap.py`，检查两个运行时目录。新的 `-I -S` 进程在没有 `pip`、site-packages 或 `packaging` 的情况下执行 bootstrap、公开 headless 入口和完整 Core 来源验证。该 smoke 使用模拟的宿主/server，不替代需要授权宿主的 E2E。

使用相同 adapter 版本 0.9.36、Core 0.20.44 和 server 0.20.45 的受控 Linux 构建结果：

| ZIP | 之前 | 之后 | 节省 |
| --- | ---: | ---: | ---: |
| Portable | 105,998,457 bytes | 105,893,395 bytes | 105,062 bytes（0.099%） |
| Pipeline | 105,996,724 bytes | 105,891,662 bytes | 105,062 bytes（0.099%） |

两个运行时目录共移除 46 个 vendor 文件、348,344 bytes 解压大小；新增的小型版本模块抵消一部分收益。包大小仍主要来自原生 Core 和 server。它们的平台/ABI 布局与共享 Runtime 分发需独立评审；本次不会删除 Python 3.7 兼容载荷或替换自家运行时。
