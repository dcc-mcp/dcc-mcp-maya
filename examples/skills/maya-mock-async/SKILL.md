---
name: maya-mock-async
description: "Synthetic async skill for gateway integration tests. Sleeps for N seconds and reports progress every 500 ms. No actual Maya installation required — uses MayaStandaloneDispatcher."
license: "MIT"
compatibility: "Python>=3.7"
metadata:
  dcc-mcp:
    dcc: maya
    version: "1.0.0"
    tags: ["testing", "async", "mock"]
    tools: tools.yaml
---

# maya-mock-async

A synthetic skill designed for integration and gateway tests. It exposes a
single tool that sleeps for a configurable duration, emitting progress
notifications every 500 ms.

**This skill has no real Maya dependency** — it works with
`MayaStandaloneDispatcher` so CI can exercise the full async dispatch path
without a Maya installation.

## Tools

### `mock_async_sleep`

Sleep for `duration_secs` seconds and return a summary.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `duration_secs` | float | 2.0 | Total sleep time in seconds |
| `progress_interval_secs` | float | 0.5 | How often to yield a progress update |

Returns `{"slept_secs": <float>, "cancelled": <bool>}`.

## Usage in gateway tests

```python
# examples/skills/maya-mock-async/scripts/mock_async_sleep.py
from dcc_mcp_core.skill import skill_entry, skill_success
```
