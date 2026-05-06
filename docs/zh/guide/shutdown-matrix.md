# 退出场景安全矩阵

Issue [#186](https://github.com/loonghao/dcc-mcp-maya/issues/186) 强化了 Maya MCP 插件在
**非协作式退出**（崩溃、`kill -9`、任务管理器结束进程等）下的清理能力，避免
`FileRegistry` 条目长时间泄漏。运维同学常见的症状
"Maya 退出后 plugin 服务好像没有退出"（`list_dcc_instances` 继续通告一个刚刚关闭的 Maya）
由两处协同修复：

1. **core 侧（上游）**——`handle.shutdown()` 正常退出时自动从 `FileRegistry` 注销。
2. **本页（Maya 侧）**——四个互相独立的安全网，覆盖各种非协作式退出路径。

## 四个安全网

每个安全网都可通过环境变量独立关闭，方便嵌入方按自己的 shutdown 编排取舍。

| 安全网                                    | 关闭环境变量                                 | 默认 | 覆盖场景                                                                                     |
|-------------------------------------------|----------------------------------------------|------|----------------------------------------------------------------------------------------------|
| `MSceneMessage.kMayaExiting` 钩子         | `DCC_MCP_MAYA_KMAYA_EXITING_HOOK=0`          | 开启 | `File → Exit Maya` 清退、`⌘Q` / Alt+F4——**早于** `uninitializePlugin` 触发。                 |
| `atexit` 兜底                             | `DCC_MCP_MAYA_ATEXIT_HOOK=0`                 | 开启 | 普通 Python 解释器退出（`mayapy` 脚本、REPL 退出、跳过 `unloadPlugin` 的嵌入场景）。         |
| 抗崩溃进程哨兵文件                        | `DCC_MCP_MAYA_PROCESS_SENTINEL=0`            | 开启 | 硬崩溃 / `kill -9` / 任务管理器结束——**操作系统会在进程死亡时自动删除哨兵**。               |
| 防御式 `__del__` 兜底（默认关闭）         | `DCC_MCP_MAYA_DEFENSIVE_DEL=1` 开启          | 关闭 | `mayapy` / 测试 fixture 里从未调用 `stop_server()` 的路径；默认关闭以规避 Tokio 嵌套死锁。   |

四个网由 `ShutdownCoordinator` 统一组合：插件启动后构造一次、
`uninitializePlugin` 时拆除。Coordinator 内部的一次性触发守卫保证即便多个网
同时触发也只会调用一次 stop callback。

## 退出路径支持矩阵

| 退出路径                                 | `uninitializePlugin` 触发 | 清理保证          | 最大脏窗口 | 命中的安全网                             |
|------------------------------------------|---------------------------|-------------------|------------|------------------------------------------|
| `File → Exit Maya`（正常）               | 是                        | **是**            | 0 秒       | `kMayaExiting` + `uninitializePlugin`    |
| `⌘Q` / Alt+F4（正常）                    | 有时                      | **是**            | 0 秒       | `kMayaExiting`                           |
| `unloadPlugin` 卸载插件                  | 是                        | **是**            | 0 秒       | `uninitializePlugin`                     |
| `mayapy` 脚本正常 `return`               | 否                        | **是**            | 0 秒       | `atexit`                                 |
| `mayapy` 脚本 `os._exit(...)`            | 否                        | 部分              | ≤ 30 秒    | 进程哨兵 + gateway 扫描                  |
| Maya 崩溃                                | 否                        | 部分              | ≤ 30 秒    | 进程哨兵 + gateway 扫描                  |
| `kill -9` / 任务管理器结束               | 否                        | 部分              | ≤ 30 秒    | 进程哨兵 + gateway 扫描                  |
| 控制台 Ctrl+C                            | 否                        | 部分              | ≤ 30 秒    | 进程哨兵 + gateway 扫描                  |

"部分"指：`FileRegistry` 里那一行可能最多保留 30 秒（`stale_timeout_secs` 默认），
但相邻的**进程哨兵文件**会被操作系统即时释放。因此 gateway 的周期扫描（默认 15 秒）
加上冷启动扫描，最坏情况下也不会超过约 45 秒脏窗口。

## 环境变量参考

| 变量                                    | 默认 | 取值            | 用途                                                                         |
|-----------------------------------------|------|-----------------|------------------------------------------------------------------------------|
| `DCC_MCP_MAYA_KMAYA_EXITING_HOOK`       | `1`  | `0` / `1`       | 关闭 `MSceneMessage.kMayaExiting` 钩子注册。                                 |
| `DCC_MCP_MAYA_ATEXIT_HOOK`              | `1`  | `0` / `1`       | 关闭 `atexit` 兜底。                                                         |
| `DCC_MCP_MAYA_PROCESS_SENTINEL`         | `1`  | `0` / `1`       | 关闭抗崩溃哨兵文件（节省 1 个文件描述符）。                                  |
| `DCC_MCP_MAYA_DEFENSIVE_DEL`            | `0`  | `0` / `1`       | 启用防御式 `__del__` 兜底。推荐仅在 `mayapy` / 测试 fixture 中开启。         |

取值遵循常见真值约定（`0`/`1`、`true`/`false`、`yes`/`no`、`on`/`off`）。
书写错误会降级为默认值并打 debug 日志，不会阻塞插件加载。

## Python API

```python
from dcc_mcp_maya import (
    ShutdownCoordinator,           # 组合四个安全网的总线
    ProcessSentinel,               # 底层 OS 哨兵文件封装
    DefensiveShutdownGuard,        # 可选的 __del__ 兜底包装器
    register_kmaya_exiting_hook,   # 只注册 kMayaExiting 的辅助函数
    register_atexit_hook,          # 只注册 atexit 的辅助函数
    write_process_sentinel,        # 只创建哨兵文件
    orphan_sentinels,              # 扫描辅助：列出 PID 已死的哨兵
)
```

插件 bootstrap 默认已经完成集成；对外暴露主要供嵌入方自定义 shutdown 流程使用
（无头编排、自定义 Maya 发行版、测试 fixture 等）。
