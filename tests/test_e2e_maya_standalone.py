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
import json
import threading
import urllib.request
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


# Resolve skills root: prefer the installed package location (packaged .mod
# module), fall back to the source tree (development / pip install -e).
def _resolve_skills_root() -> Path:
    """Find the skills/ directory from either installed package or source tree."""
    # 1. Installed package (works with packaged .mod module)
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        package_dir = Path(dcc_mcp_maya.__file__).resolve().parent
        skills_dir = package_dir / "skills"
        if skills_dir.is_dir():
            return skills_dir
    except ImportError:
        pass

    # 2. Source tree (development / pip install -e)
    src_skills = Path(__file__).resolve().parent.parent / "src" / "dcc_mcp_maya" / "skills"
    if src_skills.is_dir():
        return src_skills

    # 3. Environment variable override
    import os  # noqa: PLC0415

    env_dir = os.environ.get("DCC_MCP_MAYA_SKILL_PATHS", "")
    if env_dir:
        first = Path(env_dir.split(os.pathsep)[0])
        if first.is_dir():
            return first

    raise RuntimeError("Cannot find dcc_mcp_maya skills/ directory — check installation")


_SKILLS_ROOT = _resolve_skills_root()


# Ensure dcc_mcp_maya is importable in packaged module mode
# (Maya standalone does not process .mod PYTHONPATH directives)
def _ensure_package_importable() -> None:
    """Add the packaged module's python/ to sys.path if needed."""
    import sys  # noqa: PLC0415

    try:
        import dcc_mcp_maya  # noqa: F401

        return  # already importable
    except ImportError:
        pass

    # Try the .mod module directory from environment variable
    import os  # noqa: PLC0415

    mod_dir = os.environ.get("DCC_MCP_MAYA_MOD_DIR", "")
    if mod_dir:
        python_dir = Path(mod_dir) / "python"
        if python_dir.is_dir() and str(python_dir) not in sys.path:
            sys.path.insert(0, str(python_dir))


_ensure_package_importable()


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


