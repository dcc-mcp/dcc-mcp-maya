# Multi-Instance Gateway Testing Guide

This document describes how to run the multi-instance gateway tests for dcc-mcp-maya.

## Overview

The test suite validates two major features:

- **P2-A: Gateway Failover** — Automatic detection and replacement of failed gateway instances (RTO < 15s, elevation < 5s)
- **P2-B: Dynamic Updates** — Scene and version metadata updates without server restart (< 100ms)
- **Discovery** — Registration and visibility of 50+ instances in FileRegistry

## Prerequisites

### Local Testing (with Maya installed)

1. **Python 3.9+** — Install from python.org or your package manager
2. **Maya 2024/2025** — At least one version installed locally
3. **Dependencies** — Install test dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

### CI Testing (no Maya required)

- Python 3.9, 3.10, or 3.11
- Dependencies automatically installed
- Some tests skip gracefully if mayapy is unavailable

## Running Tests Locally

### Quick Start

Run all multi-instance tests:

```bash
./tests/scripts/run_local_tests.sh
```

### Run Specific Test Module

Test gateway failover only:

```bash
./tests/scripts/run_local_tests.sh test_gateway_failover.py
```

Test discovery only:

```bash
./tests/scripts/run_local_tests.sh test_multi_instance_discovery.py
```

### Run Specific Test

Run a single test with verbose output:

```bash
cd tests
python -m pytest test_gateway_failover.py::test_gateway_failure_detection_and_elevation -v -s
```

### Advanced Options

Run tests with extra logging:

```bash
./tests/scripts/run_local_tests.sh test_gateway_failover.py -v -s --log-cli-level=DEBUG
```

Run tests in parallel (requires pytest-xdist):

```bash
./tests/scripts/run_local_tests.sh test_gateway_failover.py -n auto
```

## Test Modules

### test_gateway_failover.py

Tests automatic gateway failover when the current gateway instance fails.

**Test Cases:**

1. `test_gateway_election_enabled_by_default` — Verify failover is enabled by default
2. `test_gateway_failure_detection_and_elevation` — Main test: detect failure → elect new gateway
3. `test_gateway_failover_disabled_when_gateway_port_zero` — Verify failover can be disabled
4. `test_multiple_instance_failover_chain` — Chain failover (kill gateway 1 → elect 2 → kill 2 → elect 3)
5. `test_fast_failover_recovery` — Verify SLA compliance (< 15s RTO)
6. `test_gateway_failover_environment_variable` — Verify `DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER` env var works

**Expected Results:**

- ✓ At least 6 test cases pass
- ✓ Detection RTO < 15 seconds
- ✓ Election time < 20 seconds total

### test_multi_instance_discovery.py

Tests that the gateway discovers and registers multiple instances.

**Test Cases:**

1. `test_discovery_basic_two_instances` — Basic discovery of 2 instances
2. `test_discovery_many_instances` — Discover 10+ instances concurrently
3. `test_discovery_with_instance_lifecycle` — Add/remove instances, verify registry updates
4. `test_discovery_instance_metadata_accuracy` — Verify version, scene metadata
5. `test_discovery_mixed_maya_versions` — Instances of different Maya versions (2024, 2025)
6. `test_discovery_registry_persistence` — Registry persists across gateway restarts

**Expected Results:**

- ✓ All 6 discovery tests pass
- ✓ Gateway can handle 10+ concurrent instances
- ✓ Metadata correctly reflects instance state

### test_scene_update.py

Tests dynamic scene/version updates without restart.

**Test Cases:**

1. `test_scene_update_basic` — Update scene file path
2. `test_version_update` — Update Maya version
3. `test_concurrent_scene_updates` — Multiple instances update scenes concurrently
4. `test_scene_update_performance` — Verify < 100ms SLA
5. `test_scene_update_no_restart_required` — Server stays healthy after update
6. `test_scene_update_visibility_latency` — Updated metadata visible within < 5s

**Expected Results:**

- ✓ All 4-6 scene update tests pass
- ✓ No server restarts required for updates
- ✓ Updates complete within SLA

