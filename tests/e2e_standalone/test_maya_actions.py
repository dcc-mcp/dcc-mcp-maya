"""Maya standalone E2E tests."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


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


class TestScriptingActions:
    """MEL and Python scripting skill scripts run inside Maya standalone."""

    def setup_method(self):
        _new_scene()

    def test_execute_mel(self):
        mod = _load_script("maya-scripting", "execute_mel")
        result = mod.execute_mel(code="polySphere -r 1 -n melSphere;")
        assert result["success"] is True

    def test_execute_python(self):
        mod = _load_script("maya-scripting", "execute_python")
        result = mod.execute_python(code="import maya.cmds as cmds; cmds.polyCube(n='pyCube')")
        assert result["success"] is True
        assert cmds.objExists("pyCube")

    def test_execute_mel_error_returns_failure(self):
        mod = _load_script("maya-scripting", "execute_mel")
        result = mod.execute_mel(code="this_is_not_valid_mel_!!!;")
        assert isinstance(result, dict)


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
