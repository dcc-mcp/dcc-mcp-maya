# dcc-mcp-maya

Maya plugin and adapter for the [DCC Model Context Protocol](https://github.com/loonghao/dcc-mcp-core) (MCP) ecosystem.

## Architecture

```
┌─────────────────────────────────────────┐
│  Maya (embedded Python)                  │
│  ┌───────────────────────────────────┐  │
│  │  dcc_mcp_maya.py  (Maya Plugin)   │  │
│  │  └─ MayaRPyCService               │  │
│  │     ├─ scene / session info       │  │
│  │     ├─ execute_python / mel       │  │
│  │     └─ call_action (ActionReg.)   │  │
│  └───────────────────────────────────┘  │
└──────────────────┬──────────────────────┘
                   │  RPyC (TCP)
┌──────────────────▼──────────────────────┐
│  External Python process / LLM host     │
│  MayaAdapter (dcc_mcp_ipc.DCCAdapter)   │
│  └─ MCP Server / Claude / Cursor …      │
└─────────────────────────────────────────┘
```

**Key packages:**

| Package | Role |
|---------|------|
| `dcc-mcp-core` | Rust+PyO3 core: `ActionResultModel`, `ActionRegistry`, models |
| `dcc-mcp-ipc` | IPC layer: `DCCRPyCService`, `DCCServer`, `DCCAdapter`, service discovery |
| `dcc-mcp-maya` | Maya plugin (`MayaRPyCService`) + external adapter (`MayaAdapter`) |

## Installation

### Deploy into Maya

1. Install Python dependencies into Maya's Python (match the Maya Python version):

```bash
# Example for Maya 2024 (Python 3.10)
mayapy -m pip install dcc-mcp-core dcc-mcp-ipc rpyc
```

2. Copy (or symlink) `maya/plugin/dcc_mcp_maya.py` to a directory on `MAYA_PLUG_IN_PATH`.

3. Optionally copy `maya/userSetup.py` to your Maya scripts folder for auto-loading.

4. Load via Plugin Manager: **Window > Settings/Preferences > Plug-in Manager**, find `dcc_mcp_maya` and check **Loaded**.

### Install the adapter (external side)

```bash
pip install dcc-mcp-maya
# or from source:
pip install -e .
```

## Usage

### Inside Maya (plugin auto-starts server)

The server starts automatically when the plugin loads. Use the **DCC MCP** menu to start/stop manually.

### External client

```python
from dcc_mcp_maya.adapter import MayaAdapter

adapter = MayaAdapter()  # auto-discovers Maya via file registry

# Get scene info
result = adapter.get_scene_info()
print(result.context)

# Create primitives
adapter.create_primitive("sphere", radius=2.0)
adapter.create_primitive("cube", width=1.0, height=2.0, depth=3.0)

# Execute MEL
adapter.execute_mel("polySphere -r 1 -name myBall;")

# Call registered actions
adapter.call_action("create_sphere", radius=5.0)
adapter.call_action("list_objects", object_type="mesh")
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (no Maya required)
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## License

MIT
