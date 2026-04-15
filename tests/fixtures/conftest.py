"""Pytest fixtures for multi-instance gateway and failover testing."""

import logging
import time
from typing import Any, Dict, List, Optional

import pytest
import requests

logger = logging.getLogger(__name__)


class GatewayTestClient:
    """HTTP client for gateway interaction and assertions."""

    def __init__(self, gateway_url: str, timeout: int = 10):
        """Initialize gateway test client.

        Args:
            gateway_url: Base URL of gateway (e.g., "http://127.0.0.1:9765")
            timeout: Request timeout in seconds
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _request(
        self, method: str, endpoint: str, **kwargs
    ) -> requests.Response:
        """Make HTTP request to gateway.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/mcp/tools/list")
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.gateway_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.error(
                "Gateway request failed: %s %s - %s", method, url, exc
            )
            raise

    def health_check(self) -> bool:
        """Check if gateway is healthy.

        Returns:
            True if gateway responds to health check
        """
        try:
            resp = self._request("GET", "/health")
            return resp.status_code == 200
        except Exception:
            return False

    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from gateway.

        Returns:
            List of tool definitions (name, description, input_schema)
        """
        resp = self._request("GET", "/mcp/tools/list")
        data = resp.json()
        return data.get("tools", [])

    def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool via gateway.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result
        """
        body = {"name": tool_name, "arguments": arguments}
        resp = self._request("POST", "/mcp/tools/call", json=body)
        return resp.json()

    def list_instances(self, dcc_type: str = "maya") -> List[Dict[str, Any]]:
        """Get list of registered instances of given DCC type.

        Calls the gateway's 'list_instances' tool.

        Args:
            dcc_type: DCC type to list (default "maya")

        Returns:
            List of instance entries (id, version, scene, status, etc.)
        """
        try:
            result = self.call_tool("list_instances", {"dcc_type": dcc_type})
            if "error" in result:
                logger.warning("Failed to list instances: %s", result["error"])
                return []

            # Parse response (format depends on actual tool implementation)
            if isinstance(result, dict) and "instances" in result:
                return result["instances"]
            elif isinstance(result, list):
                return result
            else:
                return []
        except Exception as exc:
            logger.error("Exception listing instances: %s", exc)
            return []

    def find_gateway_instance(self) -> Optional[str]:
        """Find which instance is the current gateway.

        Returns:
            Instance ID of gateway, or None if not found
        """
        try:
            result = self.call_tool("get_gateway_info", {})
            if isinstance(result, dict):
                return result.get("gateway_instance_id")
        except Exception:
            pass
        return None

    def wait_for_gateway(self, max_retries: int = 30, retry_delay: float = 1.0) -> bool:
        """Wait for gateway to become available.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            True if gateway became available, False if timeout
        """
        for attempt in range(max_retries):
            if self.health_check():
                logger.info("Gateway available after %d attempts", attempt)
                return True

            logger.debug("Gateway not yet available, retrying in %fs", retry_delay)
            time.sleep(retry_delay)

        logger.error("Gateway not available after %d attempts", max_retries)
        return False

    def wait_for_instance_count(
        self,
        expected_count: int,
        dcc_type: str = "maya",
        max_retries: int = 20,
        retry_delay: float = 0.5,
    ) -> bool:
        """Wait for expected number of instances to register with gateway.

        Args:
            expected_count: Expected number of instances
            dcc_type: DCC type to check
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            True if expected count reached, False if timeout
        """
        for attempt in range(max_retries):
            instances = self.list_instances(dcc_type)
            if len(instances) >= expected_count:
                logger.info(
                    "Reached %d instances (expected %d) after %d attempts",
                    len(instances),
                    expected_count,
                    attempt,
                )
                return True

            logger.debug(
                "Only %d instances registered, waiting for %d",
                len(instances),
                expected_count,
            )
            time.sleep(retry_delay)

        logger.error(
            "Timeout waiting for %d instances (got %d)",
            expected_count,
            len(instances),
        )
        return False


@pytest.fixture
def gateway_client() -> GatewayTestClient:
    """Fixture providing a gateway test client.

    Connects to gateway at http://127.0.0.1:9765 (default).
    """
    return GatewayTestClient("http://127.0.0.1:9765")


@pytest.fixture
def temp_registry_dir(tmp_path):
    """Fixture providing a temporary directory for FileRegistry."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    return str(registry_dir)


@pytest.fixture
def maya_instance_manager(temp_registry_dir):
    """Fixture providing a MayaInstanceManager with temp registry.

    Automatically cleans up all instances after test.
    """
    from maya_instances import MayaInstanceManager

    manager = MayaInstanceManager(
        gateway_port=9765, registry_dir=temp_registry_dir
    )

    yield manager

    # Cleanup
    manager.cleanup()