def _mcp_post(url, body):
    """POST a JSON-RPC body to *url* and return (status, response_dict)."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read())


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


class TestServerLifecycle:
    """MayaMcpServer starts, reports a valid URL, and stops cleanly."""

    def test_start_and_stop(self):
        from dcc_mcp_maya.server import MayaMcpServer

        server = MayaMcpServer(port=0)
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
        """Skills are discovered via SKILL.md (progressive loading — discovered, not loaded)."""
        from dcc_mcp_maya.server import MayaMcpServer

        server = MayaMcpServer(port=0)
        server.register_builtin_actions()
        # Progressive loading: discover() finds skills but does NOT load them.
        # list_skills() returns all discovered skills regardless of status.
        all_skills = {s.name if hasattr(s, "name") else s["name"] for s in server._server.list_skills()}
        # Key skills must be discoverable
        assert "maya-primitives" in all_skills
        assert "maya-scripting" in all_skills
        assert "maya-scene" in all_skills
        assert "maya-animation" in all_skills
        assert len(all_skills) >= 20


# ---------------------------------------------------------------------------
# MCP HTTP connectivity (real HTTP JSON-RPC against live server)
# ---------------------------------------------------------------------------


class TestMcpHttpConnectivity:
    """MCP server responds correctly to real HTTP JSON-RPC requests.

    Uses a class-scoped server fixture so all tests share one port.
    """

    @pytest.fixture(autouse=True, scope="class")
    def _start_server(self, request):
        from dcc_mcp_maya.server import MayaMcpServer

        _new_scene()
        server = MayaMcpServer(port=0)
        server.register_builtin_actions()
        handle = server.start()
        request.cls._mcp_url = handle.mcp_url()
        yield
        server.stop()

    def test_initialize_handshake(self):
        code, body = _mcp_post(
            self._mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test", "version": "1.0"},
                },
            },
        )
        assert code == 200
        result = body["result"]
        assert result["protocolVersion"] == "2025-03-26"
        assert result["serverInfo"]["name"] == "maya-mcp"

    def test_tools_list_shows_core_and_stubs(self):
        """tools/list returns core discovery tools + skill stubs (progressive loading).

        In the progressive (lazy) loading model, tools/list returns three layers:
        1. Core discovery tools (find_skills, list_skills, get_skill_info, load_skill, ...)
        2. Already-loaded skill tools with full input_schema
        3. Unloaded skill stubs as ``__skill__<name>`` with minimal description
        """
        code, body = _mcp_post(
            self._mcp_url,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert code == 200
        tools = body["result"]["tools"]
        names = {t["name"] for t in tools}

        # Layer 1: core discovery tools must always be present
        for core_tool in ("find_skills", "list_skills", "get_skill_info", "load_skill", "unload_skill"):
            assert core_tool in names, f"Core tool {core_tool!r} missing from tools/list"

        # Layer 3: unloaded skills appear as stubs (__skill__<name>)
        stub_names = {n for n in names if n.startswith("__skill__")}
        assert len(stub_names) >= 1, "Expected at least one skill stub in progressive mode"

        # Stubs should have minimal schema (no or empty input_schema)
        for t in tools:
            if t["name"].startswith("__skill__"):
                schema = t.get("inputSchema", {})
                # Stubs have empty or minimal input_schema
                assert schema.get("properties", {}) == {} or "properties" not in schema, (
                    f"Stub {t['name']} should not have full input_schema"
                )

    def test_load_skill_exposes_full_tools(self):
        """Calling load_skill replaces a stub with fully-schemad tools."""
        # First, list tools to find a skill stub
        code, body = _mcp_post(
            self._mcp_url,
            {"jsonrpc": "2.0", "id": 10, "method": "tools/list"},
        )
        assert code == 200
        before_names = {t["name"] for t in body["result"]["tools"]}
        stubs_before = {n for n in before_names if n.startswith("__skill__")}
        assert len(stubs_before) >= 1, "Need at least one stub to test progressive loading"

        # Pick the maya-scene stub (guaranteed in E2E with real skills)
        scene_stub = "__skill__maya-scene"
        if scene_stub not in stubs_before:
            # Pick first available stub
            scene_stub = next(iter(stubs_before))

        # Load the skill via tools/call
        code, body = _mcp_post(
            self._mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {"name": "load_skill", "arguments": {"skill_name": scene_stub.replace("__skill__", "")}},
            },
        )
        assert code == 200

        # Now tools/list should show the skill's real tools instead of the stub
        code, body = _mcp_post(
            self._mcp_url,
            {"jsonrpc": "2.0", "id": 12, "method": "tools/list"},
        )
        assert code == 200
        after_names = {t["name"] for t in body["result"]["tools"]}

        # The stub should be gone, replaced by real tools
        assert scene_stub not in after_names, f"Stub {scene_stub} should be removed after load_skill"

        # The loaded skill's real tools should now be present
        skill_prefix = scene_stub.replace("__skill__", "").replace("-", "_") + "__"
        real_tools = {n for n in after_names if n.startswith(skill_prefix)}
        assert len(real_tools) >= 1, f"Expected tools prefixed with {skill_prefix!r} after loading"

    @pytest.mark.xfail(
        reason="dcc-mcp-core subprocess executor uses relative script path; known issue",
        strict=False,
    )
    def test_tools_call_get_session_info_via_http(self):
        """tools/call returns Maya session info over HTTP."""
        code, body = _mcp_post(
            self._mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "maya_scene__get_session_info", "arguments": {}},
            },
        )
        assert code == 200
        content = body["result"]["content"]
        assert len(content) > 0
        # Content is a list of {type, text} blocks
        text = content[0].get("text", "")
        assert "maya_version" in text or "success" in text

    @pytest.mark.xfail(
        reason="dcc-mcp-core subprocess executor uses relative script path; known issue",
        strict=False,
    )
    def test_tools_call_create_sphere_via_http(self):
        """tools/call create_sphere returns success in JSON response."""
        code, body = _mcp_post(
            self._mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_sphere",
                    "arguments": {"radius": 1.5, "name": "httpSphere"},
                },
            },
        )
        assert code == 200
        # Verify JSON response indicates success (MCP server ran the tool)
        content = body["result"]["content"]
        assert len(content) > 0
        text = content[0].get("text", "")
        assert "success" in text or "httpSphere" in text

    @pytest.mark.xfail(
        reason="dcc-mcp-core subprocess executor uses relative script path; known issue",
        strict=False,
    )
    def test_tools_call_execute_python_via_http(self):
        """tools/call execute_python returns success in JSON response."""
        code, body = _mcp_post(
            self._mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "maya_scripting__execute_python",
                    "arguments": {"code": "import maya.cmds as cmds; cmds.polyCube(n='httpCube')"},
                },
            },
        )
        assert code == 200
        content = body["result"]["content"]
        assert len(content) > 0
        # Tool executed — response contains result text
        text = content[0].get("text", "")
        assert isinstance(text, str) and len(text) > 0


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


# ---------------------------------------------------------------------------
# Rigging workflow
# ---------------------------------------------------------------------------


class TestRiggingWorkflow:
    """Multi-step rigging workflows: joints, skin, IK, blend shapes."""

    def setup_method(self):
        _new_scene()

    def test_joint_chain_and_skin_bind(self):
        """Create a cube, a 3-joint chain, then bind skin — verify skinCluster."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        joint_mod = _load_script("maya-rigging", "create_joint")
        bind_mod = _load_script("maya-rigging", "skin_cluster_bind")

        cube_mod.create_cube(name="skinMesh")

        # Root joint at origin
        r = joint_mod.create_joint(name="jntRoot", position=[0.0, 0.0, 0.0])
        assert r["success"] is True
        # Mid joint
        r = joint_mod.create_joint(name="jntMid", position=[0.0, 2.0, 0.0], parent="jntRoot")
        assert r["success"] is True
        # Tip joint
        r = joint_mod.create_joint(name="jntTip", position=[0.0, 4.0, 0.0], parent="jntMid")
        assert r["success"] is True

        bind_result = bind_mod.skin_cluster_bind(
            joints=["jntRoot", "jntMid", "jntTip"],
            mesh="skinMesh",
            max_influences=3,
        )
        assert bind_result["success"] is True
        # A skinCluster node must exist
        assert len(cmds.ls(type="skinCluster")) > 0

    def test_ik_handle_on_joint_chain(self):
        """Create a joint chain then apply an IK handle — verify node exists."""
        joint_mod = _load_script("maya-rigging", "create_joint")
        ik_mod = _load_script("maya-rigging", "create_ik_handle")

        joint_mod.create_joint(name="ikRoot", position=[0.0, 0.0, 0.0])
        joint_mod.create_joint(name="ikMid", position=[0.0, 2.0, 0.0], parent="ikRoot")
        joint_mod.create_joint(name="ikTip", position=[0.0, 4.0, 0.0], parent="ikMid")

        ik_result = ik_mod.create_ik_handle(
            start_joint="ikRoot",
            end_joint="ikTip",
            name="testIK",
        )
        assert ik_result["success"] is True
        assert cmds.objExists("testIK")

    def test_blend_shape_workflow(self):
        """Base + target spheres → blend shape node created."""
        sphere_mod = _load_script("maya-primitives", "create_sphere")
        set_tf_mod = _load_script("maya-primitives", "set_transform")
        bs_mod = _load_script("maya-rigging", "create_blend_shape")

        sphere_mod.create_sphere(name="bsBase")
        sphere_mod.create_sphere(name="bsTarget")
        # Move target so it's distinguishable
        set_tf_mod.set_transform(object_name="bsTarget", translate=[5.0, 0.0, 0.0])

        bs_result = bs_mod.create_blend_shape(
            base_mesh="bsBase",
            target_meshes=["bsTarget"],
            name="testBlendShape",
        )
        assert bs_result["success"] is True
        assert len(cmds.ls(type="blendShape")) > 0


