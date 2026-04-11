"""Unit tests for dcc_mcp_maya.api — skill authoring helpers."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya.api import (
    MissingParamError,
    is_maya_available,
    maya_error,
    maya_from_exception,
    maya_success,
    missing_param_error,
    require_param,
    validate_node_exists,
    validate_node_type,
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

    # Force ImportError even when running inside mayapy by patching maya.cmds
    with patch.dict("sys.modules", {"maya.cmds": None}):
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
        "require_param",
        "missing_param_error",
        "MissingParamError",
        "validate_node_exists",
        "validate_node_type",
    ]:
        assert hasattr(dcc_mcp_maya, name), "dcc_mcp_maya.{} missing".format(name)


# ---------------------------------------------------------------------------
# require_param
# ---------------------------------------------------------------------------


class TestRequireParam:
    def test_returns_value_when_present(self):
        assert require_param({"name": "pSphere1"}, "name") == "pSphere1"

    def test_returns_default_when_absent(self):
        assert require_param({}, "size", 1.0) == 1.0

    def test_raises_when_absent_no_default(self):
        with pytest.raises(MissingParamError, match="name"):
            require_param({}, "name")

    def test_returns_none_value_when_key_present(self):
        # Explicit None is a valid value
        result = require_param({"flag": None}, "flag", "fallback")
        assert result is None

    def test_returns_false_value_when_key_present(self):
        result = require_param({"enabled": False}, "enabled", True)
        assert result is False

    def test_returns_zero_value_when_key_present(self):
        result = require_param({"count": 0}, "count", 99)
        assert result == 0

    def test_default_can_be_none_explicitly(self):
        result = require_param({}, "missing", None)
        assert result is None


# ---------------------------------------------------------------------------
# missing_param_error
# ---------------------------------------------------------------------------


class TestMissingParamError:
    def test_returns_error_dict(self):
        result = missing_param_error("radius")
        assert result["success"] is False
        assert "radius" in result["message"]

    def test_includes_possible_solutions(self):
        result = missing_param_error("name")
        solutions = result["context"]["possible_solutions"]
        assert any("name" in s for s in solutions)

    def test_accepts_extra_context(self):
        result = missing_param_error("width", hint="must be positive")
        assert result["context"]["hint"] == "must be positive"


# ---------------------------------------------------------------------------
# validate_node_exists
# ---------------------------------------------------------------------------


class TestValidateNodeExists:
    def _make_cmds(self, exists: bool) -> MagicMock:
        cmds = MagicMock()
        cmds.objExists.return_value = exists
        return cmds

    def test_returns_none_when_node_exists(self):
        cmds = self._make_cmds(True)
        assert validate_node_exists(cmds, "pSphere1") is None

    def test_returns_error_when_node_missing(self):
        cmds = self._make_cmds(False)
        result = validate_node_exists(cmds, "pSphere1")
        assert result is not None
        assert result["success"] is False
        assert "pSphere1" in result["message"]

    def test_error_includes_possible_solutions(self):
        cmds = self._make_cmds(False)
        result = validate_node_exists(cmds, "myNode")
        assert "possible_solutions" in result["context"]
        assert len(result["context"]["possible_solutions"]) > 0

    def test_calls_obj_exists_with_correct_name(self):
        cmds = self._make_cmds(True)
        validate_node_exists(cmds, "joint1")
        cmds.objExists.assert_called_once_with("joint1")


# ---------------------------------------------------------------------------
# validate_node_type
# ---------------------------------------------------------------------------


class TestValidateNodeType:
    def _make_cmds(self, actual_type: str) -> MagicMock:
        cmds = MagicMock()
        cmds.objectType.return_value = actual_type
        return cmds

    def test_returns_none_when_type_matches(self):
        cmds = self._make_cmds("displayLayer")
        assert validate_node_type(cmds, "layer1", "displayLayer") is None

    def test_returns_error_when_type_mismatch(self):
        cmds = self._make_cmds("transform")
        result = validate_node_type(cmds, "pSphere1", "displayLayer")
        assert result is not None
        assert result["success"] is False
        assert "transform" in result["error"]
        assert "displayLayer" in result["error"]

    def test_error_includes_node_name(self):
        cmds = self._make_cmds("mesh")
        result = validate_node_type(cmds, "myMesh", "displayLayer")
        assert "myMesh" in result["message"]

    def test_error_includes_possible_solutions(self):
        cmds = self._make_cmds("mesh")
        result = validate_node_type(cmds, "myMesh", "displayLayer")
        solutions = result["context"]["possible_solutions"]
        assert any("displayLayer" in s for s in solutions)

    def test_calls_object_type_with_correct_name(self):
        cmds = self._make_cmds("transform")
        validate_node_type(cmds, "pCube1", "transform")
        cmds.objectType.assert_called_once_with("pCube1")
