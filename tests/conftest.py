"""Shared test fixtures and helpers for dcc-mcp-maya tests.

Provides:
- ``load_skill_script(skill_dir, script_name)`` — load a skill script by path
- ``make_mock_maya(cmds_attrs, mel_attrs)`` — build a (mock_maya, mock_cmds, mock_mel) triple
- ``mock_maya_modules`` — autouse fixture for server tests
- ``load_and_call(rel_path, mock_cmds, func_name, **kwargs)`` — load + call with mock active
- ``load_and_call_with_mel(rel_path, mock_cmds, mock_mel, **kwargs)`` — like load_and_call but also patches maya.mel
- ``gateway_client`` — GatewayTestClient for multi-instance testing
- ``temp_registry_dir`` — temp directory for FileRegistry
- ``maya_instance_manager`` — MayaInstanceManager for launching instances
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest
import requests

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def load_skill_script(skill_dir: str, script_name: str):
    """Load a skill script module by path.

    Uses a unique module name per call to avoid module cache collisions
    when the same script is loaded multiple times in a test session.

    Args:
        skill_dir: Directory name under ``skills/`` (may contain hyphens).
        script_name: Script stem name (without ``.py`` extension).

    Returns:
        The loaded module object.
    """
    _MOD_COUNTER[0] += 1
    script_path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_mock_maya(
    cmds_attrs: Optional[Dict] = None,
    mel_attrs: Optional[Dict] = None,
) -> Tuple[MagicMock, MagicMock, MagicMock]:
    """Return ``(mock_maya, mock_cmds, mock_mel)`` with ``.cmds`` and ``.mel`` wired.

    Args:
        cmds_attrs: Optional dict of attribute name → return value to set on
            ``mock_cmds`` (e.g. ``{"objExists": MagicMock(return_value=True)}``).
        mel_attrs: Optional dict of attribute name → return value to set on
            ``mock_mel``.

    Returns:
        Tuple of ``(mock_maya, mock_cmds, mock_mel)``.
    """
    mock_cmds = MagicMock()
    mock_mel = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_maya.mel = mock_mel
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    if mel_attrs:
        for k, v in mel_attrs.items():
            setattr(mock_mel, k, v)
    return mock_maya, mock_cmds, mock_mel


_LOAD_COUNTER = [0]


def load_and_call(rel_path: str, mock_cmds: MagicMock, func_name: str = "main", **kwargs) -> Any:
    """Load a skill script and call a function with the Maya mock active throughout.

    This helper ensures the ``maya`` / ``maya.cmds`` mock is patched both during
    module *loading* and function *execution*, which is required for scripts that
    do ``import maya.cmds as cmds`` at the top level of the function body.

    Args:
        rel_path: Path relative to the ``skills/`` root, e.g.
            ``"maya-scene/scripts/create_object.py"``.
        mock_cmds: The :class:`~unittest.mock.MagicMock` to use as ``maya.cmds``.
        func_name: Name of the callable to invoke (default: ``"main"``).
        **kwargs: Keyword arguments forwarded to the callable.

    Returns:
        Whatever the skill function returns (typically an ActionResultModel dict).
    """
    _LOAD_COUNTER[0] += 1
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    fpath = SKILLS_ROOT / rel_path
    mod_name = "skill_lac_{}_{}".format(fpath.stem, _LOAD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(mod_name, str(fpath))
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


def load_and_call_with_mel(
    rel_path: str,
    mock_cmds: MagicMock,
    mock_mel: Optional[MagicMock] = None,
    func_name: str = "main",
    **kwargs,
) -> Any:
    """Load a skill script and call a function with maya.cmds AND maya.mel mocked.

    Extends :func:`load_and_call` for scripts that also ``import maya.mel as mel``
    inside the function body.

    Args:
        rel_path: Path relative to the ``skills/`` root.
        mock_cmds: The :class:`~unittest.mock.MagicMock` to use as ``maya.cmds``.
        mock_mel: Optional mock for ``maya.mel``; a new :class:`MagicMock` is
            created if not provided.
        func_name: Name of the callable to invoke (default: ``"main"``).
        **kwargs: Keyword arguments forwarded to the callable.

    Returns:
        Whatever the skill function returns (typically an ActionResultModel dict).
    """
    _LOAD_COUNTER[0] += 1
    if mock_mel is None:
        mock_mel = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_maya.mel = mock_mel

    fpath = SKILLS_ROOT / rel_path
    mod_name = "skill_lacm_{}_{}".format(fpath.stem, _LOAD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(mod_name, str(fpath))
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.mel": mock_mel,
        },
    ):
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ──────────────────────────────────────────────────────────────────────────
# Multi-Instance Gateway Testing Fixtures
# ──────────────────────────────────────────────────────────────────────────


class GatewayTestClient:
    """HTTP client for gateway interaction and assertions."""

    def __init__(self, gateway_url: str, timeout: int = 10):
        """Initialize gateway test client."""
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def health_check(self) -> bool:
        """Check if gateway is healthy."""
        try:
            resp = self.session.get(f"{self.gateway_url}/health", timeout=self.timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def list_instances(self, dcc_type: str = "maya"):
        """Get list of registered instances."""
        try:
            # Try to call gateway tool
            resp = self.session.post(
                f"{self.gateway_url}/mcp/tools/call",
                json={"name": "list_instances", "arguments": {"dcc_type": dcc_type}},
                timeout=self.timeout,
            )
            data = resp.json()
            if isinstance(data, dict) and "instances" in data:
                return data["instances"]
            elif isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def find_gateway_instance(self) -> Optional[str]:
        """Find which instance is the current gateway."""
        try:
            resp = self.session.post(
                f"{self.gateway_url}/mcp/tools/call",
                json={"name": "get_gateway_info", "arguments": {}},
                timeout=self.timeout,
            )
            data = resp.json()
            if isinstance(data, dict):
                return data.get("gateway_instance_id")
        except Exception:
            pass
        return None

    def wait_for_gateway(self, max_retries: int = 30, retry_delay: float = 1.0) -> bool:
        """Wait for gateway to become available."""
        for _ in range(max_retries):
            if self.health_check():
                return True
            time.sleep(retry_delay)
        return False

    def wait_for_instance_count(
        self,
        expected_count: int,
        dcc_type: str = "maya",
        max_retries: int = 20,
        retry_delay: float = 0.5,
    ) -> bool:
        """Wait for expected number of instances to register."""
        for _ in range(max_retries):
            instances = self.list_instances(dcc_type)
            if len(instances) >= expected_count:
                return True
            time.sleep(retry_delay)
        return False


@pytest.fixture
def gateway_client() -> GatewayTestClient:
    """Fixture providing a gateway test client."""
    return GatewayTestClient("http://127.0.0.1:9765")


@pytest.fixture
def temp_registry_dir(tmp_path):
    """Fixture providing a temporary directory for FileRegistry."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    return str(registry_dir)


@pytest.fixture
def maya_instance_manager(temp_registry_dir):
    """Fixture providing a MayaInstanceManager."""
    try:
        from fixtures.maya_instances import MayaInstanceManager, check_mayapy_available
    except ImportError:
        pytest.skip("MayaInstanceManager not available")

    # Skip tests if mayapy is not available
    if not check_mayapy_available():
        pytest.skip("mayapy not available in test environment")

    manager = MayaInstanceManager(gateway_port=9765, registry_dir=temp_registry_dir)
    yield manager
    manager.cleanup()
