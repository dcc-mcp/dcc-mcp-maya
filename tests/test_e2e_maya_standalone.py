"""End-to-end tests that require a real Maya standalone interpreter.

These tests are skipped unless ``maya.standalone`` can be imported and
initialised.  In CI they run inside the ``tahv/mayapy`` Docker image via
the ``e2e.yml`` workflow.

Run locally::

    mayapy -m pytest tests/test_e2e_maya_standalone.py -v -m e2e

Mark
----
All tests in this module carry the ``e2e`` pytest marker so they can be
filtered in or out with ``-m e2e`` / ``-m "not e2e"``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Guard: skip entire module when Maya is not available
# ---------------------------------------------------------------------------
maya_standalone = pytest.importorskip(
    "maya.standalone",
    reason="maya.standalone not available — run under mayapy",
)

# Initialise once per process (idempotent in Maya standalone)
try:
    maya_standalone.initialize(name="python")
except Exception:
    pass  # Already initialized

from maya import cmds  # noqa: E402 — must come after standalone.initialize()

pytestmark = pytest.mark.e2e

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _new_scene():
    """Open a fresh empty scene."""
    cmds.file(new=True, force=True)


def _load_script(skill_name: str, script_name: str):
    """Import a skill script module and return it."""
    script_path = _SKILLS_ROOT / skill_name / "scripts" / f"{script_name}.py"
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


class TestServerLifecycle:
    """MayaMcpServer starts, reports a valid URL, and stops cleanly."""

    def test_start_and_stop(self):
        from dcc_mcp_maya.server import MayaMcpServer

        server = MayaMcpServer(port=0, enable_main_thread_executor=False)
        server.register_builtin_actions()
        handle = server.start()

        assert handle is not None
        url = handle.mcp_url()
        assert url.startswith("http://")
        assert "/mcp" in url

        server.stop()
        assert not server.is_running

    def test_singleton_start_server(self):
        from dcc_mcp_maya import start_server, stop_server

        handle = start_server(port=0)
        assert handle is not None
        stop_server()

    def test_skills_discovered(self):
        """Skills are discovered via SKILL.md and registered as MCP tools."""
        from dcc_mcp_maya.server import MayaMcpServer

        server = MayaMcpServer(port=0, enable_main_thread_executor=False)
        server.register_builtin_actions()
        actions = server.registry.list_actions()
        names = {a["name"] for a in actions}
        # Skills SOP: action names follow {skill_name}__{script_stem}
        assert "maya_primitives__create_sphere" in names
        assert "maya_scripting__execute_mel" in names
        assert "maya_scene__get_session_info" in names
        assert "maya_animation__set_keyframe" in names
        assert len(actions) >= 100


# ---------------------------------------------------------------------------
# Scene actions (real Maya cmds)
# ---------------------------------------------------------------------------


class TestSceneActions:
    """Scene skill scripts execute correctly inside Maya standalone."""

    def setup_method(self):
        _new_scene()

    def test_new_scene(self):
        mod = _load_script("maya-scene", "new_scene")
        result = mod.new_scene(force=True)
        assert result["success"] is True

    def test_list_objects_empty_scene(self):
        mod = _load_script("maya-scene", "list_objects")
        result = mod.list_objects()
        assert result["success"] is True
        assert "objects" in result["context"]

    def test_get_session_info(self):
        mod = _load_script("maya-scene", "get_session_info")
        result = mod.get_session_info()
        assert result["success"] is True
        ctx = result["context"]
        assert "maya_version" in ctx
        assert "python_version" in ctx

    def test_save_scene_to_temp(self, tmp_path):
        mod = _load_script("maya-scene", "save_scene")
        out = tmp_path / "test_save.ma"
        result = mod.save_scene(file_path=str(out), file_type="mayaAscii")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Primitives (real Maya cmds)
# ---------------------------------------------------------------------------


class TestPrimitiveActions:
    """Primitive creation skill scripts produce real Maya nodes."""

    def setup_method(self):
        _new_scene()

    def test_create_sphere(self):
        mod = _load_script("maya-primitives", "create_sphere")
        result = mod.create_sphere(radius=2.0, name="testSphere")
        assert result["success"] is True
        assert cmds.objExists("testSphere") or cmds.objExists("testSphereShape")

    def test_create_cube(self):
        mod = _load_script("maya-primitives", "create_cube")
        result = mod.create_cube(name="testCube")
        assert result["success"] is True

    def test_set_and_get_transform(self):
        create_mod = _load_script("maya-primitives", "create_sphere")
        set_mod = _load_script("maya-primitives", "set_transform")
        get_mod = _load_script("maya-primitives", "get_transform")

        create_mod.create_sphere(name="xformSphere")
        set_mod.set_transform(object_name="xformSphere", translate=[1.0, 2.0, 3.0])
        result = get_mod.get_transform(object_name="xformSphere")
        assert result["success"] is True
        tx = result["context"]["translate"]
        assert abs(tx[0] - 1.0) < 0.001

    def test_delete_objects(self):
        create_mod = _load_script("maya-primitives", "create_cube")
        delete_mod = _load_script("maya-primitives", "delete_objects")

        create_mod.create_cube(name="toDelete")
        result = delete_mod.delete_objects(object_names=["toDelete"])
        assert result["success"] is True
        assert not cmds.objExists("toDelete")


# ---------------------------------------------------------------------------
# Scripting actions
# ---------------------------------------------------------------------------


class TestScriptingActions:
    """MEL and Python scripting skill scripts run inside Maya standalone."""

    def setup_method(self):
        _new_scene()

    def test_execute_mel(self):
        mod = _load_script("maya-scripting", "execute_mel")
        result = mod.execute_mel(script="polySphere -r 1 -n melSphere;")
        assert result["success"] is True

    def test_execute_python(self):
        mod = _load_script("maya-scripting", "execute_python")
        result = mod.execute_python(code="import maya.cmds as cmds; cmds.polyCube(n='pyCube')")
        assert result["success"] is True
        assert cmds.objExists("pyCube")

    def test_execute_mel_error_returns_failure(self):
        mod = _load_script("maya-scripting", "execute_mel")
        result = mod.execute_mel(script="this_is_not_valid_mel_!!!;")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Animation actions
# ---------------------------------------------------------------------------


class TestAnimationActions:
    """Keyframe and timeline skill scripts work in Maya standalone."""

    def setup_method(self):
        _new_scene()

    def test_set_and_get_keyframe(self):
        create_mod = _load_script("maya-primitives", "create_cube")
        set_kf_mod = _load_script("maya-animation", "set_keyframe")
        get_kf_mod = _load_script("maya-animation", "get_keyframes")

        create_mod.create_cube(name="animCube")
        result = set_kf_mod.set_keyframe(object_name="animCube", attribute="translateX", time=1, value=0.0)
        assert result["success"] is True

        result2 = set_kf_mod.set_keyframe(object_name="animCube", attribute="translateX", time=10, value=5.0)
        assert result2["success"] is True

        kf_result = get_kf_mod.get_keyframes(object_name="animCube", attribute="translateX")
        assert kf_result["success"] is True
        keys = kf_result["context"].get("keyframes", [])
        assert 1 in keys or 1.0 in keys

    def test_set_timeline(self):
        mod = _load_script("maya-animation", "set_timeline")
        result = mod.set_timeline(start_frame=1, end_frame=120)
        assert result["success"] is True

    def test_get_current_time(self):
        mod = _load_script("maya-animation", "get_current_time")
        result = mod.get_current_time()
        assert result["success"] is True
        assert "current_time" in result["context"]


# ---------------------------------------------------------------------------
# Material actions
# ---------------------------------------------------------------------------


class TestMaterialActions:
    """Material creation and assignment skill scripts work in Maya standalone."""

    def setup_method(self):
        _new_scene()

    def test_create_and_assign_material(self):
        create_sphere_mod = _load_script("maya-primitives", "create_sphere")
        create_mat_mod = _load_script("maya-materials", "create_material")
        assign_mod = _load_script("maya-materials", "assign_material")

        create_sphere_mod.create_sphere(name="matSphere")
        mat_result = create_mat_mod.create_material(material_type="lambert", name="testLambert")
        assert mat_result["success"] is True

        assign_result = assign_mod.assign_material(material_name="testLambert", objects=["matSphere"])
        assert assign_result["success"] is True

    def test_list_materials(self):
        mod = _load_script("maya-materials", "list_materials")
        result = mod.list_materials()
        assert result["success"] is True
        assert "materials" in result["context"]
        assert len(result["context"]["materials"]) >= 1
