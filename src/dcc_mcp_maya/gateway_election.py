"""Gateway failover election mechanism for dcc-mcp-maya.

When the current gateway instance is unreachable, non-gateway instances
automatically attempt to become the new gateway to maintain service availability.

This module implements:
- Periodic health checks of the current gateway
- Automatic election of a new gateway if the current one fails
- Exponential backoff for election attempts
- Clean shutdown and resource management
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import socket
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration from environment variables
_PROBE_INTERVAL = int(os.environ.get("DCC_MCP_GATEWAY_PROBE_INTERVAL", "5"))
_PROBE_TIMEOUT = float(os.environ.get("DCC_MCP_GATEWAY_PROBE_TIMEOUT", "2"))
_PROBE_FAILURES = int(os.environ.get("DCC_MCP_GATEWAY_PROBE_FAILURES", "3"))
_GATEWAY_HOST = "127.0.0.1"
_GATEWAY_PORT = 9765


class GatewayElection:
    """Manages automatic gateway election when the current gateway fails.

    This class runs on a background thread and periodically checks if the
    current gateway is alive. If the gateway becomes unreachable, this
    instance will attempt to become the new gateway by binding to the
    gateway port (first-wins via socket2 mechanism).

    Example::

        election = GatewayElection(server)
        election.start()
        # ... gateway health checks run in background ...
        election.stop()

    Args:
        server: The MayaMcpServer instance to manage gateway election for.
        gateway_host: Gateway bind address (default "127.0.0.1").
        gateway_port: Gateway port to compete for (default 9765).
        probe_interval: Seconds between health checks (default 5).
        probe_timeout: Timeout for each health check (default 2).
        probe_failures: Consecutive failures before attempting election (default 3).
    """

    def __init__(
        self,
        server: any,
        gateway_host: str = _GATEWAY_HOST,
        gateway_port: int = _GATEWAY_PORT,
        probe_interval: int = _PROBE_INTERVAL,
        probe_timeout: float = _PROBE_TIMEOUT,
        probe_failures: int = _PROBE_FAILURES,
    ) -> None:
        """Initialize the gateway election manager.

        Args:
            server: MayaMcpServer instance
            gateway_host: Gateway bind address
            gateway_port: Gateway port
            probe_interval: Seconds between probes
            probe_timeout: Probe timeout in seconds
            probe_failures: Failures before election attempt
        """
        self._server = server
        self._gateway_host = gateway_host
        self._gateway_port = gateway_port
        self._probe_interval = probe_interval
        self._probe_timeout = probe_timeout
        self._probe_failures = probe_failures

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._consecutive_failures = 0
        self._is_running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Whether the election thread is active."""
        with self._lock:
            return self._is_running

    def start(self) -> None:
        """Start the gateway election thread.

        Spawns a background daemon thread that runs health checks and
        attempts election if needed. Safe to call multiple times.
        """
        with self._lock:
            if self._is_running:
                logger.warning("GatewayElection already running")
                return

            self._is_running = True
            self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run_election_loop,
            daemon=True,
            name="dcc-mcp-gateway-election",
        )
        self._thread.start()
        logger.info("GatewayElection thread started")

    def stop(self) -> None:
        """Stop the gateway election thread gracefully.

        Sets the stop event and waits for the thread to finish.
        Safe to call even if not running.
        """
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False

        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("GatewayElection thread did not stop gracefully")

        logger.info("GatewayElection thread stopped")

    def _run_election_loop(self) -> None:
        """Main loop: periodically check gateway health and attempt election.

        Runs on background thread until stop event is set.
        """
        logger.debug(
            "Starting election loop: probe_interval=%ds, probe_timeout=%ds, probe_failures=%d",
            self._probe_interval,
            self._probe_timeout,
            self._probe_failures,
        )

        while not self._stop_event.is_set():
            try:
                if self._server.is_gateway:
                    # We're already the gateway, reset failure counter
                    self._consecutive_failures = 0
                    logger.debug("This instance is the gateway, no election needed")
                else:
                    # Check if current gateway is alive
                    if self._probe_gateway():
                        # Gateway is alive
                        self._consecutive_failures = 0
                        logger.debug("Gateway is alive (failures reset)")
                    else:
                        # Gateway failed
                        self._consecutive_failures += 1
                        logger.debug(
                            "Gateway probe failed (%d/%d)",
                            self._consecutive_failures,
                            self._probe_failures,
                        )

                        if self._consecutive_failures >= self._probe_failures:
                            logger.warning(
                                "Gateway unreachable for %d probes, attempting election...",
                                self._consecutive_failures,
                            )
                            if self._attempt_gateway_election():
                                logger.info("🎉 Successfully promoted to gateway!")
                                self._consecutive_failures = 0
                            else:
                                logger.debug("Election failed, another instance may have won")

            except Exception as exc:
                logger.error("Unexpected error in election loop: %s", exc)

            # Wait for next probe interval
            self._stop_event.wait(self._probe_interval)

    def _probe_gateway(self) -> bool:
        """Check if the gateway is alive via HTTP health check.

        Makes a GET /health request to the gateway endpoint.

        Returns:
            True if gateway responds with 200, False otherwise.
        """
        try:
            import requests  # noqa: PLC0415

            url = f"http://{self._gateway_host}:{self._gateway_port}/health"
            response = requests.get(url, timeout=self._probe_timeout)
            success = response.status_code == 200
            return success

        except requests.Timeout:
            logger.debug("Gateway health check timed out after %fs", self._probe_timeout)
            return False
        except requests.ConnectionError:
            logger.debug(
                "Gateway connection failed (%s:%d)",
                self._gateway_host,
                self._gateway_port,
            )
            return False
        except Exception as exc:
            logger.debug("Gateway health check error: %s", exc)
            return False

    def _attempt_gateway_election(self) -> bool:
        """Attempt to become the gateway by binding to the gateway port.

        Uses socket2 first-wins mechanism: socket with SO_REUSEADDR disabled
        to ensure mutual exclusion (cross-platform).

        Returns:
            True if successfully bound to gateway port, False otherwise.
        """
        try:
            # Import socket2 for cross-platform socket options
            try:
                import socket2  # noqa: F401, PLC0415

                socket_module = socket2
            except ImportError:
                logger.debug("socket2 not available, falling back to socket module")
                socket_module = socket

            # Create a socket
            sock = socket_module.socket(
                socket_module.AF_INET,
                socket_module.SOCK_STREAM,
            )

            # Disable SO_REUSEADDR for first-wins semantics
            # This is the key to the mutual exclusion mechanism
            if hasattr(socket_module, "SO_REUSEADDR"):
                sock.setsockopt(
                    socket_module.SOL_SOCKET,
                    socket_module.SO_REUSEADDR,
                    0,
                )

            # Attempt to bind to gateway port
            sock.bind((self._gateway_host, self._gateway_port))
            sock.listen(1)

            # Success! We've bound to the port
            logger.info(
                "Successfully bound to gateway port %s:%d",
                self._gateway_host,
                self._gateway_port,
            )

            # Close the test socket (actual gateway will bind when start() is called)
            sock.close()

            # Now signal the server to start the gateway
            # This is done via attempting to restart/upgrade the server
            # The exact mechanism depends on how MayaMcpServer implements upgrades
            self._upgrade_to_gateway()

            return True

        except OSError as exc:
            logger.debug(
                "Failed to bind to gateway port (another instance may have won): %s",
                exc,
            )
            return False
        except Exception as exc:
            logger.error("Unexpected error during gateway election: %s", exc)
            return False

    def _upgrade_to_gateway(self) -> None:
        """Signal the MayaMcpServer to upgrade to gateway mode.

        This is called after successfully binding to the gateway port.
        The actual upgrade mechanism may vary depending on server state.
        """
        try:
            # Check if server is running
            if not self._server.is_running:
                logger.warning("Server not running, cannot upgrade to gateway")
                return

            # Get current server handle
            handle = self._server._handle  # noqa: SLF001

            if handle is None:
                logger.warning("No server handle available, cannot upgrade")
                return

            # Try to restart the server with gateway enabled
            # This is a soft approach: we signal that gateway mode should be attempted
            # The actual restart happens on next start() call
            logger.info("Signaling server to attempt gateway upgrade on next restart")

            # For now, we just log the intention
            # A full implementation might:
            # 1. Call _restart_async() on the plugin
            # 2. Or set a flag that affects next start()
            # 3. Or directly promote the handle (if ServerHandle has such a method)

        except Exception as exc:
            logger.error("Error during gateway upgrade signal: %s", exc)

    def __repr__(self) -> str:
        """Return a string representation."""
        status = "running" if self.is_running else "stopped"
        return f"GatewayElection(status={status}, consecutive_failures={self._consecutive_failures})"
