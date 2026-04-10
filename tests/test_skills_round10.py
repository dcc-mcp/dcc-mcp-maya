"""Round 10: unit tests for maya-render Skill scripts.

Covers all 8 scripts under skills/maya-render/scripts/:
  - set_render_settings
  - get_render_settings
  - get_scene_render_stats
  - set_render_quality
  - capture_viewport
  - playblast
  - import_file
  - export_selection

All Maya dependencies are mocked via sys.modules.
"""

# Import built-in modules
import base64
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Load a skill script by path, returning its module."""
    path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(script_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_result(success: bool, message: str = "ok", **ctx):
    """Create a minimal ActionResultModel-like mock with .to_dict()."""
    obj = MagicMock()
    obj.success = success
    obj.message = message
    data = {"success": success, "message": message, "context": ctx}
    obj.to_dict.return_value = data
    return obj


def _patch_maya(extra_attrs=None):
    """Return a context-manager that patches maya.cmds into sys.modules."""
    mock_cmds = MagicMock()
    # sensible defaults
    mock_cmds.getAttr.side_effect = lambda attr, **kw: {
        "defaultResolution.width": 1920,
        "defaultResolution.height": 1080,
        "defaultRenderGlobals.startFrame": 1.0,
        "defaultRenderGlobals.endFrame": 24.0,
        "defaultRenderGlobals.currentRenderer": "mayaSoftware",
        "defaultRenderGlobals.imageFormat": 32,
        "defaultRenderGlobals.imageFilePrefix": "/renders/",
    }.get(attr, 0)
    mock_cmds.currentTime.return_value = 1.0
    mock_cmds.objExists.return_value = True
    mock_cmds.file.return_value = "/some/path.fbx"
    mock_cmds.ls.return_value = ["node1", "node2"]
    if extra_attrs:
        for k, v in extra_attrs.items():
            setattr(mock_cmds, k, v)

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    patches = {
        "maya": mock_maya,
        "maya.cmds": mock_cmds,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    return patches, mock_cmds


# ===========================================================================
# set_render_settings
# ===========================================================================

class TestSetRenderSettings:
    """Tests for maya-render/scripts/set_render_settings.py."""

    def _run(self, mock_cmds, **kwargs):
        patches, _ = _patch_maya()
        patches["maya.cmds"] = mock_cmds
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            return mod.set_render_settings(**kwargs)
        finally:
            for k in patches:
                sys.modules.pop(k, None)

    def test_set_width_and_height(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(width=1280, height=720)
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call("defaultResolution.width", 1280)
        mock_cmds.setAttr.assert_any_call("defaultResolution.height", 720)

    def test_set_renderer(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(renderer="arnold")
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call(
            "defaultRenderGlobals.currentRenderer", "arnold", type="string"
        )

    def test_set_frame_range(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(start_frame=1, end_frame=50)
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True

    def test_set_image_format_png(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(image_format="png")
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call("defaultRenderGlobals.imageFormat", 32)

    def test_set_image_format_exr(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(image_format="exr")
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call("defaultRenderGlobals.imageFormat", 40)

    def test_no_settings_returns_error(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is False
        assert "No settings" in result["message"]

    def test_set_output_path(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(output_path="/renders/shot001")
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True

    def test_exception_returns_error(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.setAttr.side_effect = RuntimeError("setAttr failed")
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(width=100)
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is False


# ===========================================================================
# get_render_settings
# ===========================================================================

class TestGetRenderSettings:
    """Tests for maya-render/scripts/get_render_settings.py."""

    def test_basic_success(self):
        patches, mock_cmds = _patch_maya()
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_render_settings")
            result = mod.get_render_settings()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        assert "mayaSoftware" in result["message"]

    def test_returns_format_name(self):
        patches, mock_cmds = _patch_maya()
        # format code 40 → exr
        mock_cmds.getAttr.side_effect = lambda attr, **kw: {
            "defaultResolution.width": 1920,
            "defaultResolution.height": 1080,
            "defaultRenderGlobals.startFrame": 1.0,
            "defaultRenderGlobals.endFrame": 100.0,
            "defaultRenderGlobals.currentRenderer": "arnold",
            "defaultRenderGlobals.imageFormat": 40,
            "defaultRenderGlobals.imageFilePrefix": "",
        }.get(attr, 0)
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_render_settings")
            result = mod.get_render_settings()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        assert result["context"]["image_format"] == "exr"

    def test_unknown_format_code(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.getAttr.side_effect = lambda attr, **kw: {
            "defaultResolution.width": 800,
            "defaultResolution.height": 600,
            "defaultRenderGlobals.startFrame": 1.0,
            "defaultRenderGlobals.endFrame": 10.0,
            "defaultRenderGlobals.currentRenderer": "vray",
            "defaultRenderGlobals.imageFormat": 99,
            "defaultRenderGlobals.imageFilePrefix": None,
        }.get(attr, 0)
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_render_settings")
            result = mod.get_render_settings()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        # unknown code rendered as string
        assert result["context"]["image_format"] == "99"

    def test_exception_returns_error(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.getAttr.side_effect = RuntimeError("no node")
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_render_settings")
            result = mod.get_render_settings()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is False


# ===========================================================================
# get_scene_render_stats
# ===========================================================================

class TestGetSceneRenderStats:
    """Tests for maya-render/scripts/get_scene_render_stats.py."""

    def test_basic_success(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.objExists.return_value = True
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_scene_render_stats")
            result = mod.get_scene_render_stats()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        assert "mayaSoftware" in result["message"]

    def test_quality_attrs_queried(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.side_effect = lambda attr, **kw: {
            "defaultResolution.width": 1920,
            "defaultResolution.height": 1080,
            "defaultRenderGlobals.startFrame": 1.0,
            "defaultRenderGlobals.endFrame": 24.0,
            "defaultRenderGlobals.currentRenderer": "mayaSoftware",
            "defaultRenderGlobals.imageFilePrefix": "",
        }.get(attr, 4)
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_scene_render_stats")
            result = mod.get_scene_render_stats()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        assert "quality" in result["context"]

    def test_quality_attrs_skipped_when_not_exist(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.objExists.return_value = False
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_scene_render_stats")
            result = mod.get_scene_render_stats()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        assert result["context"]["quality"] == {}

    def test_exception_returns_error(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.getAttr.side_effect = RuntimeError("crashed")
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "get_scene_render_stats")
            result = mod.get_scene_render_stats()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is False


# ===========================================================================
# set_render_quality
# ===========================================================================

class TestSetRenderQuality:
    """Tests for maya-render/scripts/set_render_quality.py."""

    def _run(self, preset="medium", objExists=True):
        patches, mock_cmds = _patch_maya()
        mock_cmds.objExists.return_value = objExists
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_quality")
            return mod.set_render_quality(preset=preset), mock_cmds
        finally:
            for k in patches:
                sys.modules.pop(k, None)

    def test_medium_preset(self):
        result, _ = self._run("medium")
        assert result["success"] is True
        assert "medium" in result["message"]

    def test_low_preset(self):
        result, _ = self._run("low")
        assert result["success"] is True

    def test_high_preset(self):
        result, _ = self._run("high")
        assert result["success"] is True

    def test_invalid_preset(self):
        result, _ = self._run("ultra")
        assert result["success"] is False
        assert "ultra" in result["message"]

    def test_attrs_not_set_when_node_missing(self):
        result, mock_cmds = self._run("high", objExists=False)
        assert result["success"] is True
        mock_cmds.setAttr.assert_not_called()

    def test_exception_returns_error(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.setAttr.side_effect = RuntimeError("locked")
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_quality")
            result = mod.set_render_quality(preset="low")
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is False

    def test_case_insensitive_preset(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.objExists.return_value = True
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "set_render_quality")
            result = mod.set_render_quality(preset="HIGH")
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True


# ===========================================================================
# capture_viewport
# ===========================================================================

class TestCaptureViewport:
    """Tests for maya-render/scripts/capture_viewport.py."""

    def _run_with_tempfile(self, frame=1.0, width=1920, height=1080, raise_exc=None):
        """Run capture_viewport with mocked tempfile/os/playblast."""
        patches, mock_cmds = _patch_maya()
        mock_cmds.currentTime.return_value = frame

        fake_img = b"\x89PNG\r\nfake"
        fake_prefix = "/tmp/mcp_test"

        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "capture_viewport")
            with patch("tempfile.NamedTemporaryFile") as mock_ntf, \
                 patch("os.path.exists") as mock_exists, \
                 patch("builtins.open", create=True) as mock_open, \
                 patch("os.unlink"):
                # tempfile mock
                ntf_inst = MagicMock()
                ntf_inst.__enter__ = lambda s: ntf_inst
                ntf_inst.__exit__ = MagicMock(return_value=False)
                ntf_inst.name = fake_prefix + ".png"
                mock_ntf.return_value = ntf_inst

                mock_exists.return_value = True

                # open mock
                fh_mock = MagicMock()
                fh_mock.__enter__ = lambda s: fh_mock
                fh_mock.__exit__ = MagicMock(return_value=False)
                fh_mock.read.return_value = fake_img
                mock_open.return_value = fh_mock

                if raise_exc:
                    mock_cmds.playblast.side_effect = raise_exc

                result = mod.capture_viewport(width=width, height=height, frame=frame)
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        return result, fake_img

    def test_success_returns_base64_image(self):
        result, fake_img = self._run_with_tempfile()
        assert result["success"] is True
        decoded = base64.b64decode(result["context"]["image"])
        assert decoded == fake_img

    def test_frame_defaults_to_current_time(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.currentTime.return_value = 5.0
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "capture_viewport")
            with patch("tempfile.NamedTemporaryFile") as mock_ntf, \
                 patch("os.path.exists", return_value=True), \
                 patch("builtins.open", create=True) as mock_open, \
                 patch("os.unlink"):
                ntf_inst = MagicMock()
                ntf_inst.__enter__ = lambda s: ntf_inst
                ntf_inst.__exit__ = MagicMock(return_value=False)
                ntf_inst.name = "/tmp/cv.png"
                mock_ntf.return_value = ntf_inst
                fh = MagicMock()
                fh.__enter__ = lambda s: fh
                fh.__exit__ = MagicMock(return_value=False)
                fh.read.return_value = b"data"
                mock_open.return_value = fh
                result = mod.capture_viewport()
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        assert result["context"]["frame"] == 5.0

    def test_playblast_exception_returns_error(self):
        result, _ = self._run_with_tempfile(raise_exc=RuntimeError("playblast boom"))
        assert result["success"] is False

    def test_custom_dimensions(self):
        result, _ = self._run_with_tempfile(width=640, height=480)
        assert result["success"] is True
        assert result["context"]["width"] == 640
        assert result["context"]["height"] == 480


# ===========================================================================
# playblast
# ===========================================================================

class TestPlayblast:
    """Tests for maya-render/scripts/playblast.py."""

    def _run(self, frame=1.0, width=1920, height=1080, percent=100,
             png_exists=True, raise_exc=None):
        patches, mock_cmds = _patch_maya()
        mock_cmds.currentTime.return_value = frame
        fake_img = b"\x89PNG\r\nfakeblast"

        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "playblast")
            with patch("tempfile.NamedTemporaryFile") as mock_ntf, \
                 patch("os.path.exists") as mock_exists, \
                 patch("builtins.open", create=True) as mock_open, \
                 patch("os.unlink"):
                ntf_inst = MagicMock()
                ntf_inst.__enter__ = lambda s: ntf_inst
                ntf_inst.__exit__ = MagicMock(return_value=False)
                ntf_inst.name = "/tmp/mcp_blast_.png"
                mock_ntf.return_value = ntf_inst

                mock_exists.side_effect = lambda p: png_exists

                fh = MagicMock()
                fh.__enter__ = lambda s: fh
                fh.__exit__ = MagicMock(return_value=False)
                fh.read.return_value = fake_img
                mock_open.return_value = fh

                if raise_exc:
                    mock_cmds.playblast.side_effect = raise_exc

                result = mod.playblast(
                    width=width, height=height, frame=frame, percent=percent
                )
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        return result, fake_img

    def test_success(self):
        result, fake_img = self._run()
        assert result["success"] is True
        decoded = base64.b64decode(result["context"]["image"])
        assert decoded == fake_img

    def test_prompt_present(self):
        result, _ = self._run()
        assert result["success"] is True
        # prompt is passed through success_result
        assert "message" in result

    def test_file_not_found_returns_error(self):
        result, _ = self._run(png_exists=False)
        assert result["success"] is False
        assert "not found" in result["message"].lower() or "playblast" in result["message"].lower()

    def test_exception_returns_error(self):
        result, _ = self._run(raise_exc=RuntimeError("headless not supported"))
        assert result["success"] is False

    def test_custom_percent(self):
        patches, mock_cmds = _patch_maya()
        mock_cmds.currentTime.return_value = 1.0
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "playblast")
            with patch("tempfile.NamedTemporaryFile") as mock_ntf, \
                 patch("os.path.exists", return_value=True), \
                 patch("builtins.open", create=True) as mock_open, \
                 patch("os.unlink"):
                ntf_inst = MagicMock()
                ntf_inst.__enter__ = lambda s: ntf_inst
                ntf_inst.__exit__ = MagicMock(return_value=False)
                ntf_inst.name = "/tmp/p.png"
                mock_ntf.return_value = ntf_inst
                fh = MagicMock()
                fh.__enter__ = lambda s: fh
                fh.__exit__ = MagicMock(return_value=False)
                fh.read.return_value = b"img"
                mock_open.return_value = fh
                result = mod.playblast(percent=50)
        finally:
            for k in patches:
                sys.modules.pop(k, None)
        assert result["success"] is True
        call_kwargs = mock_cmds.playblast.call_args[1]
        assert call_kwargs["percent"] == 50


# ===========================================================================
# import_file
# ===========================================================================

class TestImportFile:
    """Tests for maya-render/scripts/import_file.py."""

    def _run(self, file_path="/tmp/test.fbx", namespace=None,
             merge_namespaces=False, ls_return=None, raise_exc=None):
        patches, mock_cmds = _patch_maya()
        mock_cmds.ls.return_value = ls_return if ls_return is not None else ["node1"]
        if raise_exc:
            mock_cmds.file.side_effect = raise_exc
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "import_file")
            return mod.import_file(
                file_path=file_path,
                namespace=namespace,
                merge_namespaces=merge_namespaces,
            ), mock_cmds
        finally:
            for k in patches:
                sys.modules.pop(k, None)

    def test_basic_import(self):
        result, mock_cmds = self._run(ls_return=["mesh1", "mesh2"])
        assert result["success"] is True
        assert result["context"]["count"] == 2
        mock_cmds.file.assert_called_once()

    def test_namespace_passed(self):
        result, mock_cmds = self._run(namespace="my_ns")
        assert result["success"] is True
        call_kwargs = mock_cmds.file.call_args[1]
        assert call_kwargs.get("namespace") == "my_ns"

    def test_merge_namespaces(self):
        result, mock_cmds = self._run(merge_namespaces=True)
        assert result["success"] is True
        call_kwargs = mock_cmds.file.call_args[1]
        assert call_kwargs.get("mergeNamespacesOnClash") is True

    def test_empty_import(self):
        result, _ = self._run(ls_return=[])
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_exception_returns_error(self):
        result, _ = self._run(raise_exc=RuntimeError("file not found"))
        assert result["success"] is False
        assert "file not found" in result["message"].lower() or "failed" in result["message"].lower()


# ===========================================================================
# export_selection
# ===========================================================================

class TestExportSelection:
    """Tests for maya-render/scripts/export_selection.py."""

    def _run(self, file_path="/tmp/out.fbx", file_type="FBX export",
             file_return=None, raise_exc=None):
        patches, mock_cmds = _patch_maya()
        mock_cmds.file.return_value = file_return or file_path
        if raise_exc:
            mock_cmds.file.side_effect = raise_exc
        for k, v in patches.items():
            sys.modules[k] = v
        try:
            mod = _load_script("maya-render", "export_selection")
            return mod.export_selection(file_path=file_path, file_type=file_type), mock_cmds
        finally:
            for k in patches:
                sys.modules.pop(k, None)

    def test_basic_export(self):
        result, mock_cmds = self._run()
        assert result["success"] is True
        call_kwargs = mock_cmds.file.call_args[1]
        assert call_kwargs.get("exportSelected") is True
        assert call_kwargs.get("force") is True

    def test_custom_file_type(self):
        result, mock_cmds = self._run(file_type="OBJexport")
        assert result["success"] is True
        call_kwargs = mock_cmds.file.call_args[1]
        assert call_kwargs.get("type") == "OBJexport"

    def test_result_contains_file_path(self):
        result, _ = self._run(file_path="/renders/selection.fbx")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/renders/selection.fbx"

    def test_exception_returns_error(self):
        result, _ = self._run(raise_exc=RuntimeError("nothing selected"))
        assert result["success"] is False

    def test_maya_ascii_export(self):
        result, mock_cmds = self._run(file_type="mayaAscii")
        assert result["success"] is True
        call_kwargs = mock_cmds.file.call_args[1]
        assert call_kwargs["type"] == "mayaAscii"
