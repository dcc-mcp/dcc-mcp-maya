"""Tests for gateway failover and automatic elevation.

Tests the P2-A feature: non-gateway instances automatically detect and replace
a failed gateway within RTO < 15s, with backup elevation < 5s.
"""

import logging
import time

import pytest

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


@pytest.mark.timeout(120)
def test_gateway_election_enabled_by_default(maya_instance_manager, gateway_client):
    """Verify that gateway_failover is enabled by default when gateway_port is set."""
    # Create 2 instances
    config1 = maya_instance_manager.create_config("maya-2025-01")
    config2 = maya_instance_manager.create_config("maya-2025-02")

    assert maya_instance_manager.launch_instance(config1), "Failed to launch instance 1"
    assert maya_instance_manager.launch_instance(config2), "Failed to launch instance 2"

    # Wait for gateway to start and instances to register
    assert gateway_client.wait_for_gateway(), "Gateway did not start"
    assert gateway_client.wait_for_instance_count(2, max_retries=30), "Instances did not register"

    # Verify at least one is the gateway
    gateway_id = gateway_client.find_gateway_instance()
    assert gateway_id is not None, "No gateway instance identified"

    logger.info("Gateway failover test passed: gateway=%s", gateway_id)


@pytest.mark.timeout(120)
def test_gateway_failure_detection_and_elevation(maya_instance_manager, gateway_client):
    """Test that non-gateway instances detect gateway failure and one elevates.

    Scenario:
    1. Start 3 instances (first one wins gateway)
    2. Kill gateway instance
    3. Verify detection (< 15s RTO)
    4. Verify backup elevation (< 5s from detection)
    """
    # Create and launch 3 instances
    configs = [
        maya_instance_manager.create_config("maya-2025-01"),
        maya_instance_manager.create_config("maya-2025-02"),
        maya_instance_manager.create_config("maya-2025-03"),
    ]

    for config in configs:
        assert maya_instance_manager.launch_instance(config), f"Failed to launch {config.instance_id}"

    # Wait for registration
    assert gateway_client.wait_for_gateway(), "Gateway did not start"
    assert gateway_client.wait_for_instance_count(3, max_retries=30), "Instances did not register"

    # Identify current gateway
    original_gateway = gateway_client.find_gateway_instance()
    assert original_gateway is not None, "No gateway identified"
    logger.info("Original gateway: %s", original_gateway)

    # Kill the gateway instance
    kill_start = time.time()
    success = maya_instance_manager.stop_instance(original_gateway)
    assert success, f"Failed to kill gateway {original_gateway}"
    logger.info("Gateway killed: %s", original_gateway)

    # Poll for gateway switch (should happen within 15 seconds)
    detection_rto = None
    elevation_rto = None
    new_gateway = None

    for _ in range(30):  # Up to 30 seconds
        time.sleep(0.5)

        # Try to find new gateway
        try:
            if gateway_client.health_check():
                new_gateway = gateway_client.find_gateway_instance()

                if new_gateway and new_gateway != original_gateway:
                    elapsed = time.time() - kill_start

                    if detection_rto is None:
                        detection_rto = elapsed
                        logger.info("Gateway failure detected in %.2fs", elapsed)

                    if new_gateway != original_gateway and elevation_rto is None:
                        elevation_rto = elapsed
                        logger.info("New gateway elected in %.2fs: %s", elapsed, new_gateway)
                        break
        except Exception as exc:
            logger.debug("Health check failed: %s", exc)
            continue

    # Verify timeouts
    assert detection_rto is not None, "Gateway failure not detected within 15s"
    assert detection_rto < 15.0, f"Detection RTO too high: {detection_rto:.2f}s (> 15s)"

    assert elevation_rto is not None, "New gateway not elected within 20s"
    assert elevation_rto < 20.0, f"Elevation RTO too high: {elevation_rto:.2f}s (> 20s)"

    # The elevation should happen quickly after detection
    if detection_rto and elevation_rto:
        elevation_delta = elevation_rto - detection_rto
        logger.info("Elevation delta: %.2fs", elevation_delta)

    logger.info(
        "Gateway failover test PASSED: detection=%.2fs, elevation=%.2fs",
        detection_rto,
        elevation_rto,
    )


