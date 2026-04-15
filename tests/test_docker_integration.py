"""Integration tests for Docker-based Maya MCP instances.

Tests that can run in Docker environments with mayapy images,
verifying multi-version and multi-instance capabilities.
"""

import os
import pytest

from fixtures.docker_maya import is_docker_available
from fixtures.instance_factory import get_instance_manager

# Skip all tests in this file if Docker is not available
pytestmark = pytest.mark.skipif(
    not is_docker_available(), reason="Docker not available in test environment"
)


class TestDockerInstanceManager:
    """Tests for DockerMayaInstanceManager."""

    def test_docker_manager_creation(self, temp_registry_dir):
        """Test creating Docker instance manager."""
        try:
            manager = get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
            assert manager is not None
            manager.cleanup()
        except RuntimeError:
            pytest.skip("Docker Maya images not available")

    def test_create_docker_config_2025(self, temp_registry_dir):
        """Test creating config for Maya 2025."""
        try:
            manager = get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
            config = manager.create_config(
                "maya-2025-test",
                maya_version="2025",
            )
            assert config.instance_id == "maya-2025-test"
            assert config.maya_version == "2025"
            assert "2025" in config.docker_image
            manager.cleanup()
        except RuntimeError:
            pytest.skip("Docker Maya images not available")

    def test_create_docker_config_2024(self, temp_registry_dir):
        """Test creating config for Maya 2024."""
        try:
            manager = get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
            config = manager.create_config(
                "maya-2024-test",
                maya_version="2024",
            )
            assert config.instance_id == "maya-2024-test"
            assert config.maya_version == "2024"
            assert "2024" in config.docker_image
            manager.cleanup()
        except RuntimeError:
            pytest.skip("Docker Maya images not available")

    def test_create_docker_config_2023(self, temp_registry_dir):
        """Test creating config for Maya 2023."""
        try:
            manager = get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
            config = manager.create_config(
                "maya-2023-test",
                maya_version="2023",
            )
            assert config.instance_id == "maya-2023-test"
            assert config.maya_version == "2023"
            assert "2023" in config.docker_image
            manager.cleanup()
        except RuntimeError:
            pytest.skip("Docker Maya images not available")

    def test_unsupported_maya_version(self, temp_registry_dir):
        """Test error handling for unsupported Maya version."""
        try:
            manager = get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
            with pytest.raises(ValueError, match="Unsupported Maya version"):
                manager.create_config("test", maya_version="2020")
            manager.cleanup()
        except RuntimeError:
            pytest.skip("Docker Maya images not available")

    def test_auto_detection_prefers_docker(self, temp_registry_dir, monkeypatch):
        """Test that auto-detection prefers Docker when available.

        Note: This test requires Docker to be actually available.
        """
        # Force Docker mode via environment variable
        monkeypatch.setenv("DCC_MCP_FORCE_DOCKER", "1")

        try:
            manager = get_instance_manager(
                mode=None,  # Auto-detect
                registry_dir=temp_registry_dir,
            )
            # If we got here, Docker was available
            assert manager is not None
            manager.cleanup()
        except RuntimeError:
            # Expected if Docker images not available
            pytest.skip("Docker Maya images not available; auto-detection fallback to local mayapy expected")


class TestInstanceFactoryAutoSelection:
    """Tests for automatic instance manager selection."""

    def test_factory_selects_docker_when_forced(self, temp_registry_dir, monkeypatch):
        """Test explicit Docker mode selection."""
        monkeypatch.setenv("DCC_MCP_FORCE_DOCKER", "1")

        try:
            manager = get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
            from fixtures.docker_maya import DockerMayaInstanceManager
            assert isinstance(manager, DockerMayaInstanceManager)
            manager.cleanup()
        except RuntimeError:
            pytest.skip("Docker Maya images not available")

    def test_factory_falls_back_to_local(self, temp_registry_dir, monkeypatch):
        """Test fallback to local mayapy when Docker unavailable."""
        # Don't force Docker, let it try local
        monkeypatch.delenv("DCC_MCP_FORCE_DOCKER", raising=False)

        try:
            manager = get_instance_manager(
                mode="local",
                registry_dir=temp_registry_dir,
            )
            from fixtures.maya_instances import MayaInstanceManager
            assert isinstance(manager, MayaInstanceManager)
            manager.cleanup()
        except RuntimeError as exc:
            pytest.skip(f"Local mayapy not available: {exc}")

    def test_factory_raises_no_suitable_manager(self, temp_registry_dir, monkeypatch):
        """Test error when no suitable manager is available."""
        # Force Docker mode with unavailable image
        monkeypatch.setenv("DCC_MCP_FORCE_DOCKER", "1")
        monkeypatch.setenv("DCC_MCP_DOCKER_REGISTRY", "nonexistent.registry/")

        # This should raise because the registry is invalid
        with pytest.raises(RuntimeError):
            get_instance_manager(
                mode="docker",
                registry_dir=temp_registry_dir,
            )
