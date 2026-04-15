"""Multi-instance Maya MCP server launcher for gateway failover and discovery testing.

This module provides utilities for launching multiple standalone mayapy processes,
each running an independent MCP server on different ports, but all competing for
the same gateway port (default 9765). Used to test:

- Gateway failover (RTO < 15s, backup elevation < 5s)
- Multi-instance discovery (50+ instances)
- Dynamic scene/version updates without restart
"""

import json
import logging
import os
import platform
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def check_mayapy_available() -> bool:
    """Check if mayapy is available in the environment.

    Attempts to find mayapy executable for at least one Maya version.
    Used to skip tests that require mayapy when it's not available.

    Returns:
        True if mayapy can be found, False otherwise.
    """
    # Try common Maya versions
    for version in ["2025", "2024", "2023", "2022"]:
        if _find_mayapy_version(version):
            return True
    return False


def _find_mayapy_version(version: str) -> Optional[Path]:
    """Find mayapy executable for a specific version (internal helper)."""
    # Try Windows
    paths_to_try = [
        Path(f"C:/Program Files/Autodesk/Maya{version}/bin/mayapy.exe"),
        Path(f"C:/Program Files/Autodesk/Maya{version}/bin/mayapy"),
    ]

    # Try macOS
    paths_to_try.extend(
        [
            Path(f"/Applications/Autodesk/maya{version}/Maya.app/Contents/bin/mayapy"),
        ]
    )

    # Try Linux
    paths_to_try.extend(
        [
            Path(f"/opt/autodesk/maya{version}/bin/mayapy"),
            Path(f"/usr/autodesk/maya{version}/bin/mayapy"),
        ]
    )

    for path in paths_to_try:
        if path.exists() and os.access(path, os.X_OK):
            return path

    return None


@dataclass
class MayaInstanceConfig:
    """Configuration for a standalone Maya MCP instance."""

    instance_id: str  # Unique identifier (e.g., "maya-2025-01")
    port: int  # Local HTTP port for this instance
    gateway_port: int  # Shared gateway port (default 9765)
    registry_dir: str  # Shared registry directory
    maya_version: str  # Maya version string (e.g., "2025")
    scene_file: Optional[str] = None  # Optional scene file to report
    enable_hot_reload: bool = False
    enable_gateway_failover: bool = True
    env_vars: Optional[Dict[str, str]] = None  # Extra environment variables


