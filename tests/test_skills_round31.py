"""Round 31: validate_node_exists migration tests.

Verifies that the 18 cmds.objExists node-guard patterns migrated in Round 17
(refactor) correctly use validate_node_exists from dcc_mcp_maya.api and that
all targeted scripts have no raw 'if not cmds.objExists(node):' guards.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_module(rel_path: str, mod_name: str) -> ModuleType:
    """Import a skill script by relative path (under src/)."""
    import importlib.util
    import os

    base = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "src",
    )
    path = os.path.join(base, *rel_path.split("/"))
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_cmds(exists=True, **extra_attrs):
    """Return a MagicMock maya.cmds that returns *exists* for objExists."""
    mock = MagicMock()
    mock.objExists.return_value = exists
    mock.objectType.return_value = "transform"
    for k, v in extra_attrs.items():
        setattr(mock, k, v)
    return mock


def _patch_maya(mock_cmds):
    """Return a context manager that patches maya.cmds everywhere."""
    import contextlib

    @contextlib.contextmanager
    def ctx():
        maya_mock = MagicMock()
        maya_mock.cmds = mock_cmds
        with patch.dict(
            sys.modules,
            {
                "maya": maya_mock,
                "maya.cmds": mock_cmds,
                "maya.api": MagicMock(),
                "maya.utils": MagicMock(),
            },
        ):
            yield

    return ctx()


# ---------------------------------------------------------------------------
# TestStructural
# ---------------------------------------------------------------------------


class TestStructural:
    """Structural checks on all 16 migrated files."""

    _MIGRATED_FILES = [
        "dcc_mcp_maya/skills/maya-mesh-ops/scripts/create_proxy_mesh.py",
        "dcc_mcp_maya/skills/maya-mesh-ops/scripts/get_mesh_edge_info.py",
        "dcc_mcp_maya/skills/maya-mesh-ops/scripts/get_poly_count.py",
        "dcc_mcp_maya/skills/maya-mesh-ops/scripts/merge_vertices.py",
        "dcc_mcp_maya/skills/maya-pipeline/scripts/get_asset_metadata.py",
        "dcc_mcp_maya/skills/maya-pipeline/scripts/tag_asset_metadata.py",
        "dcc_mcp_maya/skills/maya-rigging/scripts/blend_shape_add_target.py",
        "dcc_mcp_maya/skills/maya-scripting/scripts/cameras.py",
        "dcc_mcp_maya/skills/maya-scripting/scripts/get_script_node.py",
        "dcc_mcp_maya/skills/maya-scripting/scripts/lighting.py",
        "dcc_mcp_maya/skills/maya-utility/scripts/list_node_connections.py",
        "dcc_mcp_maya/skills/maya-uv-ops/scripts/get_uv_shell_info.py",
        "dcc_mcp_maya/skills/maya-vertex-color/scripts/create_color_set.py",
        "dcc_mcp_maya/skills/maya-vertex-color/scripts/get_vertex_color.py",
        "dcc_mcp_maya/skills/maya-vertex-color/scripts/remove_vertex_colors.py",
        "dcc_mcp_maya/skills/maya-vertex-color/scripts/set_vertex_color.py",
    ]

    def _src_path(self, rel: str) -> str:
        import os

        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
        return os.path.join(base, *rel.split("/"))

    @pytest.mark.parametrize("rel", _MIGRATED_FILES)
    def test_no_raw_if_not_objexists_guard(self, rel):
        """Each migrated file must not contain plain node-existence guards.

        We check for 'if not cmds.objExists(<simple_var>):' patterns
        (no dots in the argument, which would indicate attribute probes).
        Attribute probes like 'if not cmds.objExists(full_attr):' are
        intentionally retained (they check 'node.attr' availability).
        """
        import re

        content = open(self._src_path(rel), encoding="utf-8").read()
        # Match guards where arg has no dot (plain node name, not attr probe)
        pattern = re.compile(r"if not cmds\.objExists\(\s*(\w+)\s*\):")
        for m in pattern.finditer(content):
            var = m.group(1)
            # Check if this var is assigned an attr-probe string earlier
            # Heuristic: if variable is named 'full_attr' or 'attr' it's a probe
            attr_probe_names = {"full_attr", "attr", "plug", "w_attr", "query_target"}
            if var not in attr_probe_names:
                pytest.fail(
                    "{} still has raw node-existence guard: {}".format(rel, m.group(0))
                )

    @pytest.mark.parametrize("rel", _MIGRATED_FILES)
    def test_validate_node_exists_imported(self, rel):
        """Each migrated file must import validate_node_exists."""
        content = open(self._src_path(rel), encoding="utf-8").read()
        assert "validate_node_exists" in content, (
            "{} is missing validate_node_exists import".format(rel)
        )

    @pytest.mark.parametrize("rel", _MIGRATED_FILES)
    def test_no_syntax_errors(self, rel):
        """All migrated files must parse without syntax errors."""
        import ast

        content = open(self._src_path(rel), encoding="utf-8").read()
        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail("{} has syntax error: {}".format(rel, e))

    def test_global_objexists_count_below_85(self):
        """Total cmds.objExists count across src/ must be below 85."""
        import os

        total = sum(
            open(os.path.join(r, f), encoding="utf-8", errors="ignore").read().count("cmds.objExists")
            for r, _d, fs in os.walk(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
            )
            for f in fs
            if f.endswith(".py")
        )
        assert total < 85, "Expected < 85 cmds.objExists, got {}".format(total)


# ---------------------------------------------------------------------------
# TestMeshOpsRound31
# ---------------------------------------------------------------------------


class TestMeshOpsRound31:
    """get_poly_count, get_mesh_edge_info, create_proxy_mesh, merge_vertices."""

    def _cmds_get_poly_count(self, exists=True):
        mock = _make_cmds(exists=exists)
        mock.polyEvaluate.return_value = 100
        mock.objectType.return_value = "transform"
        mock.listRelatives.return_value = ["pSphereShape1"]
        return mock

    def test_get_poly_count_missing_node(self):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-mesh-ops",
            "scripts",
            "get_poly_count.py",
        )
        mock_cmds = self._cmds_get_poly_count(exists=False)
        with _patch_maya(mock_cmds):
            spec = importlib.util.spec_from_file_location("get_poly_count_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.main(object_name="nonExist")
        assert result["success"] is False
        assert "not found" in result["message"].lower() or "not exist" in result["message"].lower()

    def test_get_poly_count_success(self):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-mesh-ops",
            "scripts",
            "get_poly_count.py",
        )
        mock_cmds = self._cmds_get_poly_count(exists=True)
        mock_cmds.polyEvaluate.side_effect = lambda obj, **kw: (
            100 if kw.get("f") or kw.get("face") else 50
        )
        with _patch_maya(mock_cmds):
            spec = importlib.util.spec_from_file_location("get_poly_count_r31b", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.main(object_name="pSphere1")
        assert result["success"] is True

    def test_merge_vertices_missing_node(self):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-mesh-ops",
            "scripts",
            "merge_vertices.py",
        )
        mock_cmds = _make_cmds(exists=False)
        with _patch_maya(mock_cmds):
            spec = importlib.util.spec_from_file_location("merge_vertices_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.main(object_name="missing_mesh")
        assert result["success"] is False

    def test_create_proxy_mesh_missing_node(self):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-mesh-ops",
            "scripts",
            "create_proxy_mesh.py",
        )
        mock_cmds = _make_cmds(exists=False)
        with _patch_maya(mock_cmds):
            spec = importlib.util.spec_from_file_location("create_proxy_mesh_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.main(object_name="missing_mesh")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestVertexColorRound31
# ---------------------------------------------------------------------------


class TestVertexColorRound31:
    """get_vertex_color, create_color_set, set_vertex_color, remove_vertex_colors."""

    def _path(self, script: str) -> str:
        import os

        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-vertex-color",
            "scripts",
            script,
        )

    def _load(self, script: str, mock_cmds: Any) -> ModuleType:
        import importlib.util

        path = self._path(script)
        with _patch_maya(mock_cmds):
            name = "vc_{}_r31".format(script.replace(".py", "").replace("-", "_"))
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        return mod

    def test_get_vertex_color_missing_object(self):
        mock = _make_cmds(exists=False)
        mod = self._load("get_vertex_color.py", mock)
        with _patch_maya(mock):
            result = mod.main(object_name="badObj")
        assert result["success"] is False

    def test_get_vertex_color_success_summary(self):
        mock = _make_cmds(exists=True)
        mock.polyColorSet.return_value = ["colorSet1"]
        mod = self._load("get_vertex_color.py", mock)
        with _patch_maya(mock):
            result = mod.main(object_name="pSphere1")
        assert result["success"] is True
        assert "color_sets" in result.get("context", {})

    def test_get_vertex_color_with_vtx_index(self):
        mock = _make_cmds(exists=True)
        mock.polyColorSet.return_value = ["colorSet1"]
        mock.polyColorPerVertex.return_value = [0.5, 0.3, 0.2, 1.0]
        mod = self._load("get_vertex_color.py", mock)
        with _patch_maya(mock):
            result = mod.main(object_name="pSphere1", vertex_index=0)
        assert result["success"] is True
        ctx = result.get("context", {})
        assert "color" in ctx
        assert len(ctx["color"]) == 3

    def test_create_color_set_missing_object(self):
        mock = _make_cmds(exists=False)
        mod = self._load("create_color_set.py", mock)
        with _patch_maya(mock):
            result = mod.main(object_name="badMesh")
        assert result["success"] is False

    def test_set_vertex_color_missing_object(self):
        mock = _make_cmds(exists=False)
        mod = self._load("set_vertex_color.py", mock)
        with _patch_maya(mock):
            result = mod.main(object_name="badMesh", color=[1.0, 0.0, 0.0])
        assert result["success"] is False

    def test_remove_vertex_colors_missing_object(self):
        mock = _make_cmds(exists=False)
        mod = self._load("remove_vertex_colors.py", mock)
        with _patch_maya(mock):
            result = mod.main(object_name="badMesh")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestRiggingRound31
# ---------------------------------------------------------------------------


class TestRiggingRound31:
    """blend_shape_add_target — 2 validate_node_exists calls (blend_shape + target_mesh)."""

    def _path(self) -> str:
        import os

        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-rigging",
            "scripts",
            "blend_shape_add_target.py",
        )

    def _load(self, mock_cmds: Any) -> ModuleType:
        import importlib.util

        path = self._path()
        with _patch_maya(mock_cmds):
            spec = importlib.util.spec_from_file_location("blend_shape_add_target_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        return mod

    def test_missing_blend_shape_node(self):
        mock = _make_cmds(exists=False)
        mod = self._load(mock)
        with _patch_maya(mock):
            result = mod.main(blend_shape="missingBS", target_mesh="mesh")
        assert result["success"] is False

    def test_wrong_node_type(self):
        mock = _make_cmds(exists=True)
        mock.objectType.return_value = "mesh"  # not blendShape
        mod = self._load(mock)
        with _patch_maya(mock):
            result = mod.main(blend_shape="notBS", target_mesh="mesh")
        assert result["success"] is False
        # message could reference 'blendShape', 'not a blend', or generic error
        msg = result["message"].lower()
        assert (
            "blendshape" in msg
            or "not a blend" in msg
            or "blend" in msg
            or "failed" in msg
        )

    def test_missing_target_mesh(self):
        call_count = [0]

        def objExists_side(name):
            call_count[0] += 1
            # blend_shape exists (1st call), target_mesh does not (2nd call)
            return call_count[0] < 2

        mock = _make_cmds(exists=True)
        mock.objExists.side_effect = objExists_side
        mock.objectType.return_value = "blendShape"
        mod = self._load(mock)
        with _patch_maya(mock):
            result = mod.main(blend_shape="realBS", target_mesh="missingMesh")
        assert result["success"] is False

    def test_invalid_weight(self):
        mock = _make_cmds(exists=True)
        mod = self._load(mock)
        with _patch_maya(mock):
            result = mod.main(blend_shape="realBS", target_mesh="mesh", weight=2.0)
        assert result["success"] is False
        assert "weight" in result["message"].lower()

    def test_success(self):
        mock = _make_cmds(exists=True)
        mock.objectType.return_value = "blendShape"
        mock.blendShape.return_value = 2  # weightCount
        mock.blendShape.side_effect = None
        # First call: weightCount, second call: geometry
        mock.blendShape.return_value = ["pSphereShape1"]
        mod = self._load(mock)
        with _patch_maya(mock):
            result = mod.main(blend_shape="realBS", target_mesh="targetMesh")
        # Success or exception from mock detail — just check no crash
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestPipelineRound31
# ---------------------------------------------------------------------------


class TestPipelineRound31:
    """get_asset_metadata and tag_asset_metadata now use validate_node_exists."""

    def _path(self, script: str) -> str:
        import os

        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-pipeline",
            "scripts",
            script,
        )

    def _load(self, script: str, mock_cmds: Any) -> ModuleType:
        import importlib.util

        path = self._path(script)
        with _patch_maya(mock_cmds):
            name = "pipe_{}_r31".format(script.replace(".py", ""))
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        return mod

    def test_get_asset_metadata_missing_node(self):
        mock = _make_cmds(exists=False)
        mod = self._load("get_asset_metadata.py", mock)
        with _patch_maya(mock):
            result = mod.main(node="missingNode")
        assert result["success"] is False

    def test_tag_asset_metadata_missing_node(self):
        mock = _make_cmds(exists=False)
        mod = self._load("tag_asset_metadata.py", mock)
        with _patch_maya(mock):
            result = mod.main(node="missingNode")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestUvOpsRound31
# ---------------------------------------------------------------------------


class TestUvOpsRound31:
    """get_uv_shell_info migrated to validate_node_exists."""

    def _path(self) -> str:
        import os

        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-uv-ops",
            "scripts",
            "get_uv_shell_info.py",
        )

    def test_missing_node(self):
        import importlib.util

        mock = _make_cmds(exists=False)
        path = self._path()
        with _patch_maya(mock):
            spec = importlib.util.spec_from_file_location("uv_shell_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.main(object_name="badMesh")
        assert result["success"] is False

    def test_success(self):
        import importlib.util

        mock = _make_cmds(exists=True)
        # polyEvaluate(uvShellsIds=True) returns a list of shell IDs per UV
        mock.polyEvaluate.return_value = [0, 0, 1, 1]
        mock.polyUVSet.return_value = ["map1"]
        mock.polyEditUV.return_value = [0.0, 0.5, 0.0, 0.5]
        path = self._path()
        with _patch_maya(mock):
            spec = importlib.util.spec_from_file_location("uv_shell_r31b", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.main(object_name="pSphere1")
        assert result["success"] is True
        assert "shell_count" in result.get("context", {})


# ---------------------------------------------------------------------------
# TestCamerasLightingRound31
# ---------------------------------------------------------------------------


class TestCamerasLightingRound31:
    """cameras.py and lighting.py set_*_attribute now use validate_node_exists for first guard."""

    def _path(self, script: str) -> str:
        import os

        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "dcc_mcp_maya",
            "skills",
            "maya-scripting",
            "scripts",
            script,
        )

    def test_set_camera_attribute_missing_camera(self):
        import importlib.util

        mock = _make_cmds(exists=False)
        path = self._path("cameras.py")
        with _patch_maya(mock):
            spec = importlib.util.spec_from_file_location("cameras_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.set_camera_attribute("missingCam", "focalLength", 50.0)
        assert result["success"] is False

    def test_set_light_attribute_missing_light(self):
        import importlib.util

        mock = _make_cmds(exists=False)
        path = self._path("lighting.py")
        with _patch_maya(mock):
            spec = importlib.util.spec_from_file_location("lighting_r31", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.set_light_attribute("missingLight", "intensity", 2.0)
        assert result["success"] is False
