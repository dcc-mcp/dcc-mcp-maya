"""Tests for Maya render, import and export actions (maya.cmds mocked)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


@pytest.fixture()
def mock_maya():
    cmds_mock = MagicMock()
    cmds_mock.currentTime.return_value = 1.0
    cmds_mock.file.return_value = "/tmp/exported.fbx"
    cmds_mock.ls.return_value = ["pSphere1"]

    with patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.utils": MagicMock(),
        },
    ):
        yield cmds_mock


def _reload():
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


def _no_maya():
    return patch.dict(sys.modules, {"maya": None, "maya.cmds": None})


# ---------------------------------------------------------------------------
# set_render_settings
# ---------------------------------------------------------------------------

class TestSetRenderSettings:
    def test_default_resolution(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.render import set_render_settings

        result = set_render_settings()
        assert result["success"] is True
        assert result["context"]["width"] == 1920
        assert result["context"]["height"] == 1080

    def test_with_frame_range_and_renderer(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.render import set_render_settings

        result = set_render_settings(
            width=1280, height=720,
            start_frame=1.0, end_frame=100.0,
            renderer="arnold",
        )
        assert result["success"] is True
        assert result["context"]["start_frame"] == 1.0
        assert result["context"]["renderer"] == "arnold"

    def test_exception(self, mock_maya):
        _reload()
        mock_maya.setAttr.side_effect = RuntimeError("locked node")
        from dcc_mcp_maya.actions.render import set_render_settings

        result = set_render_settings()
        assert result["success"] is False

    def test_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.render import set_render_settings

            result = set_render_settings()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# capture_viewport
# ---------------------------------------------------------------------------

class TestCaptureViewport:
    def _make_fake_png(self, prefix, frame):
        """Write a tiny valid-ish PNG to the expected playblast output path."""
        # 1x1 transparent PNG bytes (minimal valid PNG)
        PNG_1X1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
            b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        padded_path = "{}.{}.png".format(prefix, str(int(frame)).zfill(4))
        with open(padded_path, "wb") as fh:
            fh.write(PNG_1X1)
        return padded_path

    def test_capture_viewport_success(self, mock_maya):
        _reload()
        mock_maya.currentTime.return_value = 1.0

        # We need to intercept the playblast call and create the output file
        original_tmpfile = tempfile.NamedTemporaryFile

        created_paths = []

        def fake_playblast(**kwargs):
            prefix = kwargs["filename"]
            frame = kwargs["frame"][0]
            path = self._make_fake_png(prefix, frame)
            created_paths.append(path)

        mock_maya.playblast.side_effect = fake_playblast

        with patch("dcc_mcp_maya.actions.render.tempfile.NamedTemporaryFile", original_tmpfile):
            from dcc_mcp_maya.actions.render import capture_viewport

            result = capture_viewport(width=320, height=240, frame=1.0)

        assert result["success"] is True
        assert "image" in result["context"]
        # Verify it is valid base64
        img_data = base64.b64decode(result["context"]["image"])
        assert len(img_data) > 0

    def test_capture_viewport_exception(self, mock_maya):
        _reload()
        mock_maya.playblast.side_effect = RuntimeError("viewport error")
        from dcc_mcp_maya.actions.render import capture_viewport

        result = capture_viewport()
        assert result["success"] is False

    def test_capture_viewport_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.render import capture_viewport

            result = capture_viewport()
        assert result["success"] is False

    def test_capture_viewport_default_frame(self, mock_maya):
        """When frame=None, currentTime is queried."""
        _reload()
        mock_maya.currentTime.return_value = 5.0
        mock_maya.playblast.side_effect = RuntimeError("stop early")
        from dcc_mcp_maya.actions.render import capture_viewport

        result = capture_viewport()
        # playblast will fail (we stop it early), but currentTime was called
        mock_maya.currentTime.assert_called_with(query=True)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# import_file
# ---------------------------------------------------------------------------

class TestImportFile:
    def test_import_file_basic(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = ["imported_node1"]
        from dcc_mcp_maya.actions.render import import_file

        result = import_file("/path/to/model.fbx")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["file_path"] == "/path/to/model.fbx"

    def test_import_file_with_namespace(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.render import import_file

        result = import_file("/path/to/model.fbx", namespace="ns1")
        assert result["success"] is True
        call_kwargs = mock_maya.file.call_args[1]
        assert call_kwargs.get("namespace") == "ns1"

    def test_import_file_merge_namespaces(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.render import import_file

        result = import_file("/path/to/model.fbx", merge_namespaces=True)
        assert result["success"] is True
        call_kwargs = mock_maya.file.call_args[1]
        assert call_kwargs.get("mergeNamespacesOnClash") is True

    def test_import_file_exception(self, mock_maya):
        _reload()
        mock_maya.file.side_effect = RuntimeError("file not found")
        from dcc_mcp_maya.actions.render import import_file

        result = import_file("/nonexistent.fbx")
        assert result["success"] is False

    def test_import_file_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.render import import_file

            result = import_file("/path/to/model.fbx")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# export_selection
# ---------------------------------------------------------------------------

class TestExportSelection:
    def test_export_selection_fbx(self, mock_maya):
        _reload()
        mock_maya.file.return_value = "/tmp/out.fbx"
        from dcc_mcp_maya.actions.render import export_selection

        result = export_selection("/tmp/out.fbx")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/tmp/out.fbx"

    def test_export_selection_obj(self, mock_maya):
        _reload()
        mock_maya.file.return_value = "/tmp/out.obj"
        from dcc_mcp_maya.actions.render import export_selection

        result = export_selection("/tmp/out.obj", file_type="OBJexport")
        assert result["success"] is True
        assert result["context"]["file_type"] == "OBJexport"

    def test_export_selection_exception(self, mock_maya):
        _reload()
        mock_maya.file.side_effect = RuntimeError("nothing selected")
        from dcc_mcp_maya.actions.render import export_selection

        result = export_selection("/tmp/out.fbx")
        assert result["success"] is False

    def test_export_selection_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.render import export_selection

            result = export_selection("/tmp/out.fbx")
        assert result["success"] is False
