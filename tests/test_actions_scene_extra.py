"""Tests for the extra scene/rigging actions added in Round 3."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# shared fixture helpers
# ---------------------------------------------------------------------------


def _mock_maya():
    """Return a (cmds_mock, mel_mock) pair and patch sys.modules."""
    cmds_mock = MagicMock()
    mel_mock = MagicMock()

    # ── scene mocks ────────────────────────────────────────────────────────
    cmds_mock.file.return_value = "/scene/test.mb"
    cmds_mock.ls.return_value = ["|pSphere1", "|pCube1"]
    cmds_mock.objExists.return_value = True
    cmds_mock.objectType.return_value = "transform"
    cmds_mock.listRelatives.return_value = []
    cmds_mock.getAttr.return_value = [(0.0, 0.0, 0.0)]
    cmds_mock.currentUnit.return_value = "film"
    cmds_mock.about.return_value = "2025"
    cmds_mock.rename.side_effect = lambda obj, name: name

    # ── camera mocks ───────────────────────────────────────────────────────
    cmds_mock.spaceLocator.return_value = ["locator1"]
    cmds_mock.move.return_value = None

    return cmds_mock, mel_mock


def _patch_maya(cmds_mock, mel_mock):
    return patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, mel=mel_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.mel": mel_mock,
            "maya.utils": MagicMock(),
        },
    )


def _reload():
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


# ===========================================================================
# TestGetSceneInfo
# ===========================================================================


class TestGetSceneInfo:
    def test_returns_nodes_list(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.return_value = ["|pSphere1", "|pCube1"]
        cmds_mock.listRelatives.return_value = []
        cmds_mock.getAttr.return_value = [(1.0, 2.0, 3.0)]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import get_scene_info

            result = get_scene_info()

        assert result["success"] is True
        assert "nodes" in result["context"]
        assert result["context"]["count"] == 2

    def test_nodes_contain_transform_info(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.return_value = ["|pSphere1"]
        cmds_mock.listRelatives.return_value = None
        cmds_mock.getAttr.return_value = [(0.0, 0.0, 0.0)]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import get_scene_info

            result = get_scene_info(include_transforms=True)

        assert result["success"] is True
        node = result["context"]["nodes"][0]
        assert "translate" in node
        assert "rotate" in node
        assert "scale" in node

    def test_no_transform_info_when_disabled(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.return_value = ["|pSphere1"]
        cmds_mock.listRelatives.return_value = None

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import get_scene_info

            result = get_scene_info(include_transforms=False)

        assert result["success"] is True
        node = result["context"]["nodes"][0]
        assert "translate" not in node

    def test_empty_scene(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.return_value = []

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import get_scene_info

            result = get_scene_info()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_import_error_returns_failure(self):
        _reload()
        with patch.dict(sys.modules, {"maya.cmds": None}):
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            sys.modules["maya.cmds"] = None  # type: ignore[assignment]
            from dcc_mcp_maya.actions.scene import get_scene_info

            result = get_scene_info()
        assert result["success"] is False


# ===========================================================================
# TestExportScene
# ===========================================================================


class TestExportScene:
    def test_export_returns_file_path(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.file.return_value = "/out/scene.mb"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import export_scene

            result = export_scene("/out/scene.mb")

        assert result["success"] is True
        assert result["context"]["file_path"] == "/out/scene.mb"

    def test_export_ascii_type(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.file.return_value = "/out/scene.ma"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import export_scene

            result = export_scene("/out/scene.ma", file_type="mayaAscii")

        assert result["success"] is True
        assert result["context"]["file_type"] == "mayaAscii"

    def test_export_exception_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.file.side_effect = RuntimeError("disk full")

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import export_scene

            result = export_scene("/out/scene.mb")

        assert result["success"] is False


# ===========================================================================
# TestSetFrameRate
# ===========================================================================


class TestSetFrameRate:
    def test_set_valid_fps_film(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.currentUnit.return_value = "film"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import set_frame_rate

            result = set_frame_rate("film")

        assert result["success"] is True
        assert result["context"]["fps"] == "film"

    def test_set_valid_fps_ntsc(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.currentUnit.return_value = "ntsc"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import set_frame_rate

            result = set_frame_rate("ntsc")

        assert result["success"] is True

    def test_invalid_fps_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import set_frame_rate

            result = set_frame_rate("not_a_fps")

        assert result["success"] is False

    def test_cmds_exception_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.currentUnit.side_effect = RuntimeError("bad call")

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import set_frame_rate

            result = set_frame_rate("film")

        assert result["success"] is False


# ===========================================================================
# TestListCameras
# ===========================================================================


class TestListCameras:
    def test_returns_camera_list(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.return_value = ["perspShape", "myCameraShape"]
        cmds_mock.listRelatives.side_effect = lambda shape, **kw: (
            ["persp"] if shape == "perspShape" else ["myCamera"]
        )
        cmds_mock.getAttr.return_value = 35.0

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import list_cameras

            result = list_cameras(include_default=True)

        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_exclude_default_cameras(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        # All returned shapes are default cameras → should be filtered out
        cmds_mock.ls.return_value = ["perspShape", "topShape"]
        cmds_mock.listRelatives.side_effect = lambda shape, **kw: (
            ["persp"] if shape == "perspShape" else ["top"]
        )
        cmds_mock.getAttr.return_value = 35.0

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import list_cameras

            result = list_cameras(include_default=False)

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_no_cameras_returns_empty(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.return_value = []

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import list_cameras

            result = list_cameras()

        assert result["success"] is True
        assert result["context"]["cameras"] == []

    def test_exception_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.ls.side_effect = RuntimeError("oops")

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import list_cameras

            result = list_cameras()

        assert result["success"] is False


# ===========================================================================
# TestCreateLocator
# ===========================================================================


class TestCreateLocator:
    def test_create_default_locator(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.spaceLocator.return_value = ["locator1"]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import create_locator

            result = create_locator()

        assert result["success"] is True
        assert result["context"]["object_name"] == "locator1"

    def test_create_named_locator(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.spaceLocator.return_value = ["myLocator"]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import create_locator

            result = create_locator(name="myLocator")

        assert result["success"] is True
        assert result["context"]["object_name"] == "myLocator"

    def test_create_locator_with_position(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.spaceLocator.return_value = ["locator1"]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import create_locator

            result = create_locator(position=[1.0, 2.0, 3.0])

        assert result["success"] is True
        assert result["context"]["position"] == [1.0, 2.0, 3.0]
        cmds_mock.move.assert_called_once_with(1.0, 2.0, 3.0, "locator1")

    def test_create_locator_no_position_skips_move(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.spaceLocator.return_value = ["locator1"]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import create_locator

            result = create_locator()

        cmds_mock.move.assert_not_called()
        assert result["success"] is True

    def test_exception_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.spaceLocator.side_effect = RuntimeError("no space")

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.scene import create_locator

            result = create_locator()

        assert result["success"] is False


# ===========================================================================
# TestCreateJoint
# ===========================================================================


class TestCreateJoint:
    def test_create_basic_joint(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.joint.return_value = "joint1"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_joint

            result = create_joint()

        assert result["success"] is True
        assert result["context"]["object_name"] == "joint1"

    def test_create_named_joint(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.joint.return_value = "hip_jnt"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_joint

            result = create_joint(name="hip_jnt", position=[0.0, 10.0, 0.0])

        assert result["success"] is True
        assert result["context"]["position"] == [0.0, 10.0, 0.0]

    def test_create_joint_with_parent(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.objExists.return_value = True
        cmds_mock.joint.return_value = "knee_jnt"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_joint

            result = create_joint(name="knee_jnt", parent="hip_jnt")

        assert result["success"] is True
        assert result["context"]["parent"] == "hip_jnt"
        cmds_mock.select.assert_called_with("hip_jnt", replace=True)

    def test_missing_parent_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.objExists.return_value = False

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_joint

            result = create_joint(parent="nonexistent")

        assert result["success"] is False

    def test_invalid_position_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_joint

            result = create_joint(position=[1.0, 2.0])  # only 2 values

        assert result["success"] is False

    def test_exception_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.joint.side_effect = RuntimeError("joint error")

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_joint

            result = create_joint()

        assert result["success"] is False


# ===========================================================================
# TestCreateCurve
# ===========================================================================


class TestCreateCurve:
    def test_create_default_curve(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.curve.return_value = "curve1"

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_curve

            result = create_curve()

        assert result["success"] is True
        assert result["context"]["object_name"] == "curve1"

    def test_create_linear_curve(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.curve.return_value = "curve1"
        pts = [[0, 0, 0], [1, 0, 0], [2, 0, 0]]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_curve

            result = create_curve(points=pts, degree=1)

        assert result["success"] is True
        assert result["context"]["degree"] == 1
        assert result["context"]["point_count"] == 3

    def test_too_few_points_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_curve

            # degree=3 requires at least 4 points; only 2 given
            result = create_curve(points=[[0, 0, 0], [1, 0, 0]], degree=3)

        assert result["success"] is False

    def test_named_curve(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.curve.return_value = "myCurve"
        pts = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_curve

            result = create_curve(points=pts, name="myCurve")

        assert result["success"] is True
        assert result["context"]["object_name"] == "myCurve"

    def test_periodic_curve(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.curve.return_value = "circle1"
        pts = [[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]]

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_curve

            result = create_curve(points=pts, degree=3, periodic=True)

        assert result["success"] is True
        assert result["context"]["periodic"] is True

    def test_exception_returns_error(self):
        _reload()
        cmds_mock, mel_mock = _mock_maya()
        cmds_mock.curve.side_effect = RuntimeError("bad curve")

        with _patch_maya(cmds_mock, mel_mock):
            from dcc_mcp_maya.actions.rigging import create_curve

            result = create_curve(points=[[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]])

        assert result["success"] is False


# ===========================================================================
# TestRegisterAllWithRound3
# ===========================================================================


class TestRegisterAllRound3:
    def test_total_actions_at_least_46(self):
        _reload()
        from dcc_mcp_core import ActionRegistry

        from dcc_mcp_maya.actions import register_all

        reg = ActionRegistry()
        register_all(reg)
        actions = reg.list_actions()
        # 39 (prev) + 7 new = 46
        assert len(actions) >= 46

    def test_new_actions_registered(self):
        _reload()
        from dcc_mcp_core import ActionRegistry

        from dcc_mcp_maya.actions import register_all

        reg = ActionRegistry()
        register_all(reg)
        names = {a["name"] for a in reg.list_actions()}
        for expected in (
            "get_scene_info",
            "export_scene",
            "set_frame_rate",
            "list_cameras",
            "create_locator",
            "create_joint",
            "create_curve",
        ):
            assert expected in names, "Missing action: {}".format(expected)


# ===========================================================================
# ImportError branch coverage for rigging + new scene actions
# ===========================================================================


def _no_maya_modules():
    """Return a patch that makes 'maya.cmds' unavailable (None → ImportError)."""
    return patch.dict(sys.modules, {"maya": None, "maya.cmds": None})


class TestImportErrorBranches:
    """Ensure every new action gracefully handles a missing maya.cmds."""

    def _reload_and_null_maya(self):
        _reload()
        # Set modules to None so 'import maya.cmds' raises ImportError
        sys.modules["maya"] = None  # type: ignore[assignment]
        sys.modules["maya.cmds"] = None  # type: ignore[assignment]

    def test_export_scene_no_maya(self):
        self._reload_and_null_maya()
        from dcc_mcp_maya.actions.scene import export_scene

        result = export_scene("/tmp/test.mb")
        assert result["success"] is False

    def test_set_frame_rate_no_maya(self):
        self._reload_and_null_maya()
        from dcc_mcp_maya.actions.scene import set_frame_rate

        result = set_frame_rate("film")
        assert result["success"] is False

    def test_list_cameras_no_maya(self):
        self._reload_and_null_maya()
        from dcc_mcp_maya.actions.scene import list_cameras

        result = list_cameras()
        assert result["success"] is False

    def test_create_locator_no_maya(self):
        self._reload_and_null_maya()
        from dcc_mcp_maya.actions.scene import create_locator

        result = create_locator()
        assert result["success"] is False

    def test_create_joint_no_maya(self):
        self._reload_and_null_maya()
        from dcc_mcp_maya.actions.rigging import create_joint

        result = create_joint()
        assert result["success"] is False

    def test_create_curve_no_maya(self):
        self._reload_and_null_maya()
        from dcc_mcp_maya.actions.rigging import create_curve

        result = create_curve()
        assert result["success"] is False
