"""Round 46 tests: InputValidator integration, ScriptResult structured output,
SceneStatistics structured output.

Covers:
- dcc_mcp_maya.api.make_input_validator
- dcc_mcp_maya.api.validate_input
- execute_mel: InputValidator field validation + ScriptResult context key
- execute_python: InputValidator + injection guard + ScriptResult context key
- get_scene_statistics: SceneStatistics-compatible dict in context.scene_statistics
"""

# Import built-in modules
import importlib
import json
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_module(rel_path):
    """Load a skill script module dynamically with mocked Maya."""
    import importlib.util
    from pathlib import Path

    skills_base = (
        Path(__file__).parent.parent
        / "src"
        / "dcc_mcp_maya"
        / "skills"
    )
    full_path = skills_base / rel_path
    spec = importlib.util.spec_from_file_location("_skill_mod", str(full_path))
    mod = importlib.util.module_from_spec(spec)
    mock_maya = MagicMock()
    mock_cmds = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_mel = MagicMock()
    mock_maya.mel = mock_mel
    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
        spec.loader.exec_module(mod)
    return mod, mock_cmds, mock_mel


def _call(mod, fn_name, mock_cmds, mock_mel=None, **kwargs):
    """Call mod.<fn_name>(**kwargs) with maya mocks active."""
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    if mock_mel:
        mock_maya.mel = mock_mel
    mocks = {"maya": mock_maya, "maya.cmds": mock_cmds}
    if mock_mel:
        mocks["maya.mel"] = mock_mel
    with patch.dict(sys.modules, mocks):
        fn = getattr(mod, fn_name)
        return fn(**kwargs)


# ---------------------------------------------------------------------------
# TestMakeInputValidator
# ---------------------------------------------------------------------------


