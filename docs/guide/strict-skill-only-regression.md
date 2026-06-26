# Strict Skill-Only Maya Regression Suite

Issue: `PIP-481`

This suite validates a strict skill-only workflow against a live Maya gateway and emits a machine-readable JSON report for release-over-release comparison.

## What It Runs

`tools/strict_skill_only_regression.py` performs:

1. Policy guard: verifies `execute_python` and `execute_mel` are blocked at runtime.
2. Typed workload: creates 150 spheres, creates/assigns materials, sets 180 keyframes, exports FBX.
3. Read-only soak: 500 mixed read calls and latency summary (`avg/P50/P95/P99/max/failure_count`).

All tool invocations follow:

- `search` -> `load_skill` -> `describe` -> `call` typed tool

No arbitrary script path is used for the workload.

## Prerequisites

1. Run Maya with `dcc_mcp_maya` plugin loaded.
2. Gateway reachable (default `http://127.0.0.1:9765`).
3. Strict policy enabled on Maya side:

```powershell
$env:DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON = "1"
$env:DCC_MCP_MAYA_DISABLE_EXECUTE_MEL = "1"
# or one switch:
$env:DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT = "1"
```

## Run

```powershell
python tools/strict_skill_only_regression.py \
  --base-url http://127.0.0.1:9765 \
  --output-dir artifacts/perf \
  --soak-iterations 500
```

Optional:

- `--report artifacts/perf/my_run.json`
- `--timeout-secs 180`

## Output

- Console: full JSON summary.
- File: `artifacts/perf/strict_skill_only_regression_YYYYMMDD_HHMMSS.json`.
- FBX artifact: `artifacts/perf/strict_skill_only_perf.fbx`.

Key report fields:

- `policy_guard.execute_python.blocked` / `policy_guard.execute_mel.blocked` must be `true`.
- `workload.objects_created` should be `150`.
- `workload.keyframes_set` should be `180`.
- `workload.fbx.size_bytes` should be `> 0`.
- `soak.avg_ms`, `soak.p50_ms`, `soak.p95_ms`, `soak.p99_ms`, `soak.max_ms`.
- `soak.failure_count` should be `0` for a clean run.

## Compare Versions

Run the suite on each target adapter/core version and diff JSON fields:

- Latency drift: `soak.*_ms`
- Stability drift: `soak.failure_count` and `soak.failures`
- Workload correctness: `objects_created`, `keyframes_set`, FBX size/options

This makes comparisons deterministic for product and technical leads.