## Test Architecture

### Components

**MayaInstanceManager** (`tests/fixtures/maya_instances.py`)
- Launches multiple standalone mayapy processes
- Each runs independent MCP server on different ports
- All compete for shared gateway port (default 9765)
- Tracks instance lifecycle (launch, stop, health)

**GatewayTestClient** (`tests/fixtures/conftest.py`)
- HTTP client for gateway interaction
- Provides health checks, tool listing, instance discovery
- Assertions: instance count, gateway election, metadata accuracy

**pytest Fixtures** (`tests/fixtures/conftest.py`)
- `gateway_client` — Pre-configured test client
- `temp_registry_dir` — Temp directory for FileRegistry
- `maya_instance_manager` — Manager for launching instances

### Environment Variables

- `DCC_MCP_GATEWAY_PORT` — Gateway port (default: 9765)
- `DCC_MCP_REGISTRY_DIR` — Registry directory (default: temp)
- `DCC_MCP_MAYA_HOT_RELOAD` — Enable skill hot-reload (default: 1)
- `DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER` — Enable failover (default: 1)

## CI Integration

### GitHub Actions

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Matrix: Python 3.9, 3.10, 3.11

**Workflow:** `.github/workflows/multi-instance-tests.yml`

**Results:**
- Test artifacts uploaded to GitHub
- Summary shown in PR checks
- Failed tests block merge (configurable)

### Local CI Simulation

Run the same tests locally as CI would:

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e .
pip install -r requirements-test.txt
cd tests
python -m pytest test_gateway_failover.py test_multi_instance_discovery.py test_scene_update.py -v
```

## Troubleshooting

### "mayapy not found"

**Problem:** Tests skip because mayapy isn't installed

**Solutions:**
- Install Maya 2024 or 2025
- Or run tests in CI where Maya isn't required for basic validation

### "Port 9765 already in use"

**Problem:** Another process is using the gateway port

**Solutions:**
```bash
# Find process using port 9765
lsof -i :9765  # macOS/Linux
netstat -ano | findstr :9765  # Windows

# Kill process
kill -9 <PID>  # or taskkill /PID <PID> /F on Windows
```

### Tests timeout

**Problem:** Tests take longer than expected

**Solutions:**
- Increase pytest timeout: `pytest --timeout=300`
- Check system resources (CPU, memory)
- Run fewer instances first, then scale up

### Gateway never starts

**Problem:** GatewayTestClient.wait_for_gateway() times out

**Check:**
- Is dcc-mcp-core installed? `python -c "import dcc_mcp_core"`
- Are port 9765+ available?
- Check logs in first instance stdout

### Metadata not updating

**Problem:** update_gateway_metadata() doesn't show in gateway

**Check:**
- Is TransportManager available? `python -c "from dcc_mcp_core import TransportManager"`
- Is FileRegistry being created? Check `registry_dir`
- Check server logs for errors

## Performance Benchmarks

Expected performance on modern hardware (4-core, 8GB RAM):

| Operation | SLA | Actual |
|-----------|-----|--------|
| Instance startup | < 5s | ~2-3s |
| Gateway election | < 15s RTO | ~8-12s |
| Scene update | < 100ms | ~50-80ms |
| Discovery (10 instances) | < 10s | ~3-5s |
| Discovery (50 instances) | < 30s | ~10-15s |

## Contributing

When adding new tests:

1. Place in appropriate module (failover, discovery, or scene-update)
2. Use descriptive test name: `test_<feature>_<scenario>`
3. Include docstring explaining what is tested
4. Use fixtures: `gateway_client`, `maya_instance_manager`, `temp_registry_dir`
5. Add `@pytest.mark.timeout(seconds)` to prevent hangs
6. Aim for < 2 minutes per test
7. Update this README if adding new modules

## References

- [dcc-mcp-core Documentation](https://github.com/lightbox/dcc-mcp-core)
- [MCP Protocol](https://spec.modelcontextprotocol.io/)
- [pytest Documentation](https://docs.pytest.org/)
