"""Round 11: unit tests for maya-primitives Skill scripts.

Covers all 8 scripts under skills/maya-primitives/scripts/:
  - create_sphere
  - create_cube
  - create_cylinder
  - create_plane
  - delete_objects
  - get_transform
  - set_transform
  - rename_object

All Maya dependencies are mocked via sys.modules.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load(skill_dir: str, script_name: str):
    path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(script_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup_maya(cmds_overrides=None):
    """Inject mock maya.cmds into sys.modules; return (patches_dict, mock_cmds).

    The ``maya`` mock must expose ``.cmds`` pointing to the same mock_cmds so
    that ``import maya.cmds as cmds`` resolves correctly even when the module
    is re-loaded via importlib.
    """
    mock_cmds = MagicMock()
    mock_cmds.objExists.return_value = True
    mock_cmds.polySphere.return_value = ("pSphere1", "polySphere1")
    mock_cmds.polyCube.return_value = ("pCube1", "polyCube1")
    mock_cmds.polyCylinder.return_value = ("pCylinder1", "polyCylinder1")
    mock_cmds.polyPlane.return_value = ("pPlane1", "polyPlane1")
    mock_cmds.rename.side_effect = lambda old, new: new
    mock_cmds.ls.return_value = []
    mock_cmds.getAttr.side_effect = lambda attr, **kw: [(0.0, 0.0, 0.0)]
    if cmds_overrides:
        for k, v in cmds_overrides.items():
            setattr(mock_cmds, k, v)
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    patches = {
        "maya": mock_maya,
        "maya.cmds": mock_cmds,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    for k, v in patches.items():
        sys.modules[k] = v
    return patches, mock_cmds


def _teardown(patches):
    for k in patches:
        sys.modules.pop(k, None)


# ===========================================================================
# create_sphere
# ===========================================================================

class TestCreateSphere:
    def test_default_creates_sphere(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_sphere")
            result = mod.create_sphere()
        finally:
            _teardown(patches)
        assert result["success"] is True
        assert "pSphere1" in result["message"]
        mock_cmds.polySphere.assert_called_once()

    def test_custom_radius(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_sphere")
            result = mod.create_sphere(radius=5.0)
        finally:
            _teardown(patches)
        assert result["success"] is True
        call_kwargs = mock_cmds.polySphere.call_args[1]
        assert call_kwargs["radius"] == 5.0

    def test_with_name(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_sphere")
            result = mod.create_sphere(name="mySphere")
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.rename.assert_called_once_with("pSphere1", "mySphere")
        assert result["context"]["object_name"] == "mySphere"

    def test_without_name_no_rename(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_sphere")
            mod.create_sphere()
        finally:
            _teardown(patches)
        mock_cmds.rename.assert_not_called()

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.polySphere.side_effect = RuntimeError("sphere failed")
        try:
            mod = _load("maya-primitives", "create_sphere")
            result = mod.create_sphere()
        finally:
            _teardown(patches)
        assert result["success"] is False


# ===========================================================================
# create_cube
# ===========================================================================

class TestCreateCube:
    def test_default(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cube")
            result = mod.create_cube()
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.polyCube.assert_called_once()

    def test_custom_dimensions(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cube")
            result = mod.create_cube(width=2.0, height=3.0, depth=4.0)
        finally:
            _teardown(patches)
        assert result["success"] is True
        kw = mock_cmds.polyCube.call_args[1]
        assert kw["width"] == 2.0
        assert kw["height"] == 3.0
        assert kw["depth"] == 4.0

    def test_with_name(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cube")
            result = mod.create_cube(name="myCube")
        finally:
            _teardown(patches)
        assert result["success"] is True
        assert result["context"]["object_name"] == "myCube"

    def test_context_has_dimensions(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cube")
            result = mod.create_cube(width=5.0, height=6.0, depth=7.0)
        finally:
            _teardown(patches)
        assert result["context"]["width"] == 5.0
        assert result["context"]["height"] == 6.0
        assert result["context"]["depth"] == 7.0

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.polyCube.side_effect = RuntimeError("cube crash")
        try:
            mod = _load("maya-primitives", "create_cube")
            result = mod.create_cube()
        finally:
            _teardown(patches)
        assert result["success"] is False


# ===========================================================================
# create_cylinder
# ===========================================================================

class TestCreateCylinder:
    def test_default(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cylinder")
            result = mod.create_cylinder()
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.polyCylinder.assert_called_once()

    def test_custom_radius_and_height(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cylinder")
            result = mod.create_cylinder(radius=2.0, height=5.0)
        finally:
            _teardown(patches)
        assert result["success"] is True
        kw = mock_cmds.polyCylinder.call_args[1]
        assert kw["radius"] == 2.0
        assert kw["height"] == 5.0

    def test_with_name(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_cylinder")
            result = mod.create_cylinder(name="myCyl")
        finally:
            _teardown(patches)
        assert result["context"]["object_name"] == "myCyl"

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.polyCylinder.side_effect = RuntimeError("cyl error")
        try:
            mod = _load("maya-primitives", "create_cylinder")
            result = mod.create_cylinder()
        finally:
            _teardown(patches)
        assert result["success"] is False


# ===========================================================================
# create_plane
# ===========================================================================

class TestCreatePlane:
    def test_default(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_plane")
            result = mod.create_plane()
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.polyPlane.assert_called_once()

    def test_custom_size(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_plane")
            mod.create_plane(width=10.0, height=5.0)
        finally:
            _teardown(patches)
        kw = mock_cmds.polyPlane.call_args[1]
        assert kw["width"] == 10.0
        assert kw["height"] == 5.0

    def test_with_name(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "create_plane")
            result = mod.create_plane(name="myPlane")
        finally:
            _teardown(patches)
        assert result["context"]["object_name"] == "myPlane"

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.polyPlane.side_effect = RuntimeError("plane crash")
        try:
            mod = _load("maya-primitives", "create_plane")
            result = mod.create_plane()
        finally:
            _teardown(patches)
        assert result["success"] is False


# ===========================================================================
# delete_objects
# ===========================================================================

class TestDeleteObjects:
    def test_delete_existing(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.ls.return_value = ["pSphere1", "pCube1"]
        try:
            mod = _load("maya-primitives", "delete_objects")
            result = mod.delete_objects(["pSphere1", "pCube1"])
        finally:
            _teardown(patches)
        assert result["success"] is True
        assert result["context"]["deleted"] == ["pSphere1", "pCube1"]
        mock_cmds.delete.assert_called_once_with(["pSphere1", "pCube1"])

    def test_empty_list(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "delete_objects")
            result = mod.delete_objects([])
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.delete.assert_not_called()

    def test_nonexistent_objects(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.ls.return_value = []
        try:
            mod = _load("maya-primitives", "delete_objects")
            result = mod.delete_objects(["ghost1"])
        finally:
            _teardown(patches)
        assert result["success"] is True
        assert result["context"]["deleted"] == []
        mock_cmds.delete.assert_not_called()

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.ls.side_effect = RuntimeError("ls failed")
        try:
            mod = _load("maya-primitives", "delete_objects")
            result = mod.delete_objects(["obj"])
        finally:
            _teardown(patches)
        assert result["success"] is False

    def test_context_has_requested(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.ls.return_value = ["obj1"]
        try:
            mod = _load("maya-primitives", "delete_objects")
            result = mod.delete_objects(["obj1", "obj_missing"])
        finally:
            _teardown(patches)
        assert result["context"]["requested"] == ["obj1", "obj_missing"]


# ===========================================================================
# get_transform
# ===========================================================================

class TestGetTransform:
    def test_success(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.side_effect = lambda attr, **kw: [(1.0, 2.0, 3.0)]
        try:
            mod = _load("maya-primitives", "get_transform")
            result = mod.get_transform("pSphere1")
        finally:
            _teardown(patches)
        assert result["success"] is True
        assert result["context"]["translate"] == [1.0, 2.0, 3.0]
        assert result["context"]["rotate"] == [1.0, 2.0, 3.0]
        assert result["context"]["scale"] == [1.0, 2.0, 3.0]

    def test_object_not_found(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = False
        try:
            mod = _load("maya-primitives", "get_transform")
            result = mod.get_transform("ghost")
        finally:
            _teardown(patches)
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.side_effect = RuntimeError("attr crash")
        try:
            mod = _load("maya-primitives", "get_transform")
            result = mod.get_transform("pSphere1")
        finally:
            _teardown(patches)
        assert result["success"] is False

    def test_context_has_object_name(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.side_effect = lambda attr, **kw: [(0.0, 0.0, 0.0)]
        try:
            mod = _load("maya-primitives", "get_transform")
            result = mod.get_transform("myObj")
        finally:
            _teardown(patches)
        assert result["context"]["object_name"] == "myObj"


# ===========================================================================
# set_transform
# ===========================================================================

class TestSetTransform:
    def test_set_translate(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "set_transform")
            result = mod.set_transform("pSphere1", translate=[1.0, 2.0, 3.0])
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call(
            "pSphere1.translate", 1.0, 2.0, 3.0, type="double3"
        )

    def test_set_rotate(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "set_transform")
            result = mod.set_transform("pCube1", rotate=[45.0, 0.0, 0.0])
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call(
            "pCube1.rotate", 45.0, 0.0, 0.0, type="double3"
        )

    def test_set_scale(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "set_transform")
            result = mod.set_transform("pCube1", scale=[2.0, 2.0, 2.0])
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call(
            "pCube1.scale", 2.0, 2.0, 2.0, type="double3"
        )

    def test_object_not_found(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = False
        try:
            mod = _load("maya-primitives", "set_transform")
            result = mod.set_transform("ghost", translate=[0, 0, 0])
        finally:
            _teardown(patches)
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_no_transform_args(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "set_transform")
            result = mod.set_transform("pSphere1")
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.setAttr.assert_not_called()

    def test_wrong_length_ignored(self):
        patches, mock_cmds = _setup_maya()
        try:
            mod = _load("maya-primitives", "set_transform")
            # only 2 values — should be ignored (len check)
            result = mod.set_transform("pSphere1", translate=[1.0, 2.0])
        finally:
            _teardown(patches)
        assert result["success"] is True
        mock_cmds.setAttr.assert_not_called()

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.setAttr.side_effect = RuntimeError("locked")
        try:
            mod = _load("maya-primitives", "set_transform")
            result = mod.set_transform("pSphere1", translate=[0, 0, 0])
        finally:
            _teardown(patches)
        assert result["success"] is False


# ===========================================================================
# rename_object
# ===========================================================================

class TestRenameObject:
    def test_basic_rename(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.rename.return_value = "newName"
        try:
            mod = _load("maya-primitives", "rename_object")
            result = mod.rename_object("pSphere1", "newName")
        finally:
            _teardown(patches)
        assert result["success"] is True
        assert result["context"]["object_name"] == "newName"
        assert result["context"]["old_name"] == "pSphere1"

    def test_object_not_found(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = False
        try:
            mod = _load("maya-primitives", "rename_object")
            result = mod.rename_object("ghost", "newName")
        finally:
            _teardown(patches)
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_rename_called_with_correct_args(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.rename.return_value = "finalName"
        try:
            mod = _load("maya-primitives", "rename_object")
            mod.rename_object("oldObj", "finalName")
        finally:
            _teardown(patches)
        mock_cmds.rename.assert_called_once_with("oldObj", "finalName")

    def test_exception_returns_error(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.rename.side_effect = RuntimeError("rename clash")
        try:
            mod = _load("maya-primitives", "rename_object")
            result = mod.rename_object("pSphere1", "clashName")
        finally:
            _teardown(patches)
        assert result["success"] is False

    def test_message_contains_names(self):
        patches, mock_cmds = _setup_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.rename.return_value = "renamed"
        try:
            mod = _load("maya-primitives", "rename_object")
            result = mod.rename_object("original", "renamed")
        finally:
            _teardown(patches)
        assert "original" in result["message"]
        assert "renamed" in result["message"]