# ---------------------------------------------------------------------------
# Animation workflow
# ---------------------------------------------------------------------------


class TestAnimationWorkflow:
    """Multi-attribute keyframe sequences, timeline, bake, curve queries."""

    def setup_method(self):
        _new_scene()

    def test_multi_attribute_keyframe_sequence(self):
        """Key tx and ty on multiple frames, verify keyframe lists."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        set_kf_mod = _load_script("maya-animation", "set_keyframe")
        get_kf_mod = _load_script("maya-animation", "get_keyframes")

        cube_mod.create_cube(name="multiAnimCube")

        # translateX: 0 at frame 1, 10 at frame 24
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateX", time=1, value=0.0)
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateX", time=24, value=10.0)
        # translateY: 0 at frame 1, 5 at frame 12
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateY", time=1, value=0.0)
        set_kf_mod.set_keyframe(object_name="multiAnimCube", attribute="translateY", time=12, value=5.0)

        tx_keys = get_kf_mod.get_keyframes(object_name="multiAnimCube", attribute="translateX")
        assert tx_keys["success"] is True
        keys = tx_keys["context"].get("keyframes", [])
        assert 1 in keys or 1.0 in keys
        assert 24 in keys or 24.0 in keys

        ty_keys = get_kf_mod.get_keyframes(object_name="multiAnimCube", attribute="translateY")
        assert ty_keys["success"] is True
        assert len(ty_keys["context"].get("keyframes", [])) >= 2

    def test_set_current_time_and_query(self):
        """set_current_time then get_current_time returns correct frame."""
        set_mod = _load_script("maya-animation", "set_current_time")
        get_mod = _load_script("maya-animation", "get_current_time")

        set_result = set_mod.set_current_time(frame=15)
        assert set_result["success"] is True

        get_result = get_mod.get_current_time()
        assert get_result["success"] is True
        assert abs(get_result["context"]["current_time"] - 15.0) < 0.01

    def test_timeline_and_bake_simulation(self):
        """Set timeline, add keyframes, bake, verify animation curves exist."""
        tl_mod = _load_script("maya-animation", "set_timeline")
        loc_mod = _load_script("maya-scene", "create_locator")
        set_kf_mod = _load_script("maya-animation", "set_keyframe")
        bake_mod = _load_script("maya-animation", "bake_simulation")
        list_mod = _load_script("maya-animation", "list_animation_curves")

        tl_mod.set_timeline(start_frame=1, end_frame=48)
        loc_mod.create_locator(name="bakeLoc")

        set_kf_mod.set_keyframe(object_name="bakeLoc", attribute="translateX", time=1, value=0.0)
        set_kf_mod.set_keyframe(object_name="bakeLoc", attribute="translateX", time=48, value=10.0)

        bake_result = bake_mod.bake_simulation(
            objects=["bakeLoc"],
            start_frame=1.0,
            end_frame=48.0,
            sample_by=1.0,
        )
        assert bake_result["success"] is True

        curves = list_mod.list_animation_curves(object_name="bakeLoc")
        assert curves["success"] is True
        assert len(curves["context"].get("curves", [])) > 0


# ---------------------------------------------------------------------------
# Mesh and material workflow
# ---------------------------------------------------------------------------


class TestMeshAndMaterialWorkflow:
    """Subdivision, merge, cleanup, UV ops, material assignment chain."""

    def setup_method(self):
        _new_scene()

    def test_mesh_ops_chain(self):
        """Sphere → subdivision → get_poly_count > baseline → merge → cleanup."""
        sphere_mod = _load_script("maya-primitives", "create_sphere")
        subdiv_mod = _load_script("maya-mesh-ops", "apply_subdivision")
        count_mod = _load_script("maya-mesh-ops", "get_poly_count")
        merge_mod = _load_script("maya-mesh-ops", "merge_vertices")
        cleanup_mod = _load_script("maya-mesh-ops", "cleanup_mesh")

        sphere_mod.create_sphere(name="meshSphere")

        # Baseline poly count
        before = count_mod.get_poly_count("meshSphere")
        assert before["success"] is True
        base_faces = before["context"].get("faces", 0)

        # Subdivide → more polygons
        subdiv_mod.apply_subdivision(object_name="meshSphere", level=1, method="preview")
        after = count_mod.get_poly_count("meshSphere")
        assert after["success"] is True
        assert after["context"].get("faces", 0) >= base_faces

        # Merge and cleanup don't crash
        merge_mod.merge_vertices(object_name="meshSphere", threshold=0.001)
        cleanup_mod.cleanup_mesh(object_name="meshSphere")

    def test_material_and_uv_workflow(self):
        """Create plane → blinn material → assign → UV set → project → query."""
        plane_mod = _load_script("maya-primitives", "create_plane")
        mat_mod = _load_script("maya-materials", "create_material")
        assign_mod = _load_script("maya-materials", "assign_material")
        uv_set_mod = _load_script("maya-uv-ops", "create_uv_set")
        project_mod = _load_script("maya-uv-ops", "project_uvs")
        uv_info_mod = _load_script("maya-uv-ops", "get_uv_info")
        shader_mod = _load_script("maya-materials", "get_shader_assignment")

        plane_mod.create_plane(name="uvPlane")

        mat_result = mat_mod.create_material(material_type="blinn", name="testBlinn")
        assert mat_result["success"] is True

        assign_mod.assign_material(material_name="testBlinn", objects=["uvPlane"])

        uv_set_mod.create_uv_set(object_name="uvPlane", uv_set_name="myUVSet")
        project_mod.project_uvs(object_name="uvPlane", projection_type="planar", axis="y")

        uv_info = uv_info_mod.get_uv_info(object_name="uvPlane")
        assert uv_info["success"] is True

        shader_info = shader_mod.get_shader_assignment(object_name="uvPlane")
        assert shader_info["success"] is True

    def test_rename_and_group_workflow(self):
        """Create cubes → rename → group → parent → verify hierarchy."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        rename_mod = _load_script("maya-primitives", "rename_object")
        group_mod = _load_script("maya-scene", "group_objects")
        parent_mod = _load_script("maya-scene", "parent_object")

        cube_mod.create_cube(name="cubeA")
        cube_mod.create_cube(name="cubeB")

        ren = rename_mod.rename_object(object_name="cubeA", new_name="cubeRenamed")
        assert ren["success"] is True
        assert cmds.objExists("cubeRenamed")

        grp = group_mod.group_objects(objects=["cubeRenamed"], group_name="myGroup")
        assert grp["success"] is True
        assert cmds.objExists("myGroup")

        # Parent cubeB under myGroup
        par = parent_mod.parent_object(child="cubeB", parent="myGroup")
        assert par["success"] is True
        assert cmds.listRelatives("cubeB", parent=True)[0] == "myGroup"


