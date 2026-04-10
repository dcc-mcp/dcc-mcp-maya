"""Unit tests for Round 15 skill scripts: nparticles, cache, audio.

All tests mock maya.cmds / maya.mel to avoid requiring a real Maya environment.
Scripts are loaded via importlib to handle hyphenated skill directory names.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r15_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, mel_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    mel_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    maya_mock.mel = mel_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.mel": mel_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    return maya_mock, cmds_mock, mel_mock, modules


# ---------------------------------------------------------------------------
# maya-nparticles
# ---------------------------------------------------------------------------


class TestCreateNParticleSystem:
    def test_create_default(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.nParticle.return_value = ["nParticle1", "nParticleShape1"]
        cmds_mock.ls.return_value = ["nucleus1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "create_nparticle_system")
            result = mod.create_nparticle_system()
        assert result["success"] is True
        assert result["context"]["particle_node"] == "nParticle1"
        assert result["context"]["particle_type"] == "points"
        assert result["context"]["nucleus_node"] == "nucleus1"

    def test_create_spheres(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.nParticle.return_value = ["nParticle2", "nParticleShape2"]
        cmds_mock.ls.return_value = ["nucleus1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "create_nparticle_system")
            result = mod.create_nparticle_system(particle_type="spheres")
        assert result["success"] is True
        assert result["context"]["particle_type"] == "spheres"

    def test_invalid_particle_type(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "create_nparticle_system")
            result = mod.create_nparticle_system(particle_type="cubes")
        assert result["success"] is False

    def test_create_with_name(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.nParticle.return_value = ["myParticle", "myParticleShape"]
        cmds_mock.ls.return_value = ["nucleus1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "create_nparticle_system")
            result = mod.create_nparticle_system(name="myParticle")
        assert result["success"] is True
        assert result["context"]["particle_node"] == "myParticle"

    def test_no_nucleus(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.nParticle.return_value = ["nParticle1"]
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "create_nparticle_system")
            result = mod.create_nparticle_system()
        assert result["success"] is True
        assert result["context"]["nucleus_node"] == "nucleus1"

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.nParticle.side_effect = RuntimeError("DG error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "create_nparticle_system")
            result = mod.create_nparticle_system()
        assert result["success"] is False


class TestListNParticleSystems:
    def test_list_empty(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_with_particles(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["nParticle1", "nParticle2"]
        cmds_mock.listConnections.return_value = ["nucleus1"]
        cmds_mock.getParticleAttr.return_value = 500
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert result["context"]["particles"][0]["node"] == "nParticle1"

    def test_list_no_nucleus(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["nParticle1"]
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is True
        assert result["context"]["particles"][0]["nucleus"] is None

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("DG error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is False


class TestSetNParticleAttribute:
    def test_set_scalar(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nParticle1", "radius", 0.5)
        assert result["success"] is True
        assert result["context"]["attribute"] == "radius"
        assert result["context"]["value"] == 0.5

    def test_set_list_value(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nParticle1", "velocity", [1.0, 2.0, 3.0])
        assert result["success"] is True
        cmds_mock.setAttr.assert_called_once_with(
            "nParticle1.velocity", 1.0, 2.0, 3.0
        )

    def test_node_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("ghost", "radius", 1.0)
        assert result["success"] is False

    def test_empty_node(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("", "radius", 1.0)
        assert result["success"] is False

    def test_empty_attribute(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nParticle1", "", 1.0)
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nParticle1", "radius", 1.0)
        assert result["success"] is False


class TestEmitParticles:
    def test_emit_omni(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.emitter.return_value = ["emitter1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "emit_particles")
            result = mod.emit_particles("nParticle1")
        assert result["success"] is True
        assert result["context"]["emitter_type"] == "omni"
        assert result["context"]["particle_node"] == "nParticle1"

    def test_emit_surface(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.emitter.return_value = ["emitter2"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "emit_particles")
            result = mod.emit_particles("nParticle1", emitter_type="surface", source_object="pSphere1")
        assert result["success"] is True
        assert result["context"]["emitter_type"] == "surface"

    def test_invalid_emitter_type(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "emit_particles")
            result = mod.emit_particles("nParticle1", emitter_type="laser")
        assert result["success"] is False

    def test_particle_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "emit_particles")
            result = mod.emit_particles("ghost")
        assert result["success"] is False

    def test_source_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda x: x == "nParticle1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "emit_particles")
            result = mod.emit_particles("nParticle1", emitter_type="surface", source_object="ghost")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.emitter.side_effect = RuntimeError("emitter error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "emit_particles")
            result = mod.emit_particles("nParticle1")
        assert result["success"] is False


class TestDeleteNParticleSystem:
    def test_delete_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "delete_nparticle_system")
            result = mod.delete_nparticle_system("nParticle1")
        assert result["success"] is True
        assert result["context"]["particle_node"] == "nParticle1"
        assert result["context"]["nucleus_deleted"] is False
        cmds_mock.delete.assert_called_once_with("nParticle1")

    def test_delete_with_nucleus(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.listConnections.return_value = ["nucleus1"]
        # After deleting particle, no more nParticle connected to nucleus
        cmds_mock.listConnections.side_effect = [["nucleus1"], []]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "delete_nparticle_system")
            result = mod.delete_nparticle_system("nParticle1", delete_nucleus=True)
        assert result["success"] is True
        assert result["context"]["nucleus_deleted"] is True

    def test_nucleus_not_deleted_if_others_remain(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.listConnections.side_effect = [["nucleus1"], ["nParticle2"]]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "delete_nparticle_system")
            result = mod.delete_nparticle_system("nParticle1", delete_nucleus=True)
        assert result["success"] is True
        assert result["context"]["nucleus_deleted"] is False

    def test_node_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "delete_nparticle_system")
            result = mod.delete_nparticle_system("ghost")
        assert result["success"] is False

    def test_empty_node(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-nparticles", "delete_nparticle_system")
            result = mod.delete_nparticle_system("")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-cache
# ---------------------------------------------------------------------------


class TestExportAlembic:
    def test_export_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        cmds_mock.playbackOptions.return_value = 1.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic(["pSphere1"], "/tmp/test.abc")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/tmp/test.abc"
        assert result["context"]["object_count"] == 1

    def test_export_multiple_objects(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        cmds_mock.playbackOptions.return_value = 1.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic(["pSphere1", "pCube1"], "/tmp/multi.abc")
        assert result["success"] is True
        assert result["context"]["object_count"] == 2

    def test_no_objects(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic([], "/tmp/test.abc")
        assert result["success"] is False

    def test_no_file_path(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic(["pSphere1"], "")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic(["ghost"], "/tmp/test.abc")
        assert result["success"] is False

    def test_custom_frame_range(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic(
                ["pSphere1"], "/tmp/test.abc", start_frame=10.0, end_frame=50.0
            )
        assert result["success"] is True
        assert result["context"]["start_frame"] == 10.0
        assert result["context"]["end_frame"] == 50.0

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        cmds_mock.playbackOptions.return_value = 1.0
        cmds_mock.AbcExport.side_effect = RuntimeError("AbcExport error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "export_alembic")
            result = mod.export_alembic(["pSphere1"], "/tmp/test.abc")
        assert result["success"] is False


class TestImportAlembic:
    def test_import_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "import_alembic")
            result = mod.import_alembic("/tmp/test.abc")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/tmp/test.abc"
        assert result["context"]["namespace"] == ""

    def test_import_with_namespace(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "import_alembic")
            result = mod.import_alembic("/tmp/test.abc", namespace="char")
        assert result["success"] is True
        assert result["context"]["namespace"] == "char"

    def test_no_file_path(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "import_alembic")
            result = mod.import_alembic("")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.pluginInfo.return_value = True
        cmds_mock.AbcImport.side_effect = RuntimeError("file not found")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "import_alembic")
            result = mod.import_alembic("/tmp/missing.abc")
        assert result["success"] is False


class TestCreateNCache:
    def test_create_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.playbackOptions.return_value = 1.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "create_ncache")
            result = mod.create_ncache(["nCloth1"], "/tmp/cache")
        assert result["success"] is True
        assert result["context"]["cache_dir"] == "/tmp/cache"
        assert result["context"]["objects"] == ["nCloth1"]

    def test_no_objects(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "create_ncache")
            result = mod.create_ncache([], "/tmp/cache")
        assert result["success"] is False

    def test_no_cache_dir(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "create_ncache")
            result = mod.create_ncache(["nCloth1"], "")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "create_ncache")
            result = mod.create_ncache(["ghost"], "/tmp/cache")
        assert result["success"] is False

    def test_custom_frame_range(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "create_ncache")
            result = mod.create_ncache(["nCloth1"], "/tmp/cache", start_frame=5.0, end_frame=20.0)
        assert result["success"] is True
        assert result["context"]["frame_range"] == [5.0, 20.0]

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.playbackOptions.return_value = 1.0
        cmds_mock.cacheFile.side_effect = RuntimeError("cacheFile error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "create_ncache")
            result = mod.create_ncache(["nCloth1"], "/tmp/cache")
        assert result["success"] is False


class TestListCaches:
    def test_list_empty(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "list_caches")
            result = mod.list_caches()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_with_cache_file(self):
        _, cmds_mock, _, modules = _make_maya_env()

        def ls_side(type=None):
            if type == "cacheFile":
                return ["cacheFile1"]
            return []

        cmds_mock.ls.side_effect = ls_side
        cmds_mock.getAttr.return_value = "/tmp/cache"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "list_caches")
            result = mod.list_caches()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["caches"][0]["node"] == "cacheFile1"
        assert result["context"]["caches"][0]["cache_type"] == "cacheFile"

    def test_list_with_alembic_node(self):
        _, cmds_mock, _, modules = _make_maya_env()

        def ls_side(type=None):
            if type == "AlembicNode":
                return ["AlembicNode1"]
            return []

        cmds_mock.ls.side_effect = ls_side
        cmds_mock.getAttr.return_value = "/tmp/test.abc"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "list_caches")
            result = mod.list_caches()
        assert result["success"] is True
        assert result["context"]["caches"][0]["cache_type"] == "AlembicNode"

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("DG error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "list_caches")
            result = mod.list_caches()
        assert result["success"] is False


class TestDeleteCache:
    def test_delete_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "delete_cache")
            result = mod.delete_cache("cacheFile1")
        assert result["success"] is True
        assert result["context"]["cache_node"] == "cacheFile1"
        assert result["context"]["files_deleted"] is False
        cmds_mock.delete.assert_called_once_with("cacheFile1")

    def test_delete_empty_node(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "delete_cache")
            result = mod.delete_cache("")
        assert result["success"] is False

    def test_node_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "delete_cache")
            result = mod.delete_cache("ghost")
        assert result["success"] is False

    def test_delete_with_files(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "cacheFile"
        cmds_mock.getAttr.side_effect = ["/tmp/cache", "nCloth1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "delete_cache")
            # files_deleted may be False if glob finds nothing — that's OK
            result = mod.delete_cache("cacheFile1", delete_files=True)
        assert result["success"] is True

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.delete.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cache", "delete_cache")
            result = mod.delete_cache("cacheFile1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-audio
# ---------------------------------------------------------------------------


class TestImportAudio:
    def test_import_wav(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.sound.return_value = "sound1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("/tmp/music.wav")
        assert result["success"] is True
        assert result["context"]["sound_node"] == "sound1"
        assert result["context"]["file_path"] == "/tmp/music.wav"

    def test_import_aiff(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.sound.return_value = "sound2"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("/tmp/music.aif")
        assert result["success"] is True

    def test_import_with_name_and_offset(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.sound.return_value = "mySound"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("/tmp/music.wav", node_name="mySound", offset=5.0)
        assert result["success"] is True
        assert result["context"]["offset"] == 5.0

    def test_unsupported_format(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("/tmp/music.ogg")
        assert result["success"] is False

    def test_no_file_path(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.sound.side_effect = RuntimeError("cannot open file")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("/tmp/music.wav")
        assert result["success"] is False


class TestListAudioNodes:
    def test_list_empty(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "list_audio_nodes")
            result = mod.list_audio_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_with_nodes(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["sound1", "sound2"]
        cmds_mock.getAttr.side_effect = ["/tmp/music.wav", 0.0, "/tmp/fx.wav", 5.0]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "list_audio_nodes")
            result = mod.list_audio_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert result["context"]["audio_nodes"][0]["node"] == "sound1"

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("DG error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "list_audio_nodes")
            result = mod.list_audio_nodes()
        assert result["success"] is False


class TestSetAudioOffset:
    def test_set_offset(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_audio_offset")
            result = mod.set_audio_offset("sound1", 10.0)
        assert result["success"] is True
        assert result["context"]["offset"] == 10.0
        cmds_mock.setAttr.assert_called_once_with("sound1.offset", 10.0)

    def test_node_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_audio_offset")
            result = mod.set_audio_offset("ghost", 0.0)
        assert result["success"] is False

    def test_empty_node(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_audio_offset")
            result = mod.set_audio_offset("", 0.0)
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_audio_offset")
            result = mod.set_audio_offset("sound1", 5.0)
        assert result["success"] is False


class TestSetActiveAudio:
    def test_set_active(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.return_value = "timeControl1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_active_audio")
            result = mod.set_active_audio("sound1")
        assert result["success"] is True
        assert result["context"]["sound_node"] == "sound1"
        assert result["context"]["display_waveform"] is True

    def test_set_active_no_waveform(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.return_value = "timeControl1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_active_audio")
            result = mod.set_active_audio("sound1", display_waveform=False)
        assert result["success"] is True
        assert result["context"]["display_waveform"] is False

    def test_node_not_found(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_active_audio")
            result = mod.set_active_audio("ghost")
        assert result["success"] is False

    def test_empty_node(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_active_audio")
            result = mod.set_active_audio("")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.side_effect = RuntimeError("no time slider")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "set_active_audio")
            result = mod.set_active_audio("sound1")
        assert result["success"] is False


class TestDeleteAudioNode:
    def test_delete_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "audio"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "delete_audio_node")
            result = mod.delete_audio_node("sound1")
        assert result["success"] is True
        assert result["context"]["sound_node"] == "sound1"
        cmds_mock.delete.assert_called_once_with("sound1")

    def test_delete_empty_node(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "delete_audio_node")
            result = mod.delete_audio_node("")
        assert result["success"] is False

    def test_node_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "delete_audio_node")
            result = mod.delete_audio_node("ghost")
        assert result["success"] is False

    def test_wrong_type(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "delete_audio_node")
            result = mod.delete_audio_node("pSphere1")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "audio"
        cmds_mock.delete.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-audio", "delete_audio_node")
            result = mod.delete_audio_node("sound1")
        assert result["success"] is False
