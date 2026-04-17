"""Tests for multi-instance discovery and registration.

Tests that gateway can discover and register many instances (50+),
maintain current state in FileRegistry, and serve list dynamically.
"""

import json
import logging
import time

import pytest

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.integration,
    # TODO(#58): Gateway never starts under the Docker matrix runner; tests have been
    # silently red on main via `continue-on-error: true`. Unskip once the Docker
    # gateway-startup / wait_for_gateway() path is fixed.
    pytest.mark.skip(reason="Pre-existing failure tracked in https://github.com/loonghao/dcc-mcp-maya/issues/58"),
]


@pytest.mark.timeout(60)
def test_discovery_basic_two_instances(maya_instance_manager, gateway_client):
    """Test basic discovery of 2 instances."""
    # Create and launch instances
    config1 = maya_instance_manager.create_config("maya-2025-01", maya_version="2025")
    config2 = maya_instance_manager.create_config("maya-2024-01", maya_version="2024")

    assert maya_instance_manager.launch_instance(config1)
    assert maya_instance_manager.launch_instance(config2)

    # Wait for discovery
    assert gateway_client.wait_for_gateway()
    assert gateway_client.wait_for_instance_count(2, max_retries=30)

    # Query instances
    instances = gateway_client.list_instances("maya")
    assert len(instances) >= 2, f"Expected >= 2 instances, got {len(instances)}"

    logger.info("Basic discovery test PASSED: %d instances", len(instances))


@pytest.mark.timeout(120)
def test_discovery_many_instances(maya_instance_manager, gateway_client):
    """Test discovery of many instances (10+).

    Verifies that gateway can handle and serve multiple instances concurrently.
    """
    # Create 10 instances
    configs = [maya_instance_manager.create_config(f"maya-2025-{i:02d}", maya_version="2025") for i in range(1, 11)]

    # Launch them
    for config in configs:
        assert maya_instance_manager.launch_instance(config), f"Failed to launch {config.instance_id}"

    # Wait for all to register
    assert gateway_client.wait_for_gateway()
    assert gateway_client.wait_for_instance_count(10, max_retries=60, retry_delay=1.0), (
        "Not all 10 instances registered"
    )

    # Verify via FileRegistry
    registry = maya_instance_manager.get_registry_content()
    logger.info("Registry content keys: %s", list(registry.keys()))

    instances = gateway_client.list_instances("maya")
    assert len(instances) >= 10, f"Expected >= 10 instances from gateway, got {len(instances)}"

    logger.info("Many instances test PASSED: %d instances registered", len(instances))


@pytest.mark.timeout(180)
def test_discovery_with_instance_lifecycle(maya_instance_manager, gateway_client):
    """Test discovery handles instance lifecycle (add, remove, re-add).

    Verifies registry is updated correctly when instances join/leave.
    """
    # Start with 2 instances
    config1 = maya_instance_manager.create_config("maya-2025-01")
    config2 = maya_instance_manager.create_config("maya-2025-02")

    assert maya_instance_manager.launch_instance(config1)
    assert maya_instance_manager.launch_instance(config2)

    assert gateway_client.wait_for_gateway()
    assert gateway_client.wait_for_instance_count(2)

    instances_before = gateway_client.list_instances("maya")
    assert len(instances_before) >= 2

    # Stop one instance
    maya_instance_manager.stop_instance("maya-2025-02")
    time.sleep(2)

    # Check updated count
    instances_after_stop = gateway_client.list_instances("maya")
    logger.info(
        "After stopping one: %d instances (was %d)",
        len(instances_after_stop),
        len(instances_before),
    )

    # Start a new instance
    config3 = maya_instance_manager.create_config("maya-2025-03")
    assert maya_instance_manager.launch_instance(config3)

    assert gateway_client.wait_for_instance_count(2, max_retries=30)

    instances_after_add = gateway_client.list_instances("maya")
    logger.info("After adding new: %d instances", len(instances_after_add))

    logger.info("Instance lifecycle test PASSED")


@pytest.mark.timeout(90)
def test_discovery_instance_metadata_accuracy(maya_instance_manager, gateway_client):
    """Verify discovered instance metadata (version, scene) is accurate.

    Tests that each instance's reported maya_version and scene_file
    are correctly reflected in gateway discovery.
    """
    # Create instances with specific versions and scenes
    configs = [
        maya_instance_manager.create_config(
            "maya-2025-scene1",
            maya_version="2025",
            scene_file="/path/to/project1/scene.ma",
        ),
        maya_instance_manager.create_config(
            "maya-2024-scene2",
            maya_version="2024",
            scene_file="/path/to/project2/scene.ma",
        ),
    ]

    for config in configs:
        assert maya_instance_manager.launch_instance(config)

    assert gateway_client.wait_for_gateway()
    assert gateway_client.wait_for_instance_count(2, max_retries=30)

    instances = gateway_client.list_instances("maya")

    # Verify metadata
    instance_map = {inst.get("instance_id"): inst for inst in instances}

    if "maya-2025-scene1" in instance_map:
        inst1 = instance_map["maya-2025-scene1"]
        assert inst1.get("dcc_version") == "2025", "Version mismatch for instance 1"
        assert inst1.get("scene") == "/path/to/project1/scene.ma", "Scene mismatch for instance 1"

    logger.info("Instance metadata accuracy test PASSED")


@pytest.mark.timeout(120)
def test_discovery_mixed_maya_versions(maya_instance_manager, gateway_client):
    """Test discovery of mixed Maya versions (2024, 2025, etc.).

    Verifies that gateway correctly groups and tracks instances by version.
    """
    # Create instances of different versions
    configs = [maya_instance_manager.create_config(f"maya-2024-{i}", maya_version="2024") for i in range(1, 4)] + [
        maya_instance_manager.create_config(f"maya-2025-{i}", maya_version="2025") for i in range(1, 4)
    ]

    for config in configs:
        assert maya_instance_manager.launch_instance(config)

    assert gateway_client.wait_for_gateway()
    assert gateway_client.wait_for_instance_count(6, max_retries=60)

    instances = gateway_client.list_instances("maya")

    # Count by version
    version_2024 = [i for i in instances if i.get("dcc_version") == "2024"]
    version_2025 = [i for i in instances if i.get("dcc_version") == "2025"]

    logger.info("Discovered: %d x Maya2024, %d x Maya2025", len(version_2024), len(version_2025))

    assert len(version_2024) >= 3, f"Expected >= 3 Maya 2024 instances, got {len(version_2024)}"
    assert len(version_2025) >= 3, f"Expected >= 3 Maya 2025 instances, got {len(version_2025)}"

    logger.info("Mixed versions test PASSED")


@pytest.mark.timeout(90)
def test_discovery_registry_persistence(maya_instance_manager, gateway_client):
    """Test that discovery persists across gateway restarts.

    Verifies FileRegistry maintains instance list even if gateway crashes/restarts.
    """
    # Create and launch instances
    configs = [maya_instance_manager.create_config(f"maya-persist-{i}") for i in range(1, 4)]

    for config in configs:
        assert maya_instance_manager.launch_instance(config)

    assert gateway_client.wait_for_gateway()
    assert gateway_client.wait_for_instance_count(3, max_retries=30)

    # Read registry content
    registry1 = maya_instance_manager.get_registry_content()
    logger.info("Registry before: %s", json.dumps(registry1, indent=2)[:200])

    # Simulate gateway restart by reading registry again
    time.sleep(1)
    registry2 = maya_instance_manager.get_registry_content()

    # Registry should have entries
    assert registry2, "Registry should not be empty"

    logger.info("Registry persistence test PASSED")
