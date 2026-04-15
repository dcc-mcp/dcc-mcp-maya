# Docker-Based Multi-Instance Testing

This document describes how to use Docker for multi-instance Maya MCP gateway testing.

## Overview

The test framework now supports two modes for launching Maya instances:

1. **Local Mode**: Uses locally installed `mayapy` executable
2. **Docker Mode**: Uses Docker containers with Maya images

## Quick Start

### Docker Mode (CI/CD Preferred)

The framework automatically selects Docker if available:

```bash
# Tests will automatically use Docker if installed
pytest tests/test_gateway_failover.py -v

# Or explicitly force Docker mode
export DCC_MCP_FORCE_DOCKER=1
pytest tests/test_gateway_failover.py -v
```

### Local Mode

If you have Maya installed locally:

```bash
pytest tests/test_gateway_failover.py -v
# Automatically uses local mayapy if Docker is unavailable
```

## Setup

### Prerequisites

#### For Docker Mode
- Docker or Docker Desktop installed and running
- Docker images available:
  - `autodesk/maya:2023`
  - `autodesk/maya:2024`
  - `autodesk/maya:2025`

#### For Local Mode
- Maya installed (2023, 2024, or 2025)
- `mayapy` available in system PATH or standard installation locations

### Installation

1. Clone the repository:
```bash
git clone <repo>
cd dcc-mcp-maya
```

2. Install development dependencies:
```bash
pip install -e ".[dev]"
pip install -r requirements-test.txt
```

3. Install package in development mode:
```bash
pip install -e .
```

## Usage

### Automatic Selection (Recommended)

The framework automatically selects the best available mode:

```python
from tests.fixtures.instance_factory import get_instance_manager

# Auto-detects: Docker if available, else local mayapy
manager = get_instance_manager(
    gateway_port=9765,
    registry_dir="/tmp/maya_registry"
)

# Create and launch instances
config = manager.create_config("maya-2025-01", maya_version="2025")
manager.launch_instance(config)

# ... run tests ...

manager.cleanup()
```

### Explicit Docker Mode

```python
from tests.fixtures.docker_maya import DockerMayaInstanceManager

manager = DockerMayaInstanceManager(
    gateway_port=9765,
    registry_dir="/tmp/maya_registry",
    docker_registry="registry.example.com/"  # Optional custom registry
)

# Create config for specific version
config = manager.create_config("maya-2024-01", maya_version="2024")
manager.launch_instance(config)

# ... run tests ...

manager.cleanup()
```

### Explicit Local Mode

```python
from tests.fixtures.maya_instances import MayaInstanceManager

manager = MayaInstanceManager(
    gateway_port=9765,
    registry_dir="/tmp/maya_registry"
)

config = manager.create_config("maya-2025-01", maya_version="2025")
manager.launch_instance(config)

# ... run tests ...

manager.cleanup()
```

## Environment Variables

Control behavior via environment variables:

| Variable | Values | Effect |
|----------|--------|--------|
| `DCC_MCP_FORCE_DOCKER` | `1`, `true`, `yes` | Force Docker mode (skip local mayapy) |
| `DCC_MCP_DOCKER_REGISTRY` | URL prefix | Custom Docker registry (e.g., `registry.example.com/`) |
| `DCC_MCP_GATEWAY_PORT` | Port number | Shared gateway port (default: 9765) |
| `DCC_MCP_REGISTRY_DIR` | Path | Shared registry directory |

Example:
```bash
export DCC_MCP_FORCE_DOCKER=1
export DCC_MCP_DOCKER_REGISTRY=quay.io/
export DCC_MCP_GATEWAY_PORT=9765
pytest tests/test_gateway_failover.py -v
```

## Running Tests

### Run All Multi-Instance Tests

```bash
# Docker mode (if available)
export DCC_MCP_FORCE_DOCKER=1
pytest tests/test_gateway_failover.py tests/test_multi_instance_discovery.py -v

# Local mode (if mayapy available)
pytest tests/test_gateway_failover.py tests/test_multi_instance_discovery.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_gateway_failover.py::TestGatewayFailover -v
```

