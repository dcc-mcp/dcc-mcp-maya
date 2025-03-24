# DCC-MCP-Maya

<div align="center">

[![PyPI version](https://badge.fury.io/py/dcc-mcp-maya.svg)](https://badge.fury.io/py/dcc-mcp-maya)
[![Build Status](https://github.com/loonghao/dcc-mcp-maya/workflows/Build%20and%20Release/badge.svg)](https://github.com/loonghao/dcc-mcp-maya/actions)
[![Documentation Status](https://readthedocs.org/projects/dcc-mcp-maya/badge/?version=latest)](https://dcc-mcp-maya.readthedocs.io/en/latest/?badge=latest)
[![Python Version](https://img.shields.io/pypi/pyversions/dcc-mcp-maya.svg)](https://pypi.org/project/dcc-mcp-maya/)
[![License](https://img.shields.io/github/license/loonghao/dcc-mcp-maya.svg)](https://github.com/loonghao/dcc-mcp-maya/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/dcc-mcp-maya)](https://pepy.tech/project/dcc-mcp-maya)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/ruff-enabled-brightgreen)](https://github.com/astral-sh/ruff)

</div>

## Introduction
Maya integration for the Model Context Protocol (MCP). This package provides functionality for connecting to Maya through RPYC and exposing Maya's functionality to MCP clients.

## Features
- RPYC server for Maya that exposes Maya's functionality to external clients
- Client for connecting to Maya RPYC servers and executing Maya commands and scripts
- MCP adapter for integrating Maya with the Model Context Protocol
- Support for executing MEL scripts and Maya commands remotely
- Support for creating primitive objects in Maya
- Support for plugin extensions
- Integrated plugin management with dcc-mcp-core

## Installation
To install the package, run the following command:
```bash
pip install dcc-mcp-maya
```
Or with Poetry:
```bash
poetry add dcc-mcp-maya
```

## Usage
### Setting up Maya for MCP
1. Copy the `maya` directory to your Maya scripts directory or add it to your `PYTHONPATH`
2. The `userSetup.py` script will automatically load the MCP plugin when Maya starts

### Starting the Maya RPYC Server Manually
If the plugin is not automatically loaded, you can start it manually in the Maya script editor:
```python
from maya_mcp import initialize
initialize()
```
This will start a RPYC server in Maya that exposes Maya's functionality to external clients.

### Connecting to Maya from Python
```python
from dcc_mcp_maya.client import MayaRPyCClient

# Connect to Maya
client = MayaRPyCClient()

# Execute a MEL script
result = client.execute_mel('sphere -r 5;')

# Execute a Maya command
result = client.execute_cmd('polyCube', width=2, height=3, depth=4)

# Get scene information
scene_info = client.get_scene_info()
```

### Using the MCP Adapter
```python
from dcc_mcp_maya.adapter import MayaMCPAdapter

# Create the adapter
adapter = MayaMCPAdapter()

# Create a primitive object in Maya
result = adapter.maya_create_primitive('cube', width=2, height=3, depth=4)

# Execute a Maya command
result = adapter.maya_execute_command('polySphere', args='[{"radius": 5}]')

# Execute a MEL script
result = adapter.maya_execute_mel('sphere -r 5;')

# Get scene information
scene_info = adapter.maya_get_scene_info()

# Call a plugin function
result = adapter.maya_plugin_call('example_plugin', {'message': 'Hello from MCP!'})
```

### Creating Custom Plugins
You can create custom plugins for Maya MCP by creating a Python module with a `func_call` function:
```python
# example_plugin.py

# Plugin metadata
PLUGIN_INFO = {
    "author": "Your Name",
    "version": "1.0.0",
    "description": "Example plugin for Maya MCP",
    "category": "Example",
}

def func_call(context):
    # Get parameters from context
    message = context.get("message", "Hello from Maya MCP plugin!")
    
    # Do something with Maya
    from maya import cmds
    result = cmds.polyCube()
    
    return {
        "status": "success",
        "message": message,
        "result": result,
    }
```
Place your plugin in one of these locations:
1. Package plugins directory: `<package_dir>/plugins/maya/`
2. User plugins directory: `~/.dcc_mcp/plugins/maya/`
3. Custom path specified in the `DCC_MCP_PLUGIN_PATHS` environment variable

## Complete Example
See the `examples/maya_mcp_example.py` file for a complete example of using the Maya MCP framework.

## Development
### Setup
```bash
# Clone the repository
git clone https://github.com/loonghao/dcc-mcp-maya.git
cd dcc-mcp-maya

# Install dependencies
pip install -e .[dev]
```

### Creating a Maya Plugin Package
You can create a distributable ZIP package for Maya using the provided script:
```bash
# Using the make_maya_zip.py script
python make_maya_zip.py --version 0.1.0 --include-deps

# Or using nox (if installed)
nox -s make-maya-zip -- --version 0.1.0 --include-deps
```
This will create a ZIP file in the `.zip` directory containing all necessary files for installation, including:
- The Maya plugin files
- userSetup.py script
- Installation batch file
- Module template file
- Dependencies (if --include-deps is specified)

Users can install the plugin by extracting the ZIP file and running the included install.bat file.

### Running Tests
```bash
python -m unittest discover tests
```

## License
MIT
