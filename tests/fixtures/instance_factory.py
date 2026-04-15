"""Factory for creating appropriate Maya instance managers (local or Docker).

This module provides intelligent selection between local mayapy and Docker-based
instance managers, with automatic fallback and configuration detection.
"""

import logging
import os
from typing import Optional, Union

from .docker_maya import DockerMayaInstanceManager, is_docker_available
from .maya_instances import MayaInstanceManager, check_mayapy_available

logger = logging.getLogger(__name__)


def get_instance_manager(
    gateway_port: int = 9765,
    registry_dir: Optional[str] = None,
    mode: Optional[str] = None,
) -> Union[MayaInstanceManager, DockerMayaInstanceManager]:
    """Create an appropriate Maya instance manager based on environment.

    Selection logic:
    1. If mode is explicitly specified, use that mode
    2. If DCC_MCP_FORCE_DOCKER environment variable is set, use Docker
    3. If Docker is available and has images, prefer Docker
    4. Otherwise, fall back to local mayapy
    5. If neither is available, raise an error

    Args:
        gateway_port: Shared gateway port for instances
        registry_dir: Shared registry directory
        mode: Explicit mode selection ("local", "docker", or None for auto)

    Returns:
        MayaInstanceManager or DockerMayaInstanceManager instance

    Raises:
        RuntimeError: If no suitable instance manager can be created
    """
    force_docker = os.getenv("DCC_MCP_FORCE_DOCKER", "").lower() in ("1", "true", "yes")
    docker_registry = os.getenv("DCC_MCP_DOCKER_REGISTRY", "")

    # Explicit mode selection
    if mode == "docker":
        logger.info("Using Docker mode (explicit)")
        try:
            return DockerMayaInstanceManager(
                gateway_port=gateway_port,
                registry_dir=registry_dir,
                docker_registry=docker_registry if docker_registry else None,
            )
        except RuntimeError as exc:
            logger.error("Docker mode requested but unavailable: %s", exc)
            raise

    if mode == "local":
        logger.info("Using local mayapy mode (explicit)")
        if not check_mayapy_available():
            raise RuntimeError(
                "Local mayapy mode requested but no mayapy found. Install Maya or use Docker mode instead."
            )
        return MayaInstanceManager(gateway_port=gateway_port, registry_dir=registry_dir)

    # Auto-detection
    logger.info("Auto-detecting instance manager mode...")

    # Check for forced Docker
    if force_docker:
        logger.info("DCC_MCP_FORCE_DOCKER set; using Docker mode")
        try:
            return DockerMayaInstanceManager(
                gateway_port=gateway_port,
                registry_dir=registry_dir,
                docker_registry=docker_registry if docker_registry else None,
            )
        except RuntimeError as exc:
            logger.warning("Docker forced but not available: %s. Falling back to local mayapy.", exc)

    # Try Docker first in CI environments, but only if Maya images are available
    if is_docker_available():
        from .docker_maya import DOCKER_IMAGES, has_docker_image

        has_maya_images = any(has_docker_image(img) for img in DOCKER_IMAGES.values())
        if has_maya_images:
            logger.info("Docker is available with Maya images; using Docker mode")
            try:
                return DockerMayaInstanceManager(
                    gateway_port=gateway_port,
                    registry_dir=registry_dir,
                    docker_registry=docker_registry if docker_registry else None,
                )
            except RuntimeError as exc:
                logger.warning("Docker available but initialization failed: %s. Trying local mayapy.", exc)
        else:
            logger.info("Docker available but no Maya images found; skipping Docker mode")

    # Fall back to local mayapy
    if check_mayapy_available():
        logger.info("Using local mayapy mode (fallback)")
        return MayaInstanceManager(gateway_port=gateway_port, registry_dir=registry_dir)

    # No suitable manager found
    raise RuntimeError(
        "No suitable Maya instance manager available. "
        "Either install Maya locally or ensure Docker with mayapy images is available."
    )
