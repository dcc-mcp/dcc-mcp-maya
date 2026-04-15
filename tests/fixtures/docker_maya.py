"""Docker-based Maya MCP instance launcher for multi-version CI testing.

This module provides Docker-based alternatives to local mayapy, enabling:
- Multi-version Maya testing (2023/2024/2025) in CI
- Consistent environment across Windows/macOS/Linux
- Automatic Docker image detection and fallback to local mayapy
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Docker image mapping for different Maya versions
DOCKER_IMAGES = {
    "2023": "autodesk/maya:2023",
    "2024": "autodesk/maya:2024",
    "2025": "autodesk/maya:2025",
}

# Environment variable to force Docker mode
ENV_FORCE_DOCKER = "DCC_MCP_FORCE_DOCKER"
ENV_DOCKER_REGISTRY = "DCC_MCP_DOCKER_REGISTRY"


def is_docker_available() -> bool:
    """Check if Docker daemon is accessible."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def has_docker_image(image: str) -> bool:
    """Check if a Docker image is available locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@dataclass
class DockerMayaConfig:
    """Configuration for Docker-based Maya MCP instance."""

    instance_id: str
    port: int
    gateway_port: int
    registry_dir: str
    maya_version: str
    docker_image: str
    scene_file: Optional[str] = None
    enable_hot_reload: bool = False
    enable_gateway_failover: bool = True
    env_vars: Optional[Dict[str, str]] = None
    container_name: Optional[str] = None  # Generated container name


class DockerMayaInstanceManager:
    """Manages Maya MCP instances via Docker containers."""

    def __init__(
        self,
        gateway_port: int = 9765,
        registry_dir: Optional[str] = None,
        docker_registry: Optional[str] = None,
    ):
        """Initialize Docker-based instance manager.

        Args:
            gateway_port: Shared gateway port
            registry_dir: Shared registry directory
            docker_registry: Optional Docker registry prefix (e.g., "registry.example.com/")
        """
        self.gateway_port = gateway_port
        self.registry_dir = registry_dir or tempfile.mkdtemp(prefix="maya_mcp_registry_")
        self.docker_registry = docker_registry or ""
        self.containers: Dict[str, str] = {}  # instance_id -> container_id
        self.configs: Dict[str, DockerMayaConfig] = {}
        self._next_port = 10000

        if not is_docker_available():
            raise RuntimeError(
                "Docker is not available. Install Docker or use local mayapy instead."
            )

    def create_config(
        self,
        instance_id: str,
        maya_version: str = "2025",
        scene_file: Optional[str] = None,
        enable_gateway_failover: bool = True,
    ) -> DockerMayaConfig:
        """Create a Docker-based Maya instance config.

        Args:
            instance_id: Unique instance identifier
            maya_version: Maya version (2023/2024/2025)
            scene_file: Optional scene file path
            enable_gateway_failover: Enable automatic gateway failover

        Returns:
            DockerMayaConfig ready to launch

        Raises:
            ValueError: If maya_version is not supported
        """
        if maya_version not in DOCKER_IMAGES:
            raise ValueError(
                f"Unsupported Maya version: {maya_version}. "
                f"Supported versions: {list(DOCKER_IMAGES.keys())}"
            )

        docker_image = self.docker_registry + DOCKER_IMAGES[maya_version]
        container_name = f"maya-mcp-{instance_id}-{int(time.time())}"

        config = DockerMayaConfig(
            instance_id=instance_id,
            port=self._next_port,
            gateway_port=self.gateway_port,
            registry_dir=self.registry_dir,
            maya_version=maya_version,
            docker_image=docker_image,
            scene_file=scene_file,
            enable_gateway_failover=enable_gateway_failover,
            container_name=container_name,
        )
        self._next_port += 1
        return config

    def launch_instance(self, config: DockerMayaConfig, timeout: int = 30) -> bool:
        """Launch a Docker container running Maya MCP server.

        Args:
            config: Docker Maya instance configuration
            timeout: Startup timeout in seconds

        Returns:
            True if container started successfully
        """
        if config.instance_id in self.containers:
            logger.warning("Instance %s already running", config.instance_id)
            return False

        try:
            # Check if image is available
            if not has_docker_image(config.docker_image):
                logger.warning(
                    "Docker image %s not found. Pulling...", config.docker_image
                )
                result = subprocess.run(
                    ["docker", "pull", config.docker_image],
                    capture_output=True,
                    timeout=300,
                )
                if result.returncode != 0:
                    logger.error(
                        "Failed to pull Docker image %s: %s",
                        config.docker_image,
                        result.stderr.decode(),
                    )
                    return False

            # Generate startup script
            startup_script = self._generate_startup_script(config)

            # Build docker run command
            env_vars = {
                "DCC_MCP_GATEWAY_PORT": str(config.gateway_port),
                "DCC_MCP_REGISTRY_DIR": "/mnt/registry",
                "DCC_MCP_MAYA_HOT_RELOAD": "1" if config.enable_hot_reload else "0",
                "DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER": (
                    "1" if config.enable_gateway_failover else "0"
                ),
            }

            if config.env_vars:
                env_vars.update(config.env_vars)

            # Build docker run command
            docker_cmd = [
                "docker",
                "run",
                "--name",
                config.container_name,
                "-d",  # Detached mode
                "-p",
                f"{config.port}:8000",  # Map container port
                "-v",
                f"{config.registry_dir}:/mnt/registry",  # Mount registry volume
                "-v",
                "/tmp:/tmp",  # Share /tmp for temporary files
            ]

            # Add environment variables
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

            # Add the startup script as entrypoint
            docker_cmd.extend([
                config.docker_image,
                "mayapy",
                "-c",
                startup_script,
            ])

            logger.info(
                "Launching Docker instance %s from image %s on port %d (gateway %d)",
                config.instance_id,
                config.docker_image,
                config.port,
                config.gateway_port,
            )

            # Run docker command
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.error(
                    "Failed to start Docker container: %s",
                    result.stderr.decode(),
                )
                return False

            container_id = result.stdout.decode().strip()
            self.containers[config.instance_id] = container_id
            self.configs[config.instance_id] = config

            # Give container time to start and register
            time.sleep(2)

            # Verify container is running
            verify_cmd = ["docker", "ps", "-q", "--filter", f"id={container_id}"]
            verify_result = subprocess.run(
                verify_cmd,
                capture_output=True,
                timeout=5,
            )

            if not verify_result.stdout.decode().strip():
                logger.error(
                    "Docker container %s not running after startup",
                    container_id,
                )
                # Get logs for debugging
                logs_cmd = ["docker", "logs", container_id]
                logs_result = subprocess.run(logs_cmd, capture_output=True)
                logger.error("Container logs: %s", logs_result.stdout.decode())
                del self.containers[config.instance_id]
                return False

            logger.info("Docker instance %s started successfully", config.instance_id)
            return True

        except subprocess.TimeoutExpired:
            logger.error("Docker startup timeout for instance %s", config.instance_id)
            return False
        except Exception as exc:
            logger.error("Failed to launch Docker instance %s: %s", config.instance_id, exc)
            return False

    def stop_instance(self, instance_id: str, timeout: int = 10) -> bool:
        """Stop a running Docker container.

        Args:
            instance_id: Instance to stop
            timeout: Shutdown timeout in seconds

        Returns:
            True if container was stopped
        """
        if instance_id not in self.containers:
            logger.warning("Instance %s not found", instance_id)
            return False

        try:
            container_id = self.containers[instance_id]
            logger.info("Stopping Docker container %s", container_id)

            # Stop container with timeout
            stop_cmd = ["docker", "stop", "-t", str(timeout), container_id]
            result = subprocess.run(
                stop_cmd,
                capture_output=True,
                timeout=timeout + 5,
            )

            if result.returncode != 0:
                logger.warning(
                    "Failed to stop container gracefully: %s",
                    result.stderr.decode(),
                )

            # Remove container
            rm_cmd = ["docker", "rm", "-f", container_id]
            subprocess.run(rm_cmd, capture_output=True, timeout=5)

            del self.containers[instance_id]
            logger.info("Docker container %s stopped", container_id)
            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout stopping Docker container %s", instance_id)
            return False
        except Exception as exc:
            logger.error("Failed to stop Docker container %s: %s", instance_id, exc)
            return False

    def stop_all(self, timeout: int = 10) -> None:
        """Stop all running containers."""
        for instance_id in list(self.containers.keys()):
            self.stop_instance(instance_id, timeout=timeout)

    def list_running(self) -> List[str]:
        """List IDs of running instances."""
        running = []
        for instance_id, container_id in self.containers.items():
            # Check if container is still running
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"id={container_id}"],
                capture_output=True,
                timeout=5,
            )
            if result.stdout.decode().strip():
                running.append(instance_id)
        return running

    def get_registry_content(self) -> Dict:
        """Read current FileRegistry JSON content."""
        registry_file = Path(self.registry_dir) / "file_registry.json"
        if not registry_file.exists():
            return {}

        try:
            with open(registry_file) as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to read registry: %s", exc)
            return {}

    def cleanup(self) -> None:
        """Cleanup resources (stop all containers)."""
        self.stop_all()

    @staticmethod
    def _generate_startup_script(config: DockerMayaConfig) -> str:
        """Generate Python script to run inside Docker container."""
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
        registry_dir="{registry_dir}",
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
