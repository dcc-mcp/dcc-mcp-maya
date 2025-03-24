"""Maya MCP integration package.

This package provides integration between Maya and the Model Context Protocol (MCP).
"""

from dcc_mcp_maya.__version__ import __version__
from dcc_mcp_maya.client import MayaRPyCClient
from dcc_mcp_maya.adapter import MayaMCPAdapter

# Register the Maya client class with the client registry
try:
    from dcc_mcp_rpyc.client import ClientRegistry

    ClientRegistry.register("maya", MayaRPyCClient)
except ImportError:
    # dcc_mcp_rpyc is not installed, or the ClientRegistry is not available
    pass

__all__ = [
    "MayaMCPAdapter",
    "MayaRPyCClient",
    "__version__",
]