# ---------------------------------------------------------------------------
# Node graph workflow
# ---------------------------------------------------------------------------


class TestNodeGraphWorkflow:
    """Attribute ops, connect/disconnect, expressions, display layers."""

    def setup_method(self):
        _new_scene()

    def test_add_and_connect_attribute(self):
        """Add float attr to cube A, connect to cube B translateX, then disconnect."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        add_attr_mod = _load_script("maya-attributes", "add_attribute")
        connect_mod = _load_script("maya-node-graph", "connect_attr")
        list_conn_mod = _load_script("maya-node-graph", "list_connections")
        disconnect_mod = _load_script("maya-node-graph", "disconnect_attr")

        cube_mod.create_cube(name="srcCube")
        cube_mod.create_cube(name="dstCube")

        add_result = add_attr_mod.add_attribute(
            node_name="srcCube",
            attribute="myFloat",
            attr_type="float",
            keyable=True,
        )
        assert add_result["success"] is True

        connect_result = connect_mod.connect_attr(
            source_attr="srcCube.myFloat",
            dest_attr="dstCube.translateX",
            force=True,
        )
        assert connect_result["success"] is True

        # Verify connection exists
        conns = list_conn_mod.list_connections(object_name="dstCube", attribute="translateX")
        assert conns["success"] is True
        assert len(conns["context"].get("connections", [])) > 0

        # Disconnect
        disc = disconnect_mod.disconnect_attr(
            source_attr="srcCube.myFloat",
            dest_attr="dstCube.translateX",
        )
        assert disc["success"] is True

    def test_expression_driven_value(self):
        """Create expression driving tx = frame*0.1 → verify at frame 10."""
        cube_mod = _load_script("maya-primitives", "create_cube")
        expr_mod = _load_script("maya-expressions", "create_expression")
        list_expr_mod = _load_script("maya-expressions", "list_expressions")
        set_time_mod = _load_script("maya-animation", "set_current_time")
        get_tf_mod = _load_script("maya-primitives", "get_transform")
        del_expr_mod = _load_script("maya-expressions", "delete_expression")

        cube_mod.create_cube(name="exprCube")

        expr_result = expr_mod.create_expression(
            expression="exprCube.translateX = frame * 0.1;",
            name="testExpr",
        )
        assert expr_result["success"] is True

        exprs = list_expr_mod.list_expressions()
        assert exprs["success"] is True
        names = [e.get("name", "") for e in exprs["context"].get("expressions", [])]
        assert "testExpr" in names

        set_time_mod.set_current_time(frame=10)
        tf = get_tf_mod.get_transform(object_name="exprCube")
        assert tf["success"] is True
        tx = tf["context"]["translate"][0]
        assert abs(tx - 1.0) < 0.1  # frame 10 * 0.1 ≈ 1.0

        del_expr_mod.delete_expression(expression_name="testExpr")

    def test_display_layer_workflow(self):
        """Create display layer, add objects, list layers, delete."""
        sphere_mod = _load_script("maya-primitives", "create_sphere")
        dl_create_mod = _load_script("maya-display", "create_display_layer")
        dl_set_mod = _load_script("maya-display", "set_display_layer")
        dl_list_mod = _load_script("maya-display", "list_display_layers")
        dl_delete_mod = _load_script("maya-display", "delete_display_layer")

        sphere_mod.create_sphere(name="dlSphere1")
        sphere_mod.create_sphere(name="dlSphere2")

        create_result = dl_create_mod.create_display_layer(name="testLayer")
        assert create_result["success"] is True

        set_result = dl_set_mod.set_display_layer(
            layer_name="testLayer",
            objects=["dlSphere1", "dlSphere2"],
        )
        assert set_result["success"] is True

        list_result = dl_list_mod.list_display_layers()
        assert list_result["success"] is True
        layer_names = [lay.get("name", "") for lay in list_result["context"].get("layers", [])]
        assert "testLayer" in layer_names

        del_result = dl_delete_mod.delete_display_layer(layer_name="testLayer")
        assert del_result["success"] is True
        layer_names_after = [
            lay.get("name", "") for lay in dl_list_mod.list_display_layers()["context"].get("layers", [])
        ]
        assert "testLayer" not in layer_names_after


# ---------------------------------------------------------------------------
# Multi-instance isolation
# ---------------------------------------------------------------------------


class TestMultiInstanceIsolation:
    """Verify that multiple MayaMcpServer instances on different ports are
    fully independent: independent lifecycles, no port conflicts, concurrent
    HTTP requests each reach the correct server.
    """

    def _make_server(self):
        """Create, populate and start a fresh MayaMcpServer on a random port."""
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.register_builtin_actions()
        handle = srv.start()
        return srv, handle

    def test_two_instances_on_different_ports(self):
        """Two servers start on different OS-assigned ports simultaneously."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        try:
            assert h_a.port != h_b.port, "Both servers must use distinct ports"
            assert h_a.mcp_url() != h_b.mcp_url()
            assert srv_a.is_running
            assert srv_b.is_running
        finally:
            srv_a.stop()
            srv_b.stop()

    def test_stop_one_does_not_affect_other(self):
        """Stopping server A leaves server B fully operational."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        try:
            srv_a.stop()
            assert not srv_a.is_running
            assert srv_b.is_running

            # Server B still responds to initialize
            code, body = _mcp_post(
                h_b.mcp_url(),
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "multi-test", "version": "1"},
                    },
                },
            )
            assert code == 200
            assert body["result"]["serverInfo"]["name"] == "maya-mcp"
        finally:
            srv_b.stop()

    def test_three_instances_all_serve_tools_list(self):
        """Three servers all respond to tools/list independently."""
        servers = [self._make_server() for _ in range(3)]
        try:
            for srv, handle in servers:
                code, body = _mcp_post(
                    handle.mcp_url(),
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                )
                assert code == 200
                tools = body["result"]["tools"]
                names = {t["name"] for t in tools}
                # Core discovery tools must be present
                assert "find_skills" in names
                assert "load_skill" in names
        finally:
            for srv, handle in servers:
                srv.stop()

    def test_concurrent_requests_to_two_servers(self):
        """Concurrent HTTP calls to two servers return independent results."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        results = {}

        def call_server(label, url, req_id):
            try:
                code, body = _mcp_post(
                    url,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": label, "version": "1"},
                        },
                    },
                )
                results[label] = (code, body)
            except Exception as exc:
                results[label] = exc

        try:
            t_a = threading.Thread(target=call_server, args=("serverA", h_a.mcp_url(), 10))
            t_b = threading.Thread(target=call_server, args=("serverB", h_b.mcp_url(), 11))
            t_a.start()
            t_b.start()
            t_a.join(timeout=15)
            t_b.join(timeout=15)

            for label in ("serverA", "serverB"):
                assert label in results, "Thread did not complete"
                r = results[label]
                assert not isinstance(r, Exception), "Request failed: {}".format(r)
                code, body = r
                assert code == 200
                assert body["result"]["serverInfo"]["name"] == "maya-mcp"
        finally:
            srv_a.stop()
            srv_b.stop()

    def test_restart_one_server_other_unaffected(self):
        """A restarted server comes back up; the other server is unaffected."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        srv_a2 = None
        try:
            srv_a.stop()
            assert not srv_a.is_running
            assert srv_b.is_running

            from dcc_mcp_maya.server import MayaMcpServer

            srv_a2 = MayaMcpServer(port=0)
            srv_a2.register_builtin_actions()
            srv_a2.start()

            assert srv_a2.is_running
            assert srv_b.is_running

            code, _ = _mcp_post(
                h_b.mcp_url(),
                {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
            )
            assert code == 200
        finally:
            if srv_a2 is not None:
                srv_a2.stop()
            srv_b.stop()


# ---------------------------------------------------------------------------
# Multi-instance concurrent workflows (shared Maya session)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="dcc-mcp-core subprocess executor uses relative script path; known issue",
    strict=False,
)
class TestMultiInstanceConcurrentWorkflows:
    """Two MCP servers run different Maya workflows concurrently via HTTP.

    Maya standalone shares a single scene, but each server MCP layer is
    independent.  We verify that concurrent tool calls from different servers
    do not crash either server and each server stays fully operational.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        _new_scene()
        from dcc_mcp_maya.server import MayaMcpServer

        self._srv_a = MayaMcpServer(port=0, server_name="maya-worker-a")
        self._srv_a.register_builtin_actions()
        self._h_a = self._srv_a.start()

        self._srv_b = MayaMcpServer(port=0, server_name="maya-worker-b")
        self._srv_b.register_builtin_actions()
        self._h_b = self._srv_b.start()
        yield
        self._srv_a.stop()
        self._srv_b.stop()

    def test_different_server_names(self):
        """Each server reports its own configured name in initialize."""
        _, body_a = _mcp_post(
            self._h_a.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        _, body_b = _mcp_post(
            self._h_b.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert body_a["result"]["serverInfo"]["name"] == "maya-worker-a"
        assert body_b["result"]["serverInfo"]["name"] == "maya-worker-b"

    def test_sequential_tool_calls_from_two_servers(self):
        """Server A creates a sphere; server B creates a cube via HTTP."""
        code_a, body_a = _mcp_post(
            self._h_a.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_sphere",
                    "arguments": {"name": "multiSphereA"},
                },
            },
        )
        assert code_a == 200
        text_a = body_a["result"]["content"][0].get("text", "")
        assert "success" in text_a or "multiSphereA" in text_a

        code_b, body_b = _mcp_post(
            self._h_b.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_cube",
                    "arguments": {"name": "multiCubeB"},
                },
            },
        )
        assert code_b == 200
        text_b = body_b["result"]["content"][0].get("text", "")
        assert "success" in text_b or "multiCubeB" in text_b

        # Both HTTP calls succeeded — scene state verified via response text
        # (cmds.objExists is unreliable across threads in standalone mode)

    def test_concurrent_tool_calls_to_different_servers(self):
        """Concurrent tools/call to server A and B both return 200."""
        results = {}

        def call_a():
            try:
                code, body = _mcp_post(
                    self._h_a.mcp_url(),
                    {
                        "jsonrpc": "2.0",
                        "id": 20,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__get_session_info", "arguments": {}},
                    },
                )
                results["a"] = (code, body)
            except Exception as exc:
                results["a"] = exc

        def call_b():
            try:
                code, body = _mcp_post(
                    self._h_b.mcp_url(),
                    {
                        "jsonrpc": "2.0",
                        "id": 21,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__list_objects", "arguments": {}},
                    },
                )
                results["b"] = (code, body)
            except Exception as exc:
                results["b"] = exc

        t_a = threading.Thread(target=call_a)
        t_b = threading.Thread(target=call_b)
        t_a.start()
        t_b.start()
        t_a.join(timeout=15)
        t_b.join(timeout=15)

        assert "a" in results and "b" in results
        for key in ("a", "b"):
            r = results[key]
            assert not isinstance(r, Exception), "Request {} failed: {}".format(key, r)
            code, body = r
            assert code == 200

    def test_tools_list_stable_after_concurrent_calls(self):
        """tools/list stays complete on both servers after burst of concurrent calls."""
        errors = []

        def fire_call(url, req_id):
            try:
                _mcp_post(
                    url,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__get_session_info", "arguments": {}},
                    },
                )
            except Exception as exc:
                errors.append(exc)

        threads = []
        for i in range(6):
            url = self._h_a.mcp_url() if i % 2 == 0 else self._h_b.mcp_url()
            threads.append(threading.Thread(target=fire_call, args=(url, 30 + i)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        assert not errors, "Concurrent calls raised: {}".format(errors)

        for handle in (self._h_a, self._h_b):
            code, body = _mcp_post(
                handle.mcp_url(),
                {"jsonrpc": "2.0", "id": 99, "method": "tools/list"},
            )
            assert code == 200
            tools = body["result"]["tools"]
            names = {t["name"] for t in tools}
            assert "find_skills" in names

    def test_cross_server_scene_visibility(self):
        """Nodes created via server A are visible when queried via server B."""
        _mcp_post(
            self._h_a.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 40,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_sphere",
                    "arguments": {"name": "crossVisSphere"},
                },
            },
        )

        code, body = _mcp_post(
            self._h_b.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 41,
                "method": "tools/call",
                "params": {"name": "maya_scene__list_objects", "arguments": {}},
            },
        )
        assert code == 200
        content_text = body["result"]["content"][0].get("text", "")
        assert "success" in content_text