class MayaInstanceManager:
    """Manages lifecycle of multiple standalone Maya MCP instances."""

    def __init__(self, gateway_port: int = 9765, registry_dir: Optional[str] = None):
        """Initialize instance manager.

        Args:
            gateway_port: Shared gateway port for all instances
            registry_dir: Shared registry directory. If None, creates temp directory.
        """
        self.gateway_port = gateway_port
        self.registry_dir = registry_dir or tempfile.mkdtemp(prefix="maya_mcp_registry_")
        self.instances: Dict[str, subprocess.Popen] = {}
        self.configs: Dict[str, MayaInstanceConfig] = {}
        self._next_port = 10000

    def create_config(
        self,
        instance_id: str,
        maya_version: str = "2025",
        scene_file: Optional[str] = None,
        enable_gateway_failover: bool = True,
    ) -> MayaInstanceConfig:
        """Create a config for a new instance.

        Args:
            instance_id: Unique instance identifier
            maya_version: Maya version string
            scene_file: Optional scene file path
            enable_gateway_failover: Enable automatic gateway failover

        Returns:
            MayaInstanceConfig ready to launch
        """
        config = MayaInstanceConfig(
            instance_id=instance_id,
            port=self._next_port,
            gateway_port=self.gateway_port,
            registry_dir=self.registry_dir,
            maya_version=maya_version,
            scene_file=scene_file,
            enable_gateway_failover=enable_gateway_failover,
        )
        self._next_port += 1
        return config

    def launch_instance(self, config: MayaInstanceConfig, timeout: int = 30) -> bool:
        """Launch a standalone mayapy instance running MCP server.

        Args:
            config: Instance configuration
            timeout: Startup timeout in seconds

        Returns:
            True if instance started successfully
        """
        if config.instance_id in self.instances:
            logger.warning("Instance %s already running", config.instance_id)
            return False

        try:
            # Build Python script to run inside mayapy
            startup_script = self._generate_startup_script(config)

            # Determine mayapy executable path
            mayapy_path = self._find_mayapy(config.maya_version)
            if not mayapy_path:
                logger.error(
                    "mayapy %s not found for instance %s",
                    config.maya_version,
                    config.instance_id,
                )
                return False

            # Setup environment
            env = os.environ.copy()
            env["DCC_MCP_GATEWAY_PORT"] = str(config.gateway_port)
            env["DCC_MCP_REGISTRY_DIR"] = config.registry_dir
            env["DCC_MCP_MAYA_HOT_RELOAD"] = "1" if config.enable_hot_reload else "0"
            env["DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER"] = "1" if config.enable_gateway_failover else "0"

            if config.env_vars:
                env.update(config.env_vars)

            # Launch mayapy process
            logger.info(
                "Launching instance %s on port %d (gateway %d)",
                config.instance_id,
                config.port,
                config.gateway_port,
            )

            # Run mayapy with startup script via stdin
            proc = subprocess.Popen(
                [mayapy_path, "-c", startup_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            self.instances[config.instance_id] = proc
            self.configs[config.instance_id] = config

            # Give instance time to start and register with gateway
            time.sleep(2)

            # Verify instance is running
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                logger.error(
                    "Instance %s failed to start. stdout=%s stderr=%s",
                    config.instance_id,
                    stdout,
                    stderr,
                )
                del self.instances[config.instance_id]
                return False

            logger.info("Instance %s started successfully", config.instance_id)
            return True

        except Exception as exc:
            logger.error("Failed to launch instance %s: %s", config.instance_id, exc)
            return False

    def stop_instance(self, instance_id: str, timeout: int = 10) -> bool:
        """Stop a running instance.

        Args:
            instance_id: Instance to stop
            timeout: Shutdown timeout in seconds

        Returns:
            True if instance was stopped
        """
        if instance_id not in self.instances:
            logger.warning("Instance %s not found", instance_id)
            return False

        try:
            proc = self.instances[instance_id]
            logger.info("Stopping instance %s", instance_id)

            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning("Instance %s did not terminate; killing", instance_id)
                proc.kill()
                proc.wait()

            del self.instances[instance_id]
            logger.info("Instance %s stopped", instance_id)
            return True

        except Exception as exc:
            logger.error("Failed to stop instance %s: %s", instance_id, exc)
            return False

    def stop_all(self, timeout: int = 10) -> None:
        """Stop all running instances."""
        for instance_id in list(self.instances.keys()):
            self.stop_instance(instance_id, timeout=timeout)

    def get_instance_config(self, instance_id: str) -> Optional[MayaInstanceConfig]:
        """Get configuration for an instance."""
        return self.configs.get(instance_id)

    def list_running(self) -> List[str]:
        """List IDs of running instances."""
        return [iid for iid, proc in self.instances.items() if proc.poll() is None]

    def get_registry_content(self) -> Dict[str, Any]:
        """Read current FileRegistry JSON content.

        Returns:
            Dict with registry data (services, instances, etc.)
        """
        registry_file = Path(self.registry_dir) / "file_registry.json"
        if not registry_file.exists():
            return {}

        try:
            with open(registry_file) as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to read registry: %s", exc)
            return {}

    @staticmethod
    def _find_mayapy(version: str) -> Optional[str]:
        """Find mayapy executable for given Maya version.

        Args:
            version: Maya version string (e.g., "2025")

        Returns:
            Path to mayapy executable or None
        """
        system = platform.system()

        if system == "Windows":
            # Windows paths: C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe
            candidates = [
                f"C:/Program Files/Autodesk/Maya{version}/bin/mayapy.exe",
                f"C:/Program Files (x86)/Autodesk/Maya{version}/bin/mayapy.exe",
            ]
        elif system == "Darwin":
            # macOS: /Applications/Autodesk/Maya{version}/Maya.app/Contents/bin/mayapy
            candidates = [
                f"/Applications/Autodesk/Maya{version}/Maya.app/Contents/bin/mayapy",
            ]
        elif system == "Linux":
            # Linux: /usr/autodesk/maya{version}/bin/mayapy
            candidates = [
                f"/usr/autodesk/maya{version}/bin/mayapy",
            ]
        else:
            return None

        for path in candidates:
            if Path(path).exists():
                return path

        return None

    @staticmethod
    def _generate_startup_script(config: MayaInstanceConfig) -> str:
        """Generate Python script to run inside mayapy.

        This script initializes Maya, starts the MCP server, and keeps it running.
        """
        # Escape registry_dir for Python string literal (convert backslashes to forward slashes)
        registry_dir = config.registry_dir.replace("\\", "/")
        scene_file_repr = repr(config.scene_file) if config.scene_file else "None"

        return f"""
import sys
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("maya_mcp_startup")

try:
    # Initialize Maya
    import maya.standalone
    maya.standalone.initialize(name="{config.instance_id}")
    logger.info("Maya initialized for {config.instance_id}")

    # Import and start MCP server
    from dcc_mcp_maya import start_server

    handle = start_server(
        port={config.port},
        gateway_port={config.gateway_port},
        registry_dir=r"{registry_dir}",
        dcc_version="{config.maya_version}",
        scene={scene_file_repr},
        enable_hot_reload={config.enable_hot_reload},
        enable_gateway_failover={config.enable_gateway_failover},
    )

    logger.info("MCP server started: {config.instance_id} -> {{}}".format(handle.mcp_url()))

    # Keep server running
    while True:
        time.sleep(1)

except Exception as e:
    logger.exception("Startup failed for {config.instance_id}: %s", e)
    sys.exit(1)
"""

    def cleanup(self) -> None:
        """Cleanup resources (stop all instances, remove temp registry)."""
        self.stop_all()
        # Don't delete registry_dir if it was provided externally
        # Only clean up temp directories created by this manager


if __name__ == "__main__":
    # Example usage
    manager = MayaInstanceManager(gateway_port=9765)

    # Create configs for 3 instances (2025, 2024, 2025)
    configs = [
        manager.create_config("maya-2025-01", maya_version="2025"),
        manager.create_config("maya-2024-01", maya_version="2024"),
        manager.create_config("maya-2025-02", maya_version="2025"),
    ]

    # Launch them
    for config in configs:
        manager.launch_instance(config)

    # Check registry
    print("Running instances:", manager.list_running())
    print("Registry content:", json.dumps(manager.get_registry_content(), indent=2))

    # Cleanup
    manager.cleanup()
