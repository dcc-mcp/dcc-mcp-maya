"""Round 37 deep edge-case tests: maya-audio, maya-cache, maya-ocean + server search API.

Coverage targets
----------------
- maya-audio: import_audio (file-not-found, named, offset), list_audio (empty/nodes),
  set_timeline_audio (missing/wrong-type/happy), remove_audio (missing/wrong-type/happy)
- maya-cache: create_geometry_cache (missing obj/mel happy/playback defaults),
  attach_geometry_cache (missing mesh/missing xml/happy),
  list_geometry_caches (all/filtered/mesh-filter/getAttr-error),
  delete_geometry_cache (missing/happy/delete-files)
- maya-ocean: create_ocean (defaults/custom), set_ocean_attribute (missing/happy),
  add_ocean_wake (missing/no-obj/with-obj-exists/with-obj-missing),
  list_ocean_surfaces (empty/one-shader/no-wave-height-attr)
- server: search_skills, get_skill_categories, get_skill_tags (no registry / with registry)
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock, patch

# Import third-party modules
from conftest import load_and_call, load_and_call_with_mel

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _call_mel(rel_path, mock_cmds, mock_mel=None, **kwargs):
    """Shorthand for load_and_call_with_mel."""
    return load_and_call_with_mel(rel_path, mock_cmds, mock_mel=mock_mel, func_name="main", **kwargs)


def _call(rel_path, mock_cmds, **kwargs):
    """Shorthand for load_and_call."""
    return load_and_call(rel_path, mock_cmds, func_name="main", **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# maya-audio: import_audio
# ─────────────────────────────────────────────────────────────────────────────


class TestImportAudio:
    def _mk(self):
        mc = MagicMock()
        mc.sound.return_value = "sound1"
        return mc

    def test_file_not_found(self, tmp_path):
        mc = self._mk()
        result = _call("maya-audio/scripts/import_audio.py", mc, file_path=str(tmp_path / "nonexistent.wav"))
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_happy_path_unnamed(self, tmp_path):
        wav = tmp_path / "music.wav"
        wav.write_bytes(b"RIFF")
        mc = self._mk()
        result = _call("maya-audio/scripts/import_audio.py", mc, file_path=str(wav))
        assert result["success"] is True
        assert result["context"]["sound_node"] == "sound1"
        assert result["context"]["offset"] == 0.0

    def test_named_with_offset(self, tmp_path):
        wav = tmp_path / "score.wav"
        wav.write_bytes(b"RIFF")
        mc = self._mk()
        result = _call("maya-audio/scripts/import_audio.py", mc, file_path=str(wav), name="my_sound", offset=10.0)
        assert result["success"] is True
        call_kwargs = mc.sound.call_args[1]
        assert call_kwargs["name"] == "my_sound"
        assert call_kwargs["offset"] == 10.0

    def test_prompt_present(self, tmp_path):
        wav = tmp_path / "fx.wav"
        wav.write_bytes(b"RIFF")
        mc = self._mk()
        result = _call("maya-audio/scripts/import_audio.py", mc, file_path=str(wav))
        assert "prompt" in result
        assert result["prompt"]

    def test_exception_propagated(self, tmp_path):
        wav = tmp_path / "bad.wav"
        wav.write_bytes(b"RIFF")
        mc = self._mk()
        mc.sound.side_effect = RuntimeError("cmds failure")
        result = _call("maya-audio/scripts/import_audio.py", mc, file_path=str(wav))
        assert result["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# maya-audio: list_audio
# ─────────────────────────────────────────────────────────────────────────────


class TestListAudio:
    def test_empty_scene(self):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _call("maya-audio/scripts/list_audio.py", mc)
        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["sound_nodes"] == []

    def test_two_sound_nodes(self):
        mc = MagicMock()
        mc.ls.return_value = ["snd1", "snd2"]
        mc.getAttr.side_effect = lambda attr: {
            "snd1.filename": "/audio/a.wav",
            "snd1.offset": 0.0,
            "snd2.filename": "/audio/b.wav",
            "snd2.offset": 24.0,
        }[attr]
        result = _call("maya-audio/scripts/list_audio.py", mc)
        assert result["success"] is True
        assert result["context"]["count"] == 2
        nodes = result["context"]["sound_nodes"]
        assert nodes[0]["node"] == "snd1"
        assert nodes[1]["offset"] == 24.0

    def test_prompt_present(self):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _call("maya-audio/scripts/list_audio.py", mc)
        assert "prompt" in result and result["prompt"]

    def test_getattr_returns_none(self):
        mc = MagicMock()
        mc.ls.return_value = ["snd_nil"]
        mc.getAttr.return_value = None
        result = _call("maya-audio/scripts/list_audio.py", mc)
        assert result["success"] is True
        node_info = result["context"]["sound_nodes"][0]
        assert node_info["file_path"] == ""
        assert node_info["offset"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# maya-audio: set_timeline_audio (uses mel)
# ─────────────────────────────────────────────────────────────────────────────


class TestSetTimelineAudio:
    def test_missing_node(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call_mel("maya-audio/scripts/set_timeline_audio.py", mc, sound_node="missing_snd")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_node_type(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "transform"
        result = _call_mel("maya-audio/scripts/set_timeline_audio.py", mc, sound_node="badNode")
        assert result["success"] is False
        assert "sound" in result["message"].lower() or "audio" in result["message"].lower()

    def test_happy_path(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "audio"
        mock_mel = MagicMock()
        mock_mel.eval.return_value = "timeControl1"
        result = _call_mel("maya-audio/scripts/set_timeline_audio.py", mc, mock_mel=mock_mel, sound_node="snd1")
        assert result["success"] is True
        assert result["context"]["sound_node"] == "snd1"

    def test_prompt_present(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "audio"
        result = _call_mel("maya-audio/scripts/set_timeline_audio.py", mc, sound_node="snd1")
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-audio: remove_audio
# ─────────────────────────────────────────────────────────────────────────────


class TestRemoveAudio:
    def test_missing_node(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call("maya-audio/scripts/remove_audio.py", mc, sound_node="ghost")
        assert result["success"] is False

    def test_wrong_type(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "mesh"
        result = _call("maya-audio/scripts/remove_audio.py", mc, sound_node="pSphere1")
        assert result["success"] is False
        assert "sound" in result["message"].lower() or "audio" in result["message"].lower()

    def test_happy_path(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "audio"
        result = _call("maya-audio/scripts/remove_audio.py", mc, sound_node="snd1")
        assert result["success"] is True
        mc.delete.assert_called_once_with("snd1")
        assert result["context"]["deleted_node"] == "snd1"

    def test_prompt_present(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "audio"
        result = _call("maya-audio/scripts/remove_audio.py", mc, sound_node="snd1")
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-cache: create_geometry_cache
# ─────────────────────────────────────────────────────────────────────────────


class TestCreateGeometryCache:
    def test_missing_object(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = False
        mock_mel = MagicMock()
        result = _call_mel(
            "maya-cache/scripts/create_geometry_cache.py",
            mc,
            mock_mel=mock_mel,
            objects=["ghost_mesh"],
            directory=str(tmp_path),
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_happy_path_with_explicit_frames(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = ["cacheFile1"]
        mock_mel = MagicMock()
        result = _call_mel(
            "maya-cache/scripts/create_geometry_cache.py",
            mc,
            mock_mel=mock_mel,
            objects=["pSphere1"],
            directory=str(tmp_path),
            start_frame=1.0,
            end_frame=24.0,
        )
        assert result["success"] is True
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 24
        assert "cacheFile1" in result["context"]["cache_nodes"]

    def test_playback_defaults_used(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = lambda query, minTime=False, maxTime=False: 1.0 if minTime else 48.0
        mc.ls.return_value = []
        mock_mel = MagicMock()
        result = _call_mel(
            "maya-cache/scripts/create_geometry_cache.py",
            mc,
            mock_mel=mock_mel,
            objects=["mesh1"],
            directory=str(tmp_path),
        )
        assert result["success"] is True
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 48

    def test_prompt_present(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = []
        result = _call_mel(
            "maya-cache/scripts/create_geometry_cache.py",
            mc,
            objects=["mesh1"],
            directory=str(tmp_path),
            start_frame=1.0,
            end_frame=10.0,
        )
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-cache: attach_geometry_cache
# ─────────────────────────────────────────────────────────────────────────────


class TestAttachGeometryCache:
    def test_missing_mesh(self, tmp_path):
        xml = tmp_path / "cache.xml"
        xml.write_text("<cache/>")
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call_mel(
            "maya-cache/scripts/attach_geometry_cache.py", mc, mesh="missing_mesh", cache_xml_path=str(xml)
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_missing_xml(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        result = _call_mel(
            "maya-cache/scripts/attach_geometry_cache.py",
            mc,
            mesh="pSphere1",
            cache_xml_path=str(tmp_path / "ghost.xml"),
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_happy_path(self, tmp_path):
        xml = tmp_path / "mesh.xml"
        xml.write_text("<cache/>")
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = ["cacheFile1"]
        mock_mel = MagicMock()
        result = _call_mel(
            "maya-cache/scripts/attach_geometry_cache.py",
            mc,
            mock_mel=mock_mel,
            mesh="pSphere1",
            cache_xml_path=str(xml),
        )
        assert result["success"] is True
        assert result["context"]["mesh"] == "pSphere1"
        assert "cacheFile1" in result["context"]["cache_nodes"]

    def test_prompt_present(self, tmp_path):
        xml = tmp_path / "x.xml"
        xml.write_text("<c/>")
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = []
        result = _call_mel("maya-cache/scripts/attach_geometry_cache.py", mc, mesh="pSphere1", cache_xml_path=str(xml))
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-cache: list_geometry_caches
# ─────────────────────────────────────────────────────────────────────────────


class TestListGeometryCaches:
    def test_empty_scene(self):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _call("maya-cache/scripts/list_geometry_caches.py", mc)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_all_caches(self):
        mc = MagicMock()
        mc.ls.return_value = ["cf1", "cf2"]
        mc.getAttr.side_effect = lambda attr: {
            "cf1.cachePath": "/tmp/cache/",
            "cf1.cacheName": "mesh1",
            "cf1.sourceStart": 1.0,
            "cf1.sourceEnd": 24.0,
            "cf2.cachePath": "/tmp/cache/",
            "cf2.cacheName": "mesh2",
            "cf2.sourceStart": 1.0,
            "cf2.sourceEnd": 48.0,
        }[attr]
        result = _call("maya-cache/scripts/list_geometry_caches.py", mc)
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_filter_by_mesh(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = ["cf1", "cf2"]
        mc.listRelatives.return_value = ["pSphereShape1"]
        mc.listConnections.return_value = ["cf1"]
        mc.getAttr.return_value = ""
        result = _call("maya-cache/scripts/list_geometry_caches.py", mc, mesh="pSphere1")
        assert result["success"] is True
        nodes = result["context"]["cache_nodes"]
        assert all(n["node"] == "cf1" for n in nodes)

    def test_mesh_not_found(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call("maya-cache/scripts/list_geometry_caches.py", mc, mesh="ghost_mesh")
        assert result["success"] is False

    def test_prompt_present(self):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _call("maya-cache/scripts/list_geometry_caches.py", mc)
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-cache: delete_geometry_cache
# ─────────────────────────────────────────────────────────────────────────────


class TestDeleteGeometryCache:
    def test_missing_cache_node(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call("maya-cache/scripts/delete_geometry_cache.py", mc, cache_node="ghost_cf")
        assert result["success"] is False

    def test_happy_path_no_delete_files(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        result = _call("maya-cache/scripts/delete_geometry_cache.py", mc, cache_node="cf1", delete_files=False)
        assert result["success"] is True
        mc.delete.assert_called_once_with("cf1")
        assert result["context"]["files_deleted"] == []

    def test_delete_files_removes_on_disk(self, tmp_path):
        xml_file = tmp_path / "cache.xml"
        mcx_file = tmp_path / "cache.mcx"
        xml_file.write_text("<c/>")
        mcx_file.write_bytes(b"\x00")

        mc = MagicMock()
        mc.objExists.return_value = True
        mc.getAttr.side_effect = lambda attr: {
            "cf1.cachePath": str(tmp_path),
            "cf1.cacheName": "cache",
        }[attr]
        result = _call("maya-cache/scripts/delete_geometry_cache.py", mc, cache_node="cf1", delete_files=True)
        assert result["success"] is True
        assert len(result["context"]["files_deleted"]) == 2
        assert not xml_file.exists()
        assert not mcx_file.exists()

    def test_prompt_present(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        result = _call("maya-cache/scripts/delete_geometry_cache.py", mc, cache_node="cf1")
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-ocean: create_ocean
# ─────────────────────────────────────────────────────────────────────────────


class TestCreateOcean:
    def _mk(self):
        mc = MagicMock()
        mc.polyPlane.return_value = ["ocean_surface", "polyPlane1"]
        mc.shadingNode.return_value = "ocean_surface_shader"
        mc.sets.side_effect = lambda *a, **kw: "ocean_surface_SG" if kw.get("empty") else None
        return mc

    def test_defaults(self):
        mc = self._mk()
        result = _call("maya-ocean/scripts/create_ocean.py", mc)
        assert result["success"] is True
        assert result["context"]["ocean_transform"] == "ocean_surface"
        assert result["context"]["shader_name"] == "ocean_surface_shader"

    def test_custom_name_and_scale(self):
        mc = self._mk()
        mc.polyPlane.return_value = ["my_ocean", "polyPlane2"]
        mc.shadingNode.return_value = "my_ocean_shader"
        result = _call("maya-ocean/scripts/create_ocean.py", mc, name="my_ocean", scale=200.0)
        assert result["success"] is True
        call_kwargs = mc.polyPlane.call_args[1]
        assert call_kwargs["width"] == 200.0

    def test_polyplane_exception(self):
        mc = MagicMock()
        mc.polyPlane.side_effect = RuntimeError("plugin not loaded")
        result = _call("maya-ocean/scripts/create_ocean.py", mc)
        assert result["success"] is False

    def test_prompt_present(self):
        mc = self._mk()
        result = _call("maya-ocean/scripts/create_ocean.py", mc)
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-ocean: set_ocean_attribute
# ─────────────────────────────────────────────────────────────────────────────


class TestSetOceanAttribute:
    def test_missing_shader(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call(
            "maya-ocean/scripts/set_ocean_attribute.py", mc, shader="ghost_shader", attribute="waveHeight", value=2.0
        )
        assert result["success"] is False

    def test_happy_path(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        result = _call(
            "maya-ocean/scripts/set_ocean_attribute.py", mc, shader="oceanShader1", attribute="waveHeight", value=3.5
        )
        assert result["success"] is True
        mc.setAttr.assert_called_once_with("oceanShader1.waveHeight", 3.5)
        assert result["context"]["value"] == 3.5

    def test_context_keys(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        result = _call("maya-ocean/scripts/set_ocean_attribute.py", mc, shader="sh1", attribute="windSpeed", value=10.0)
        assert result["context"]["shader"] == "sh1"
        assert result["context"]["attribute"] == "windSpeed"

    def test_prompt_present(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        result = _call("maya-ocean/scripts/set_ocean_attribute.py", mc, shader="sh1", attribute="waveHeight", value=1.0)
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-ocean: add_ocean_wake
# ─────────────────────────────────────────────────────────────────────────────


class TestAddOceanWake:
    def test_missing_shader(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _call("maya-ocean/scripts/add_ocean_wake.py", mc, shader="ghost_sh")
        assert result["success"] is False

    def test_happy_path_no_wake_object(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["oceanShader1_wake_loc"]
        result = _call("maya-ocean/scripts/add_ocean_wake.py", mc, shader="oceanShader1", wake_size=2.0)
        assert result["success"] is True
        assert result["context"]["wake_locator"] == "oceanShader1_wake_loc"
        mc.setAttr.assert_called_with("oceanShader1.waveHeightScale", 2.0)

    def test_with_wake_object_exists(self):
        """When wake_object exists, parentConstraint should be called."""
        mc = MagicMock()
        # objExists is called twice: shader (True) + wake_object check (True)
        mc.objExists.side_effect = [True, True]
        mc.spaceLocator.return_value = ["sh_wake_loc"]
        result = _call("maya-ocean/scripts/add_ocean_wake.py", mc, shader="sh", wake_object="boat", wake_size=1.0)
        assert result["success"] is True
        mc.parentConstraint.assert_called_once_with("boat", "sh_wake_loc", maintainOffset=False)

    def test_with_wake_object_missing_skips_constraint(self):
        """When wake_object does not exist, parentConstraint should NOT be called."""
        mc = MagicMock()
        # First objExists = shader exists, second = wake_object missing
        mc.objExists.side_effect = [True, False]
        mc.spaceLocator.return_value = ["sh_wake_loc"]
        result = _call("maya-ocean/scripts/add_ocean_wake.py", mc, shader="sh", wake_object="ghost_boat", wake_size=1.0)
        assert result["success"] is True
        mc.parentConstraint.assert_not_called()

    def test_prompt_present(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["sh_wake_loc"]
        result = _call("maya-ocean/scripts/add_ocean_wake.py", mc, shader="sh")
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# maya-ocean: list_ocean_surfaces
# ─────────────────────────────────────────────────────────────────────────────


class TestListOceanSurfaces:
    def test_empty_scene(self):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _call("maya-ocean/scripts/list_ocean_surfaces.py", mc)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_one_shader_with_wave_height(self):
        mc = MagicMock()
        mc.ls.return_value = ["oceanShader1"]
        mc.listConnections.return_value = ["oceanSG1"]
        mc.sets.return_value = ["ocean_surface"]
        mc.attributeQuery.return_value = True
        mc.getAttr.return_value = 2.5
        result = _call("maya-ocean/scripts/list_ocean_surfaces.py", mc)
        assert result["success"] is True
        assert result["context"]["count"] == 1
        surf = result["context"]["surfaces"][0]
        assert surf["shader"] == "oceanShader1"
        assert surf["wave_height"] == 2.5

    def test_no_wave_height_attr(self):
        mc = MagicMock()
        mc.ls.return_value = ["sh1"]
        mc.listConnections.return_value = []
        mc.sets.return_value = []
        mc.attributeQuery.return_value = False
        result = _call("maya-ocean/scripts/list_ocean_surfaces.py", mc)
        assert result["success"] is True
        surf = result["context"]["surfaces"][0]
        assert surf["wave_height"] is None

    def test_prompt_present(self):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _call("maya-ocean/scripts/list_ocean_surfaces.py", mc)
        assert "prompt" in result and result["prompt"]


# ─────────────────────────────────────────────────────────────────────────────
# server.py: search_skills / get_skill_categories / get_skill_tags
# ─────────────────────────────────────────────────────────────────────────────


class TestServerSearchAPI:
    """Unit tests for MayaMcpServer search / discovery helpers."""

    def _make_server(self, registry=None):
        """Return a MayaMcpServer with mocked internals (bypasses __init__)."""
        from dcc_mcp_maya.server import MayaMcpServer  # noqa: PLC0415

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._config = MagicMock()
        srv._server = MagicMock()
        srv._handle = None
        srv._hot_reloader = None
        srv._gateway_election = None
        srv._enable_gateway_failover = False
        if registry is not None:
            srv._server.registry = registry
        else:
            srv._server.registry = None
        return srv

    def test_search_skills_no_registry_returns_empty(self):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._config = MagicMock()
        srv._server = MagicMock()
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda self: None)):
            result = srv.search_actions(category="geometry")
        assert result == []

    def test_search_skills_delegates_to_registry(self):
        mock_registry = MagicMock()
        mock_registry.search_actions.return_value = ["tool1", "tool2"]

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            result = srv.search_actions(category="geometry", tags=["mesh"])

        mock_registry.search_actions.assert_called_once_with(category="geometry", tags=["mesh"], dcc_name="maya")
        assert result == ["tool1", "tool2"]

    def test_search_skills_uses_custom_dcc_name(self):
        mock_registry = MagicMock()
        mock_registry.search_actions.return_value = []

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            srv.search_actions(dcc_name="houdini")

        call_kwargs = mock_registry.search_actions.call_args[1]
        assert call_kwargs["dcc_name"] == "houdini"

    def test_search_skills_exception_returns_empty(self):
        mock_registry = MagicMock()
        mock_registry.search_actions.side_effect = RuntimeError("oops")

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            result = srv.search_actions()
        assert result == []

    def test_get_skill_categories_returns_sorted_list(self):
        mock_registry = MagicMock()
        mock_registry.get_categories.return_value = ["geometry", "animation", "lighting"]

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            cats = srv.get_skill_categories()
        assert cats == ["geometry", "animation", "lighting"]

    def test_get_skill_categories_no_registry(self):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: None)):
            assert srv.get_skill_categories() == []

    def test_get_skill_categories_exception_returns_empty(self):
        mock_registry = MagicMock()
        mock_registry.get_categories.side_effect = AttributeError("no method")

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            assert srv.get_skill_categories() == []

    def test_get_skill_tags_default_dcc_maya(self):
        mock_registry = MagicMock()
        mock_registry.get_tags.return_value = ["mesh", "create", "transform"]

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            tags = srv.get_skill_tags()
        mock_registry.get_tags.assert_called_once_with(dcc_name="maya")
        assert "mesh" in tags

    def test_get_skill_tags_custom_dcc(self):
        mock_registry = MagicMock()
        mock_registry.get_tags.return_value = []

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            srv.get_skill_tags(dcc_name="blender")
        mock_registry.get_tags.assert_called_once_with(dcc_name="blender")

    def test_get_skill_tags_no_registry(self):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: None)):
            assert srv.get_skill_tags() == []

    def test_get_skill_tags_exception_returns_empty(self):
        mock_registry = MagicMock()
        mock_registry.get_tags.side_effect = RuntimeError("broken")

        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._handle = None
        with patch.object(type(srv), "registry", new_callable=lambda: property(lambda s: mock_registry)):
            assert srv.get_skill_tags() == []