class TestMakeInputValidator:
    """Tests for dcc_mcp_maya.api.make_input_validator."""

    def test_creates_validator_instance(self):
        from dcc_mcp_maya.api import make_input_validator
        from dcc_mcp_core import InputValidator

        v = make_input_validator(string_fields={"code": (1, 100)})
        assert isinstance(v, InputValidator)

    def test_string_field_required(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(string_fields={"code": (1, 100)})
        ok, err = validate_input(v, {})
        assert ok is False
        assert "code" in (err or "")

    def test_string_field_valid(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(string_fields={"code": (1, 100)})
        ok, err = validate_input(v, {"code": "hello"})
        assert ok is True
        assert err is None

    def test_number_field_required(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(number_fields={"width": (1, 8192)})
        ok, err = validate_input(v, {})
        assert ok is False
        assert "width" in (err or "")

    def test_number_field_out_of_range(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(number_fields={"width": (1, 8192)})
        ok, err = validate_input(v, {"width": 99999})
        assert ok is False
        assert "width" in (err or "")

    def test_number_field_valid(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(number_fields={"width": (1, 8192)})
        ok, err = validate_input(v, {"width": 1920})
        assert ok is True
        assert err is None

    def test_no_fields_always_valid(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator()
        ok, err = validate_input(v, {})
        assert ok is True

    def test_reexport_from_package(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "make_input_validator")
        assert hasattr(dcc_mcp_maya, "validate_input")

    def test_in_all(self):
        import dcc_mcp_maya

        assert "make_input_validator" in dcc_mcp_maya.__all__
        assert "validate_input" in dcc_mcp_maya.__all__


# ---------------------------------------------------------------------------
# TestValidateInput
# ---------------------------------------------------------------------------


class TestValidateInput:
    """Tests for dcc_mcp_maya.api.validate_input."""

    def test_returns_tuple(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(string_fields={"s": (1, 10)})
        result = validate_input(v, {"s": "hi"})
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_graceful_on_non_serializable(self):
        """Non-serialisable params should not raise; returns (True, None) as fallback."""
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(string_fields={"s": (1, 10)})
        # Passing an un-serialisable object
        ok, err = validate_input(v, {"s": object()})
        # Must not raise; result is a tuple
        assert isinstance(ok, bool)

    def test_empty_string_fails_min_length(self):
        from dcc_mcp_maya.api import make_input_validator, validate_input

        v = make_input_validator(string_fields={"code": (1, 1000)})
        ok, err = validate_input(v, {"code": ""})
        assert ok is False


# ---------------------------------------------------------------------------
# TestExecuteMelInputValidator
# ---------------------------------------------------------------------------


class TestExecuteMelInputValidator:
    """execute_mel now uses InputValidator for field validation."""

    def _setup(self):
        mod, mock_cmds, mock_mel = _load_module("maya-scripting/scripts/execute_mel.py")
        return mod, mock_cmds, mock_mel

    def test_missing_script_param_returns_error(self):
        mod, mock_cmds, mock_mel = self._setup()
        # validator detects missing 'script'
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="")
        assert result["success"] is False

    def test_valid_script_succeeds(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = "hello"
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="print 1;")
        assert result["success"] is True
        assert result["context"]["output"] == "hello"

    def test_script_result_key_present(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = "42"
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="sphere;")
        assert "script_result" in result["context"]

    def test_script_result_has_success_flag(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = "ok"
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="sphere;")
        sr = result["context"]["script_result"]
        assert sr["success"] is True

    def test_script_result_has_output(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = "pSphere1"
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="sphere;")
        sr = result["context"]["script_result"]
        assert sr["output"] == "pSphere1"

    def test_execution_time_ms_present(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = None
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="print 1;")
        assert "execution_time_ms" in result["context"]
        assert isinstance(result["context"]["execution_time_ms"], float)

    def test_mel_exception_returns_error(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.side_effect = RuntimeError("MEL error")
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="bad;")
        assert result["success"] is False

    def test_none_return_value_gives_empty_output(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = None
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="ls;")
        assert result["context"]["output"] == ""

    def test_script_key_preserved(self):
        mod, mock_cmds, mock_mel = self._setup()
        mock_mel.eval.return_value = "x"
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="sphere;")
        assert result["context"]["script"] == "sphere;"

    def test_whitespace_only_script_returns_error(self):
        mod, mock_cmds, mock_mel = self._setup()
        result = _call(mod, "execute_mel", mock_cmds, mock_mel, script="   ")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestExecutePythonInjectionGuard
# ---------------------------------------------------------------------------


class TestExecutePythonInjectionGuard:
    """execute_python injection guard catches dangerous patterns."""

    def _setup(self):
        mod, mock_cmds, mock_mel = _load_module("maya-scripting/scripts/execute_python.py")
        return mod, mock_cmds

    def test_os_system_blocked(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="os.system('id')")
        assert result["success"] is False
        assert "os.system" in result["error"] or "injection" in result["message"].lower()

    def test_subprocess_blocked(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="import subprocess; subprocess.run(['ls'])")
        assert result["success"] is False

    def test_import_blocked(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="__import__('os').system('id')")
        assert result["success"] is False

    def test_safe_code_executes(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="result = 1 + 1")
        assert result["success"] is True
        assert result["context"]["output"] == "2"

    def test_empty_code_returns_error(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="")
        assert result["success"] is False

    def test_whitespace_code_returns_error(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="   ")
        assert result["success"] is False

    def test_script_result_key_present(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="x = 1")
        assert "script_result" in result["context"]

    def test_script_result_success_flag(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="result = 'done'")
        sr = result["context"]["script_result"]
        assert sr["success"] is True

    def test_script_result_output_matches(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="result = 'hello world'")
        sr = result["context"]["script_result"]
        assert sr["output"] == "hello world"

    def test_execution_time_ms_present(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="x = 1")
        assert "execution_time_ms" in result["context"]
        assert isinstance(result["context"]["execution_time_ms"], float)

    def test_capture_output_true(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="print('captured')", capture_output=True)
        assert result["success"] is True
        assert "captured" in result["context"]["output"]

    def test_exception_in_code_returns_error(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="raise ValueError('boom')")
        assert result["success"] is False

    def test_open_call_blocked(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="open('/etc/passwd')")
        assert result["success"] is False

    def test_eval_call_blocked(self):
        mod, mock_cmds = self._setup()
        result = _call(mod, "execute_python", mock_cmds, code="eval('1+1')")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestGetSceneStatisticsStructured
# ---------------------------------------------------------------------------


class TestGetSceneStatisticsStructured:
    """get_scene_statistics returns SceneStatistics-compatible dict."""

    def _make_mock_cmds(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.side_effect = lambda **kwargs: (
            ["pSphere1", "pCube1", "defaultLight"] if not kwargs else
            ["pSphere1", "pCube1"] if kwargs.get("type") in ("transform", "mesh") else
            ["shadingGroup1"] if kwargs.get("type") == "shadingEngine" else
            ["camera1"] if kwargs.get("type") == "camera" else
            ["fileNode1"] if kwargs.get("type") == "file" else
            ["light1"] if kwargs.get("lights") else
            []
        )
        mock_cmds.polyEvaluate.side_effect = lambda mesh, **kw: (
            100 if kw.get("vertex") else 50 if kw.get("face") else 0
        )
        mock_cmds.file.return_value = "/tmp/test.ma"
        mock_cmds.memory.return_value = 1024 * 100  # 100 MB in KB
        return mock_cmds

    def _setup(self):
        mod, mock_cmds, mock_mel = _load_module("maya-utility/scripts/get_scene_statistics.py")
        return mod, mock_cmds

    def test_scene_statistics_key_present(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        assert result["success"] is True
        assert "scene_statistics" in result["context"]

    def test_scene_statistics_has_object_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "object_count" in ss
        assert isinstance(ss["object_count"], int)

    def test_scene_statistics_has_polygon_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "polygon_count" in ss

    def test_scene_statistics_has_vertex_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "vertex_count" in ss

    def test_scene_statistics_has_material_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "material_count" in ss

    def test_scene_statistics_has_texture_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "texture_count" in ss

    def test_scene_statistics_has_light_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "light_count" in ss

    def test_scene_statistics_has_camera_count(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ss = result["context"]["scene_statistics"]
        assert "camera_count" in ss

    def test_legacy_keys_still_present(self):
        """Backward compatibility: old keys must remain."""
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        ctx = result["context"]
        for key in ("total_nodes", "transform_count", "mesh_count",
                    "poly_vertex_count", "poly_face_count", "scene_file"):
            assert key in ctx, "Missing legacy key: {}".format(key)

    def test_include_memory_false(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2, include_memory=False)
        assert result["success"] is True
        assert "memory_mb" not in result["context"]

    def test_scene_file_in_context(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        assert result["context"]["scene_file"] == "/tmp/test.ma"

    def test_prompt_present(self):
        mod, mock_cmds = self._setup()
        mock_cmds2 = self._make_mock_cmds()
        result = _call(mod, "get_scene_statistics", mock_cmds2)
        assert result.get("prompt") or "prompt" in result.get("context", {})


# ---------------------------------------------------------------------------
# TestStructuralChecks
# ---------------------------------------------------------------------------


class TestStructuralChecks:
    """Structural checks: imports, file existence, API shape."""

    def test_execute_mel_imports_make_input_validator(self):
        from pathlib import Path

        script = (
            Path(__file__).parent.parent
            / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "scripts" / "execute_mel.py"
        )
        content = script.read_text(encoding="utf-8")
        assert "make_input_validator" in content or "InputValidator" in content

    def test_execute_python_imports_make_input_validator(self):
        from pathlib import Path

        script = (
            Path(__file__).parent.parent
            / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "scripts" / "execute_python.py"
        )
        content = script.read_text(encoding="utf-8")
        assert "make_input_validator" in content or "InputValidator" in content

    def test_execute_python_has_injection_patterns(self):
        from pathlib import Path

        script = (
            Path(__file__).parent.parent
            / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "scripts" / "execute_python.py"
        )
        content = script.read_text(encoding="utf-8")
        assert "_DANGEROUS_PATTERNS" in content or "os.system" in content

    def test_get_scene_statistics_has_scene_statistics_key(self):
        from pathlib import Path

        script = (
            Path(__file__).parent.parent
            / "src" / "dcc_mcp_maya" / "skills" / "maya-utility" / "scripts" / "get_scene_statistics.py"
        )
        content = script.read_text(encoding="utf-8")
        assert "scene_statistics" in content

    def test_api_module_has_make_input_validator(self):
        from dcc_mcp_maya import api

        assert hasattr(api, "make_input_validator")
        assert hasattr(api, "validate_input")

    def test_execute_mel_has_script_result_key(self):
        from pathlib import Path

        script = (
            Path(__file__).parent.parent
            / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "scripts" / "execute_mel.py"
        )
        content = script.read_text(encoding="utf-8")
        assert "script_result" in content

    def test_execute_python_has_script_result_key(self):
        from pathlib import Path

        script = (
            Path(__file__).parent.parent
            / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "scripts" / "execute_python.py"
        )
        content = script.read_text(encoding="utf-8")
        assert "script_result" in content
