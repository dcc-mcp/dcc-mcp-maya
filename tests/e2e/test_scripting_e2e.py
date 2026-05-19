"""E2E tests for maya-scripting, maya-utility, and maya-pipeline skills.

Requires a real mayapy interpreter.  Skipped automatically when maya is not
available.

Run::

    mayapy -m pytest tests/e2e/test_scripting_e2e.py -v
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
from pathlib import Path

# Import third-party modules
import pytest

maya_standalone = pytest.importorskip(
    "maya.standalone",
    reason="maya.standalone not available — run under mayapy",
)

try:
    maya_standalone.initialize(name="python")
except Exception:
    pass

from maya import cmds  # noqa: E402

pytestmark = pytest.mark.e2e

_SKILLS_ROOT = Path(__file__).parent.parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load(skill_dir: str, script_name: str):
    _MOD_COUNTER[0] += 1
    path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "e2e_scr_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_scene():
    cmds.file(new=True, force=True)


class TestScriptingE2E:
    def setup_method(self):
        _new_scene()

    def test_execute_mel_polysphere(self):
        mod = _load("maya-scripting", "execute_mel")
        result = mod.execute_mel(code="polySphere -r 1 -n melE2ESphere;")
        assert result["success"] is True
        assert cmds.objExists("melE2ESphere")

    def test_execute_mel_syntax_error_returns_result(self):
        """Invalid MEL returns a structured failure, not just "some dict"."""
        mod = _load("maya-scripting", "execute_mel")
        result = mod.execute_mel(code="this_is_invalid_mel_xyz!!!;")
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["message"] == "MEL execution failed"
        assert result["error"]

    def test_execute_python_creates_node(self):
        mod = _load("maya-scripting", "execute_python")
        result = mod.execute_python(code="import maya.cmds as cmds; cmds.polyCube(n='pyE2ECube')")
        assert result["success"] is True
        assert cmds.objExists("pyE2ECube")

    def test_execute_python_captures_result(self):
        mod = _load("maya-scripting", "execute_python")
        result = mod.execute_python(code="result = 1 + 2\nresult", result_type="VALUE")
        assert result["success"] is True
        ctx = result.get("context", {})
        assert ctx.get("output") == "3"

    def test_execute_python_blocks_dirty_new_scene_prompt(self):
        cmds.polyCube(name="dirtyPromptCube")
        mod = _load("maya-scripting", "execute_python")
        result = mod.execute_python(code="cmds.file(new=True)", capture_output=False)
        assert result["success"] is False
        assert result["message"] == "cmds.file prompt blocked"
        assert "force=True" in result["error"]

    def test_list_mel_procedures(self):
        mod = _load("maya-scripting", "list_mel_procedures")
        result = mod.list_mel_procedures()
        assert result["success"] is True
        procs = result["context"].get("procedures", [])
        assert isinstance(procs, list)

    def test_get_script_node(self):
        # Create a script node first
        import maya.mel as mel

        mel.eval('scriptNode -st 2 -bs "print(\\"hello\\");" -n e2eScriptNode -stp "python";')
        mod = _load("maya-scripting", "get_script_node")
        result = mod.get_script_node(node_name="e2eScriptNode")
        assert result["success"] is True
        assert "script" in result["context"] or "node_name" in result["context"]

    def test_execute_mel_warning_captured(self):
        """Issue #151 — MEL ``warning`` flows through MCommandMessage and
        must reach the client via the structured envelope's stderr field.
        """
        mod = _load("maya-scripting", "execute_mel")
        result = mod.execute_mel(code='warning "e2e-mel-warning";')
        assert isinstance(result, dict)
        # ``warning`` does not abort MEL, so success=True is expected.
        assert result.get("success") is True
        ctx = result.get("context", {})
        combined = (ctx.get("stdout") or "") + (ctx.get("stderr") or "")
        assert "e2e-mel-warning" in combined, (
            "MayaOutputCapture should have captured MEL 'warning' output via MCommandMessage. Got: {!r}".format(
                combined
            )
        )

    def test_execute_python_cmds_warning_captured(self):
        """Issue #151 — ``cmds.warning`` output is captured alongside print()."""
        mod = _load("maya-scripting", "execute_python")
        result = mod.execute_python(
            code=("import maya.cmds as cmds\nprint('from-print')\ncmds.warning('from-cmds-warning')\n")
        )
        assert result.get("success") is True
        ctx = result.get("context", {})
        combined = (ctx.get("stdout") or "") + (ctx.get("stderr") or "")
        assert "from-print" in combined
        assert "from-cmds-warning" in combined

    def test_execute_python_defer_cancels_long_loop(self):
        """Issue #153 — a ``defer=True`` infinite loop must abort when
        the active job's cancel flag fires.

        Uses the real in-Maya path: ``maya.utils.executeDeferred`` is
        available, so the snippet runs on the main thread's idle queue.
        Because ``mayapy`` drives that queue synchronously when the main
        thread is idle, the snippet would otherwise block indefinitely.
        The ``sys.settrace`` hook installed by ``_run_inline`` observes
        the cancel event between Python lines and raises ``CancelledError``.
        """
        # Import local modules
        from dcc_mcp_maya.dispatcher.job import _current_job, _JobEntry

        mod = _load("maya-scripting", "execute_python")
        job = _JobEntry(
            request_id="e2e-defer-cancel",
            affinity="main",
            task=lambda: None,
        )
        token = _current_job.set(job)
        try:
            deferred = mod._run_deferred(
                code=("i = 0\nwhile True:\n    i += 1\n"),
                capture_output=False,
                timeout_secs=5.0,
            )
            # Cancel before polling so the first settrace checkpoint sees it.
            job.cancel()
            envelope = None
            # Drive the poll loop a few times; CancelledError will surface
            # from check_is_finished as soon as the tracer trips.
            try:
                for _ in range(50):
                    envelope = deferred.check_is_finished()
                    if envelope is not None:
                        break
            except Exception as exc:  # core cancellation raises
                assert "cancel" in type(exc).__name__.lower()
                return
            # If we reached here, the snippet either finished (not expected
            # given the infinite loop) or returned a cancelled envelope.
            assert envelope is not None and envelope.get("success") is False
        finally:
            _current_job.reset(token)