### Run With Coverage

```bash
pytest tests/test_gateway_failover.py --cov=src/dcc_mcp_maya --cov-report=html
```

### Run Docker Integration Tests

```bash
export DCC_MCP_FORCE_DOCKER=1
pytest tests/test_docker_integration.py -v
```

## CI/CD Integration

The GitHub Actions workflow (`multi-instance-tests.yml`) automatically:

1. **Docker Multi-Version Tests**: Runs tests with Maya 2023, 2024, 2025 images
   - Matrix: Python 3.9, 3.10, 3.11 × Maya 2023, 2024, 2025
   - Total: 9 job combinations

2. **Local Fallback Tests**: Attempts local mayapy (skipped if unavailable)
   - Matrix: Python 3.9, 3.10, 3.11
   - Total: 3 job combinations

## Multi-Version Testing Example

Test gateway failover across different Maya versions:

```python
@pytest.fixture(params=["2023", "2024", "2025"])
def maya_version(request):
    return request.param

def test_gateway_failover_all_versions(maya_version):
    """Test gateway failover on all Maya versions."""
    manager = get_instance_manager()
    
    # Create instances for the specified version
    config1 = manager.create_config(f"maya-{maya_version}-01", maya_version=maya_version)
    config2 = manager.create_config(f"maya-{maya_version}-02", maya_version=maya_version)
    
    # Launch both
    assert manager.launch_instance(config1)
    assert manager.launch_instance(config2)
    
    # Test gateway competition...
    # ...
    
    manager.cleanup()
```

## Troubleshooting

### Docker Command Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'docker'`

**Solution**:
- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Ensure Docker daemon is running: `docker ps`

### Docker Image Not Found

**Error**: `Failed to pull Docker image autodesk/maya:2025`

**Solutions**:
- Ensure Docker is authenticated: `docker login`
- Check image availability:
  ```bash
  docker pull autodesk/maya:2025
  ```
- Use custom registry if needed:
  ```bash
  export DCC_MCP_DOCKER_REGISTRY=quay.io/autodesk/
  ```

### mayapy Not Found (Local Mode)

**Error**: `mayapy 2025 not found for instance maya-2025-01`

**Solutions**:
- Install Maya locally
- Add Maya to PATH
- Use Docker mode instead: `export DCC_MCP_FORCE_DOCKER=1`

### Port Already in Use

**Error**: `Address already in use`

**Solutions**:
- Change gateway port:
  ```bash
  export DCC_MCP_GATEWAY_PORT=9766
  pytest ...
  ```
- Kill existing processes:
  ```bash
  lsof -ti:9765 | xargs kill -9  # macOS/Linux
  netstat -ano | findstr :9765   # Windows
  ```

## Performance Considerations

### Docker
- **Startup**: ~3-5 seconds per container (depends on image size)
- **Memory**: ~800MB per container minimum
- **Network**: Uses host networking for gateway communication
- **Benefits**: Consistent environment, version isolation, CI/CD friendly

### Local mayapy
- **Startup**: ~1-2 seconds (faster than Docker)
- **Memory**: Variable (depends on Maya installation)
- **Limitations**: Must match local Maya installations only

## Best Practices

1. **Use Docker in CI/CD**: Ensures consistency across all test runs
2. **Use Local for Development**: Faster iteration if Maya is already installed
3. **Test Multiple Versions**: Use Docker matrix for comprehensive testing
4. **Clean Up Resources**: Always call `manager.cleanup()` to stop containers
5. **Check Docker Health**: Run `docker ps` to verify containers are running

## Contributing

When adding new tests:

1. Mark Docker-specific tests with `@pytest.mark.skipif(not is_docker_available())`
2. Use `get_instance_manager()` for automatic mode selection
3. Document any Maya version-specific behavior
4. Test with at least two versions (e.g., 2024 and 2025)
5. Ensure cleanup happens even on test failure (use fixtures)

## Related Documents

- [Multi-Instance Gateway Testing](README_TESTING.md)
- [Gateway Failover Implementation](HOTRELOAD_CHANGES.md)
- [Project README](../README.md)