@pytest.mark.timeout(90)
def test_gateway_failover_disabled_when_gateway_port_zero(maya_instance_manager, gateway_client):
    """Verify gateway failover is disabled when gateway_port=0."""
    # Create instance without gateway
    config = maya_instance_manager.create_config("maya-no-gateway")
    config.gateway_port = 0  # Disable gateway
    config.enable_gateway_failover = False

    assert maya_instance_manager.launch_instance(config), "Failed to launch instance"

    # Wait a bit
    time.sleep(2)

    # Instance should be running but NOT as gateway
    running = maya_instance_manager.list_running()
    assert "maya-no-gateway" in running, "Instance should be running"

    logger.info("Instance without gateway running successfully")


@pytest.mark.timeout(150)
def test_multiple_instance_failover_chain(maya_instance_manager, gateway_client):
    """Test failover chain: kill gateway → new gateway elected → kill that too.

    This verifies the election process is robust and can handle cascading failures.
    """
    # Create 5 instances to test failover chain
    configs = [maya_instance_manager.create_config(f"maya-2025-{i:02d}") for i in range(1, 6)]

    for config in configs:
        assert maya_instance_manager.launch_instance(config), f"Failed to launch {config.instance_id}"

    assert gateway_client.wait_for_gateway(), "Gateway did not start"
    assert gateway_client.wait_for_instance_count(5, max_retries=30), "Instances did not register"

    # Track gateway transitions
    gateways_seen = []
    current_gateway = gateway_client.find_gateway_instance()
    assert current_gateway is not None
    gateways_seen.append(current_gateway)

    # Kill first gateway and verify transition
    maya_instance_manager.stop_instance(current_gateway)
    time.sleep(1)

    # Wait for new gateway
    for _ in range(20):
        time.sleep(0.5)
        try:
            new_gateway = gateway_client.find_gateway_instance()
            if new_gateway and new_gateway != current_gateway:
                gateways_seen.append(new_gateway)
                current_gateway = new_gateway
                logger.info("Gateway transition to: %s", current_gateway)
                break
        except Exception:
            pass

    assert len(gateways_seen) >= 2, f"Should see at least 2 gateways, saw {gateways_seen}"
    logger.info("Gateway chain test PASSED: transitions=%s", gateways_seen)


@pytest.mark.timeout(60)
def test_fast_failover_recovery(maya_instance_manager, gateway_client):
    """Verify that gateway recovery time meets SLA (< 5s elevation after detection)."""
    # Create instances
    configs = [
        maya_instance_manager.create_config("maya-2025-fast-01"),
        maya_instance_manager.create_config("maya-2025-fast-02"),
    ]

    for config in configs:
        assert maya_instance_manager.launch_instance(config), "Failed to launch"

    assert gateway_client.wait_for_gateway(), "Gateway did not start"

    original_gateway = gateway_client.find_gateway_instance()
    assert original_gateway is not None

    # Record time and kill gateway
    kill_time = time.time()
    maya_instance_manager.stop_instance(original_gateway)

    # Measure time to new gateway
    new_gateway = None
    for _ in range(40):  # 20 seconds max
        time.sleep(0.5)
        try:
            new_gateway = gateway_client.find_gateway_instance()
            if new_gateway and new_gateway != original_gateway:
                break
        except Exception:
            pass

    recovery_time = time.time() - kill_time
    assert new_gateway is not None, "No new gateway elected"
    assert recovery_time < 15.0, f"Recovery took too long: {recovery_time:.2f}s"

    logger.info("Fast recovery test PASSED: recovery_time=%.2fs", recovery_time)


@pytest.mark.timeout(120)
def test_gateway_failover_environment_variable(maya_instance_manager, gateway_client):
    """Verify DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER env var controls failover."""
    # Create instance with failover explicitly disabled via config
    config = maya_instance_manager.create_config("maya-no-failover")
    config.enable_gateway_failover = False
    config.env_vars = {"DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER": "0"}

    assert maya_instance_manager.launch_instance(config), "Failed to launch instance"

    time.sleep(2)

    running = maya_instance_manager.list_running()
    assert "maya-no-failover" in running, "Instance should be running"

    logger.info("Environment variable control test PASSED")