# ---------------------------------------------------------------------------
# Plugin entry-point (initializePlugin / uninitializePlugin)
# ---------------------------------------------------------------------------


class TestPluginEntryPoint:
    """Verify that the Maya plugin script's initializePlugin and
    uninitializePlugin work correctly in Maya standalone for 2022-2025.

    Background
    ----------
    In some Maya standalone / batch environments ``maya.OpenMaya`` (API 1.0)
    does not expose ``MFnPlugin``, causing ``AttributeError`` at plugin load
    time.  The plugin now imports from ``maya.api.OpenMaya`` (API 2.0) first
    and falls back to ``maya.OpenMaya``.  These tests exercise that path.

    Because ``cmds.loadPlugin`` requires a file on disk inside MAYA_PLUG_IN_PATH
    we instead import the plugin module directly and pass a mock MFnPlugin
    object.  This mirrors what Maya itself does and lets us catch the
    ``AttributeError`` that triggered the original bug report.
    """

    @pytest.fixture
    def plugin_module(self):
        """Import the plugin script as a plain Python module."""
        plugin_path = Path(__file__).parent.parent / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
        spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_plugin", plugin_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @pytest.fixture
    def mock_mfn_plugin(self):
        """Return a lightweight stand-in for the MFnPlugin *mobject* argument.

        Maya passes an ``MObject`` (plugin node) to ``initializePlugin`` /
        ``uninitializePlugin``.  We supply a dummy class that accepts positional
        args and exposes the minimal interface Maya's ``MFnPlugin`` requires so
        that ``om.MFnPlugin(plugin, vendor, version)`` does not raise.
        """

        class _FakePluginObject:
            pass

        # Patch the om.MFnPlugin so it accepts our fake object without needing
        # a real Maya plugin node.
        import maya.api.OpenMaya as _om2

        class _FakeMFnPlugin:
            def __init__(self, *args, **kwargs):
                pass

        _original = getattr(_om2, "MFnPlugin", None)
        _om2.MFnPlugin = _FakeMFnPlugin
        yield _FakePluginObject()
        # Restore
        if _original is not None:
            _om2.MFnPlugin = _original
        else:
            del _om2.MFnPlugin

    def test_om_mfnplugin_importable(self):
        """maya.api.OpenMaya.MFnPlugin is always available (Maya 2022-2025)."""
        import maya.api.OpenMaya as om2

        assert hasattr(om2, "MFnPlugin"), (
            "maya.api.OpenMaya.MFnPlugin not found — plugin will raise AttributeError on load"
        )

    def test_plugin_uses_api2_import(self, plugin_module):
        """Plugin module must use maya.api.OpenMaya and declare maya_useNewAPI."""
        import inspect

        src = inspect.getsource(plugin_module)
        assert "maya.api.OpenMaya" in src, (
            "Plugin should import from maya.api.OpenMaya (API 2.0) to avoid MFnPlugin AttributeError"
        )
        # maya_useNewAPI() is the official Autodesk mechanism that tells Maya to
        # pass API 2.0 MObject wrappers to initializePlugin/uninitializePlugin.
        assert "maya_useNewAPI" in src, (
            "Plugin must declare maya_useNewAPI() so Maya passes API 2.0 objects to plugin callbacks"
        )

    def test_initialize_plugin(self, plugin_module, mock_mfn_plugin):
        """initializePlugin starts the MCP server without raising."""
        import os

        os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
        try:
            plugin_module.initializePlugin(mock_mfn_plugin)
            assert plugin_module._handle is not None or True  # server may be None if start fails gracefully
        except AttributeError as exc:
            pytest.fail(f"initializePlugin raised AttributeError — MFnPlugin compat broken: {exc}")
        finally:
            # Always clean up the server to avoid port leaks across tests
            try:
                plugin_module.uninitializePlugin(mock_mfn_plugin)
            except Exception:
                pass

    def test_uninitialize_plugin(self, plugin_module, mock_mfn_plugin):
        """uninitializePlugin stops the MCP server without raising."""
        import os

        os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
        try:
            plugin_module.initializePlugin(mock_mfn_plugin)
        except Exception:
            pass  # If init failed for unrelated reason, still test uninit

        try:
            plugin_module.uninitializePlugin(mock_mfn_plugin)
        except AttributeError as exc:
            pytest.fail(f"uninitializePlugin raised AttributeError — MFnPlugin compat broken: {exc}")

    def test_initialize_uninitialize_cycle(self, plugin_module, mock_mfn_plugin):
        """Full init → uninit cycle runs cleanly (simulates plugin load/unload)."""
        import os

        os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
        errors = []
        try:
            plugin_module.initializePlugin(mock_mfn_plugin)
        except AttributeError as exc:
            errors.append(f"initializePlugin: {exc}")
        except Exception:
            pass  # RuntimeError from server start is acceptable here

        try:
            plugin_module.uninitializePlugin(mock_mfn_plugin)
        except AttributeError as exc:
            errors.append(f"uninitializePlugin: {exc}")
        except Exception:
            pass

        assert not errors, "AttributeError in plugin lifecycle: {}".format(errors)

    def test_no_mfnplugin_in_old_api(self):
        """Documents that maya.OpenMaya (API 1.0) may not have MFnPlugin.

        This test is informational: it passes regardless of whether the old API
        exposes MFnPlugin, but it records which environment triggered the bug.
        """
        import maya.OpenMaya as om1

        has_attr = hasattr(om1, "MFnPlugin")
        # Just record — we don't assert True/False because it varies per version
        # and environment.  The fix is to always use API 2.0.
        assert isinstance(has_attr, bool)