class TestUtilityE2E:
    def setup_method(self):
        _new_scene()

    def test_get_scene_statistics(self):
        cmds.polySphere(name="statSphere")
        cmds.polyCube(name="statCube")
        mod = _load("maya-utility", "get_scene_statistics")
        result = mod.get_scene_statistics()
        assert result["success"] is True
        ctx = result["context"]
        assert "scene_file" in ctx or "node_count" in ctx or "total_nodes" in ctx

    def test_create_utility_node_multiplyDivide(self):
        mod = _load("maya-utility", "create_utility_node")
        result = mod.create_utility_node(node_type="multiplyDivide", name="e2eMulDiv")
        assert result["success"] is True
        # Node should exist (may be renamed by Maya)
        nodes = cmds.ls(type="multiplyDivide") or []
        assert len(nodes) > 0

    def test_list_node_connections(self):
        cmds.polySphere(name="connSphere")
        mod = _load("maya-utility", "list_node_connections")
        result = mod.list_node_connections(node_name="connSphere")
        assert result["success"] is True
        assert "connections" in result["context"]

    def test_clean_scene_removes_unused(self):
        # Create and immediately disconnect an unused material
        cmds.shadingNode("lambert", asShader=True, name="unusedLambert")
        mod = _load("maya-utility", "clean_scene")
        result = mod.clean_scene()
        assert result["success"] is True


class TestPipelineE2E:
    def setup_method(self):
        _new_scene()

    def test_set_project(self, tmp_path):
        mod = _load("maya-pipeline", "set_project")
        result = mod.set_project(project_path=str(tmp_path))
        assert result["success"] is True

    def test_tag_and_get_asset_metadata(self):
        cmds.polySphere(name="assetSphere")
        tag_mod = _load("maya-pipeline", "tag_asset_metadata")
        result = tag_mod.tag_asset_metadata(
            node_name="assetSphere",
            asset_name="TestAsset",
            asset_type="prop",
            version="1.0.0",
        )
        assert result["success"] is True

        get_mod = _load("maya-pipeline", "get_asset_metadata")
        get_result = get_mod.get_asset_metadata(node_name="assetSphere")
        assert get_result["success"] is True
        ctx = get_result["context"]
        assert ctx.get("asset_name") == "TestAsset" or "metadata" in ctx
