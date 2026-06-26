# 严格 Skill-Only Maya 回归测试套件

Issue: `PIP-481`

该套件基于严格 skill-only 工作流对 Maya 网关进行验证，并生成机器可读的 JSON 报告，用于版本间对比。

## 测试内容

`tools/strict_skill_only_regression.py` 执行以下步骤：

1. 策略守卫：验证 `execute_python` 和 `execute_mel` 在运行时已被阻止。
2. 类型化工作负载：创建 150 个球体，创建/分配材质，设置 180 个关键帧，导出 FBX。
3. 只读浸泡测试：500 次混合只读调用及延迟统计（`avg/P50/P95/P99/max/failure_count`）。

所有工具调用遵循：

- `search` -> `load_skill` -> `describe` -> `call` 类型化工具

工作负载不使用任意脚本路径。

## 前置条件

1. 启动已加载 `dcc_mcp_maya` 插件的 Maya。
2. 网关可访问（默认 `http://127.0.0.1:9765`）。
3. Maya 端已启用严格策略：

```powershell
$env:DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON = "1"
$env:DCC_MCP_MAYA_DISABLE_EXECUTE_MEL = "1"
# 或者使用单一开关：
$env:DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT = "1"
```

## 运行

```powershell
python tools/strict_skill_only_regression.py \
  --base-url http://127.0.0.1:9765 \
  --output-dir artifacts/perf \
  --soak-iterations 500
```

可选参数：

- `--report artifacts/perf/my_run.json`
- `--timeout-secs 180`

## 输出

- 控制台：完整 JSON 摘要。
- 文件：`artifacts/perf/strict_skill_only_regression_YYYYMMDD_HHMMSS.json`。
- FBX 产物：`artifacts/perf/strict_skill_only_perf.fbx`。

报告关键字段：

- `policy_guard.execute_python.blocked` / `policy_guard.execute_mel.blocked` 必须为 `true`。
- `workload.objects_created` 应为 `150`。
- `workload.keyframes_set` 应为 `180`。
- `workload.fbx.size_bytes` 应 `> 0`。
- `soak.avg_ms`、`soak.p50_ms`、`soak.p95_ms`、`soak.p99_ms`、`soak.max_ms`。
- `soak.failure_count` 干净运行时应为 `0`。

## 版本比较

在每个目标适配器/核心版本上运行套件，对比 JSON 字段：

- 延迟漂移：`soak.*_ms`
- 稳定性漂移：`soak.failure_count` 和 `soak.failures`
- 工作负载正确性：`objects_created`、`keyframes_set`、FBX 大小/选项

这使得产品和技术负责人可以进行确定性对比。
