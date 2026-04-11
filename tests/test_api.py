"""Unit tests for dcc_mcp_maya.api — skill authoring helpers."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya.api import (
    is_maya_available,
    maya_error,
    maya_from_exception,
    maya_success,
    with_maya,
)


# ---------------------------------------------------------------------------
# maya_success
# ---------------------------------------------------------------------------


def test_maya_success_basic():
    result = maya_success("done")
    assert result["success"] is True
    assert result["message"] == "done"
    assert result["error"] is None


def test_maya_success_with_context():
    result = maya_success("created", object_name="pSphere1", radius=2.0)
    assert result["success"] is True
    assert result["context"]["object_name"] == "pSphere1"
    assert result["context"]["radius"] == 2.0


def test_maya_success_with_prompt():
    result = maya_success("ok", prompt="use delete to undo")
    assert result["prompt"] == "use delete to undo"


# ---------------------------------------------------------------------------
# maya_error
# ---------------------------------------------------------------------------


def test_maya_error_basic():
    result = maya_error("oops", "something broke")
    assert result["success"] is False
    assert result["message"] == "oops"
    assert result["error"] == "something broke"


def test_maya_error_with_solutions():
    solutions = ["check name", "use list_objects"]
    result = maya_error("not found", "node missing", possible_solutions=solutions)
    assert result["context"]["possible_solutions"] == solutions


def test_maya_error_with_context():
    result = maya_error("bad input", "invalid radius", radius=-1.0)
    assert result["context"]["radius"] == -1.0


# ---------------------------------------------------------------------------
# maya_from_exception
# ---------------------------------------------------------------------------


def test_maya_from_exception_captures_message():
    exc = ValueError("bad value")
    result = maya_from_exception(exc, "operation failed")
    assert result["success"] is False
    assert result["message"] == "operation failed"
    assert "bad value" in result["error"]


def test_maya_from_exception_default_message():
    exc = RuntimeError("crash")
    result = maya_from_exception(exc)
    assert result["message"] == "Maya operation failed"


def test_maya_from_exception_with_context():
    exc = Exception("err")
    result = maya_from_exception(exc, "failed", node="pCube1")
    assert result["context"]["node"] == "pCube1"


def test_maya_from_exception_with_solutions():
    exc = Exception("err")
    result = maya_from_exception(exc, possible_solutions=["try X", "try Y"])
    assert result["context"]["possible_solutions"] == ["try X", "try Y"]


# ---------------------------------------------------------------------------
# is_maya_available
# ---------------------------------------------------------------------------


def test_is_maya_available_false_without_maya():
    # In CI / non-Maya environment, should be False
    result = is_maya_available()
    assert isinstance(result, bool)


def test_is_maya_available_true_when_maya_importable():
    mock_cmds = MagicMock()
    with patch.dict("sys.modules", {"maya": MagicMock(), "maya.cmds": mock_cmds}):
        assert is_maya_available() is True


# ---------------------------------------------------------------------------
# with_maya decorator
# ---------------------------------------------------------------------------


def test_with_maya_import_error():
    @with_maya
    def broken() -> dict:
        import maya.cmds  # noqa: F401 - intentional ImportError

        return maya_success("never")

    result = broken()
    assert result["success"] is False
    assert result["message"] == "Maya not available"
    assert "possible_solutions" in result["context"]


def test_with_maya_general_exception():
    @with_maya
    def explodes() -> dict:
        raise RuntimeError("boom")

    result = explodes()
    assert result["success"] is False
    assert "explodes" in result["message"]
    assert "boom" in result["error"]


def test_with_maya_success_path():
    """with_maya passes through success results from the wrapped function."""

    @with_maya
    def returns_success() -> dict:
        # Simulate a successful Maya operation without actually importing maya.cmds
        return maya_success("created", object_name="pSphere1")

    result = returns_success()
    assert result["success"] is True
    assert result["context"]["object_name"] == "pSphere1"


def test_with_maya_preserves_function_name():
    @with_maya
    def my_special_function() -> dict:
        raise RuntimeError("err")

    assert my_special_function.__name__ == "my_special_function"


def test_with_maya_passes_kwargs():
    mock_cmds = MagicMock()
    mock_cmds.polySphere.return_value = ["pSphere1", "poly1"]

    @with_maya
    def create(radius: float = 1.0) -> dict:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.polySphere(radius=radius)
        return maya_success("done", radius=radius)

    with patch.dict("sys.modules", {"maya": MagicMock(), "maya.cmds": mock_cmds}):
        result = create(radius=3.5)

    assert result["context"]["radius"] == 3.5


# ---------------------------------------------------------------------------
# Public API re-export via dcc_mcp_maya
# ---------------------------------------------------------------------------


def test_public_api_reexport():
    """All helpers must be importable directly from dcc_mcp_maya."""
    import dcc_mcp_maya

    for name in [
        "maya_success",
        "maya_error",
        "maya_from_exception",
        "is_maya_available",
        "with_maya",
        "get_cmds",
        "require_cmds",
    ]:
        assert hasattr(dcc_mcp_maya, name), f"dcc_mcp_maya.{name} missing"