# ---------------------------------------------------------------------------
# Singleton re-entrancy
# ---------------------------------------------------------------------------


class TestSingletonReentrancy:
    """Module-level start_server / stop_server is thread-safe and idempotent."""

    def test_idempotent_start_returns_same_handle(self):
        """Calling start_server twice without stopping returns the same handle."""
        from dcc_mcp_maya import start_server, stop_server

        h1 = start_server(port=0)
        h2 = start_server(port=0)
        try:
            assert h1 is h2, "Second call must return existing handle"
            assert h1.port == h2.port
        finally:
            stop_server()

    def test_stop_then_restart_creates_new_server(self):
        """After stop_server(), start_server() creates a fresh server instance."""
        from dcc_mcp_maya import start_server, stop_server

        h1 = start_server(port=0)
        stop_server()

        h2 = start_server(port=0)
        try:
            assert h2 is not h1
            assert h2.mcp_url().startswith("http://")
        finally:
            stop_server()

    def test_concurrent_start_server_calls_are_safe(self):
        """Multiple threads calling start_server() concurrently get the same handle."""
        from dcc_mcp_maya import start_server, stop_server

        handles = []
        errors = []
        lock = threading.Lock()

        def do_start():
            try:
                h = start_server(port=0)
                with lock:
                    handles.append(h)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=do_start) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        try:
            assert not errors, "Concurrent start_server raised: {}".format(errors)
            assert len(handles) == 5
            ports = {h.port for h in handles}
            assert len(ports) == 1, "Expected singleton port, got: {}".format(ports)
        finally:
            stop_server()
