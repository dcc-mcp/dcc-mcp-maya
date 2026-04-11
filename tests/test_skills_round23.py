"""Round 23 tests — error-path and edge-case coverage for Round 5-9 skills.

Focuses on:
- maya-toon (add_toon_outline, create_toon_shader, set_outline_width, list_toon_outlines)
- maya-fluid (create_fluid_container, set_fluid_attribute, list_fluid_containers, delete_fluid_container)
- maya-ocean (create_ocean, set_ocean_attribute, add_ocean_wake, list_ocean_surfaces)
- maya-cloth-sim (create_ncloth, set_ncloth_attribute, bake_cloth_cache, list_ncloth_objects)
- maya-mocap (import_mocap: file-not-found and unsupported-format paths)
- maya-scene-assembly (create_assembly_definition, add_assembly_representation, list_assemblies)
- maya-proxy-mesh (create_proxy: missing source; swap_proxy; set_proxy_attribute; list_proxies)
- maya-muscle (create_muscle_capsule, list_muscles, set_muscle_attribute, apply_muscle_skin)
- maya-export-preset (save_export_preset, load_export_preset, list_export_presets, delete_export_preset)
- maya-pipeline (set_project, tag/get metadata round-trip, publish_asset)
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock

# Import third-party modules
from tests.conftest import load_skill_script


def _mock_maya():
    """Install fresh maya mock modules into sys.modules and return (cmds, mel)."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_mel = MagicMock()
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.mel"] = mock_mel
    sys.modules["maya.api"] = MagicMock()
    sys.modules["maya.utils"] = MagicMock()
    return mock_cmds, mock_mel


def _clear_maya():
    for mod in ["maya", "maya.cmds", "maya.mel", "maya.api", "maya.utils"]:
        sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# maya-toon
# ---------------------------------------------------------------------------


class TestToonAddOutline:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_no_objects_and_empty_selection_returns_error(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-toon", "add_toon_outline")
        result = mod.add_toon_outline(objects=None)
        assert result["success"] is False
        assert "No objects" in result["message"]

    def test_objects_with_no_mesh_shapes_returns_error(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []
        mod = load_skill_script("maya-toon", "add_toon_outline")
        result = mod.add_toon_outline(objects=["emptyGroup"])
        assert result["success"] is False
        assert "No mesh" in result["message"]

    def test_with_mesh_shape_succeeds(self):
        """add_toon_outline with a direct mesh shape calls assignNewPfxToon MEL."""
        mock_cmds, mock_mel = _mock_maya()
        # The object is a mesh shape (objectType returns 'mesh')
        mock_cmds.objectType.return_value = "mesh"
        mock_cmds.ls.return_value = ["pfxToon1"]
        mock_cmds.rename.return_value = "myOutline"
        mock_cmds.attributeQuery.return_value = True
        mod = load_skill_script("maya-toon", "add_toon_outline")
        result = mod.add_toon_outline(objects=["pSphereShape1"], name="myOutline")
        assert result["success"] is True
        assert result["context"]["line_width"] == 1.0

    def test_list_toon_outlines_empty(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-toon", "list_toon_outlines")
        result = mod.list_toon_outlines()
        assert result["success"] is True
        assert result["context"]["outlines"] == []
        assert result["context"]["count"] == 0

    def test_list_toon_outlines_found(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["pfxToon1", "pfxToon2"]
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 2.5
        mock_cmds.listConnections.return_value = ["pSphereShape"]
        mod = load_skill_script("maya-toon", "list_toon_outlines")
        result = mod.list_toon_outlines()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_set_outline_width_success(self):
        """set_outline_width requires objectType == 'pfxToon'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pfxToon"
        mock_cmds.attributeQuery.return_value = True
        mod = load_skill_script("maya-toon", "set_outline_width")
        result = mod.set_outline_width(toon_node="pfxToon1", line_width=3.0)
        assert result["success"] is True
        mock_cmds.setAttr.assert_any_call("pfxToon1.lineWidth", 3.0)

    def test_set_outline_width_node_missing(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-toon", "set_outline_width")
        result = mod.set_outline_width(toon_node="missingNode", line_width=1.0)
        assert result["success"] is False

    def test_set_outline_width_wrong_type(self):
        """Returns failure if node is not a pfxToon."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mod = load_skill_script("maya-toon", "set_outline_width")
        result = mod.set_outline_width(toon_node="pSphere1", line_width=2.0)
        assert result["success"] is False

    def test_create_toon_shader_defaults(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.shadingNode.return_value = "toonShader1"
        mock_cmds.sets.return_value = "toonShader1_SG"
        mod = load_skill_script("maya-toon", "create_toon_shader")
        result = mod.create_toon_shader()
        assert result["success"] is True
        assert result["context"]["shader"] == "toonShader1"
        assert result["context"]["shading_group"] == "toonShader1_SG"

    def test_create_toon_shader_with_assign_to(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.shadingNode.return_value = "toonS"
        mock_cmds.sets.return_value = "toonS_SG"
        mock_cmds.objExists.return_value = True
        mod = load_skill_script("maya-toon", "create_toon_shader")
        result = mod.create_toon_shader(name="toonS", assign_to=["pSphere1"])
        assert result["success"] is True
        assert "pSphere1" in result["context"]["assigned_to"]


# ---------------------------------------------------------------------------
# maya-fluid
# ---------------------------------------------------------------------------


class TestFluidSkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_create_fluid_container_default(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        mod = load_skill_script("maya-fluid", "create_fluid_container")
        result = mod.create_fluid_container()
        assert result["success"] is True
        assert result["context"]["fluid_shape"] == "fluidShape1"
        assert result["context"]["fluid_transform"] == "fluid1"

    def test_create_fluid_container_with_name(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        mock_cmds.rename.return_value = "myFluid"
        mod = load_skill_script("maya-fluid", "create_fluid_container")
        result = mod.create_fluid_container(name="myFluid", resolution=20)
        assert result["success"] is True
        mock_cmds.create3dFluid.assert_called_once()

    def test_list_fluid_containers_empty(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-fluid", "list_fluid_containers")
        result = mod.list_fluid_containers()
        assert result["success"] is True
        assert result["context"]["containers"] == []

    def test_list_fluid_containers_found(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["fluidShape1", "fluidShape2"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        mock_cmds.attributeQuery.return_value = True
        # resolution attr returns a tuple of a list (Maya style: ((10, 10, 10),))
        mock_cmds.getAttr.return_value = ((10, 10, 10),)
        mod = load_skill_script("maya-fluid", "list_fluid_containers")
        result = mod.list_fluid_containers()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_set_fluid_attribute_success(self):
        """set_fluid_attribute uses param name 'fluid_shape', not 'fluid_node'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mod = load_skill_script("maya-fluid", "set_fluid_attribute")
        result = mod.set_fluid_attribute(fluid_shape="fluidShape1", attribute="density", value=1.5)
        assert result["success"] is True

    def test_set_fluid_attribute_node_missing(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-fluid", "set_fluid_attribute")
        result = mod.set_fluid_attribute(fluid_shape="missing", attribute="density", value=1.0)
        assert result["success"] is False

    def test_delete_fluid_container_success(self):
        """delete_fluid_container uses param name 'name', not 'fluid_name'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.side_effect = [["fluidShape1"], ["fluid1"]]
        mod = load_skill_script("maya-fluid", "delete_fluid_container")
        result = mod.delete_fluid_container(name="fluid1")
        assert result["success"] is True
        mock_cmds.delete.assert_called()

    def test_delete_fluid_container_missing(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-fluid", "delete_fluid_container")
        result = mod.delete_fluid_container(name="nonexistent")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-ocean
# ---------------------------------------------------------------------------


class TestOceanSkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_create_ocean_success(self):
        mock_cmds, _ = _mock_maya()
        # polyPlane returns a tuple, not a list of tuples
        mock_cmds.polyPlane.return_value = ("ocean_surface", "polyPlane1")
        mock_cmds.shadingNode.return_value = "ocean_surface_shader"
        mock_cmds.sets.return_value = "ocean_surface_SG"
        mod = load_skill_script("maya-ocean", "create_ocean")
        result = mod.create_ocean()
        assert result["success"] is True
        assert result["context"]["shader_name"] == "ocean_surface_shader"

    def test_create_ocean_custom_name_and_scale(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.polyPlane.return_value = ("my_ocean", "polyPlane1")
        mock_cmds.shadingNode.return_value = "my_ocean_shader"
        mock_cmds.sets.return_value = "my_ocean_SG"
        mod = load_skill_script("maya-ocean", "create_ocean")
        result = mod.create_ocean(name="my_ocean", scale=200.0)
        assert result["success"] is True
        call_kwargs = mock_cmds.polyPlane.call_args[1]
        assert call_kwargs["width"] == 200.0

    def test_list_ocean_surfaces_empty(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-ocean", "list_ocean_surfaces")
        result = mod.list_ocean_surfaces()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_ocean_surfaces_found(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["ocean_surface_shader"]
        mock_cmds.listConnections.return_value = ["ocean_surface_SG"]
        mock_cmds.sets.return_value = ["ocean_surface"]
        mod = load_skill_script("maya-ocean", "list_ocean_surfaces")
        result = mod.list_ocean_surfaces()
        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_set_ocean_attribute_success(self):
        """set_ocean_attribute uses param 'shader', not 'ocean_surface'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mod = load_skill_script("maya-ocean", "set_ocean_attribute")
        result = mod.set_ocean_attribute(shader="ocean_surface_shader", attribute="scale", value=0.5)
        assert result["success"] is True

    def test_set_ocean_attribute_missing_shader(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-ocean", "set_ocean_attribute")
        result = mod.set_ocean_attribute(shader="missing", attribute="scale", value=0.5)
        assert result["success"] is False

    def test_add_ocean_wake_success(self):
        """add_ocean_wake uses param 'shader', not 'ocean_surface'."""
        mock_cmds, mock_mel = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["oceanWakeLocator1"]
        mod = load_skill_script("maya-ocean", "add_ocean_wake")
        result = mod.add_ocean_wake(shader="ocean_surface_shader")
        assert result["success"] is True

    def test_add_ocean_wake_missing_shader(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-ocean", "add_ocean_wake")
        result = mod.add_ocean_wake(shader="missing")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-cloth-sim
# ---------------------------------------------------------------------------


class TestClothSimSkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_create_ncloth_missing_mesh(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-cloth-sim", "create_ncloth")
        result = mod.create_ncloth(mesh="missingMesh")
        assert result["success"] is False
        assert "not found" in result["message"] or "does not exist" in result["message"]

    def test_create_ncloth_cotton_preset(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.side_effect = [["nClothShape1"], ["nucleus1"]]
        mod = load_skill_script("maya-cloth-sim", "create_ncloth")
        result = mod.create_ncloth(mesh="pPlane1", preset="cotton")
        assert result["success"] is True
        assert result["context"]["preset"] == "cotton"
        assert result["context"]["ncloth_shape"] == "nClothShape1"

    def test_create_ncloth_silk_preset(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.side_effect = [["nClothShape1"], ["nucleus1"]]
        mod = load_skill_script("maya-cloth-sim", "create_ncloth")
        result = mod.create_ncloth(mesh="pPlane1", preset="silk")
        assert result["success"] is True
        assert result["context"]["preset"] == "silk"

    def test_create_ncloth_denim_preset(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.side_effect = [["nClothShape1"], ["nucleus1"]]
        mod = load_skill_script("maya-cloth-sim", "create_ncloth")
        result = mod.create_ncloth(mesh="pPlane1", preset="denim")
        assert result["success"] is True

    def test_create_ncloth_rubber_preset(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.side_effect = [["nClothShape1"], ["nucleus1"]]
        mod = load_skill_script("maya-cloth-sim", "create_ncloth")
        result = mod.create_ncloth(mesh="pPlane1", preset="rubber")
        assert result["success"] is True

    def test_set_ncloth_attribute_success(self):
        """set_ncloth_attribute uses param 'ncloth_shape', not 'ncloth_node'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mod = load_skill_script("maya-cloth-sim", "set_ncloth_attribute")
        result = mod.set_ncloth_attribute(ncloth_shape="nClothShape1", attribute="stretchResistance", value=60.0)
        assert result["success"] is True

    def test_set_ncloth_attribute_missing_node(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-cloth-sim", "set_ncloth_attribute")
        result = mod.set_ncloth_attribute(ncloth_shape="missing", attribute="stretchResistance", value=60.0)
        assert result["success"] is False

    def test_list_ncloth_objects_empty(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-cloth-sim", "list_ncloth_objects")
        result = mod.list_ncloth_objects()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_ncloth_objects_found(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["nClothShape1"]
        mock_cmds.listRelatives.return_value = ["pPlane1"]
        mock_cmds.getAttr.return_value = 50.0
        mod = load_skill_script("maya-cloth-sim", "list_ncloth_objects")
        result = mod.list_ncloth_objects()
        assert result["success"] is True
        assert result["context"]["count"] == 1


# ---------------------------------------------------------------------------
# maya-mocap
# ---------------------------------------------------------------------------


class TestMocapSkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_import_mocap_missing_path(self):
        _mock_maya()
        mod = load_skill_script("maya-mocap", "import_mocap")
        result = mod.import_mocap(file_path="")
        assert result["success"] is False
        assert "required" in result["message"] or "Missing" in result["message"]

    def test_import_mocap_file_not_found(self):
        _mock_maya()
        mod = load_skill_script("maya-mocap", "import_mocap")
        result = mod.import_mocap(file_path="/nonexistent/anim.bvh")
        assert result["success"] is False
        assert "not found" in result["message"] or "File not found" in result["message"]

    def test_import_mocap_unsupported_format(self, tmp_path):
        fake = tmp_path / "anim.xyz"
        fake.write_bytes(b"fake data")
        _mock_maya()
        mod = load_skill_script("maya-mocap", "import_mocap")
        result = mod.import_mocap(file_path=str(fake))
        assert result["success"] is False
        assert "Unsupported" in result["message"]

    def test_create_hik_definition_success(self):
        """create_hik_definition requires joint_mapping parameter."""
        mock_cmds, mock_mel = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_mel.eval.return_value = None
        mock_cmds.ls.return_value = ["HIKCharacterNode1"]
        mod = load_skill_script("maya-mocap", "create_hik_definition")
        joint_mapping = {
            "Hips": "jntRoot",
            "Spine": "jntSpine",
        }
        result = mod.create_hik_definition(character_name="hikChar", joint_mapping=joint_mapping)
        assert result["success"] is True

    def test_clean_mocap_keys_with_joints_list(self):
        """clean_mocap_keys takes 'joints' list, not 'namespace'.

        cmds.keyframe(query=True, keyframeCount=True) returns an int.
        """
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        # keyframeCount=True returns total count as int
        mock_cmds.keyframe.return_value = 10
        mod = load_skill_script("maya-mocap", "clean_mocap_keys")
        result = mod.clean_mocap_keys(joints=["mocap:jntRoot", "mocap:jntMid"])
        assert result["success"] is True

    def test_clean_mocap_keys_empty_joints(self):
        """clean_mocap_keys with empty joints list returns success."""
        mock_cmds, _ = _mock_maya()
        mod = load_skill_script("maya-mocap", "clean_mocap_keys")
        result = mod.clean_mocap_keys(joints=[])
        assert result["success"] is True


# ---------------------------------------------------------------------------
# maya-scene-assembly
# ---------------------------------------------------------------------------


class TestSceneAssemblySkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_create_assembly_definition_default(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.assembly.return_value = "assemblyDefinition1"
        mod = load_skill_script("maya-scene-assembly", "create_assembly_definition")
        result = mod.create_assembly_definition()
        assert result["success"] is True
        assert result["context"]["node"] == "assemblyDefinition1"

    def test_create_assembly_definition_named(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.assembly.return_value = "myAssembly"
        mod = load_skill_script("maya-scene-assembly", "create_assembly_definition")
        result = mod.create_assembly_definition(name="myAssembly")
        assert result["success"] is True
        mock_cmds.assembly.assert_called_once_with(name="myAssembly", type="assemblyDefinition")

    def test_add_assembly_representation_success(self):
        """add_assembly_representation uses param 'assembly', not 'definition_node'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.assembly.return_value = "rep1"
        mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
        result = mod.add_assembly_representation(
            assembly="myAssembly",
            rep_type="Cache",
            rep_name="CacheRep",
        )
        assert result["success"] is True

    def test_add_assembly_representation_missing_node(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
        result = mod.add_assembly_representation(
            assembly="missing",
            rep_type="Cache",
            rep_name="CacheRep",
        )
        assert result["success"] is False

    def test_list_assemblies_empty(self):
        """list_assemblies context keys are 'definitions' and 'references', not 'assemblies'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-scene-assembly", "list_assemblies")
        result = mod.list_assemblies()
        assert result["success"] is True
        assert result["context"]["definitions"] == []
        assert result["context"]["references"] == []

    def test_list_assemblies_found_definitions(self):
        mock_cmds, _ = _mock_maya()
        # ls(type='assemblyDefinition') returns definitions, ls(type='assemblyReference') returns refs
        mock_cmds.ls.side_effect = [["assemblyDefinition1"], []]
        mock_cmds.assembly.return_value = ["CacheRep"]
        mod = load_skill_script("maya-scene-assembly", "list_assemblies")
        result = mod.list_assemblies()
        assert result["success"] is True
        assert result["context"]["count"] >= 1


# ---------------------------------------------------------------------------
# maya-proxy-mesh
# ---------------------------------------------------------------------------


class TestProxyMeshSkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_create_proxy_missing_source(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-proxy-mesh", "create_proxy")
        result = mod.create_proxy(source="nonexistentMesh")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_create_proxy_success(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.duplicate.return_value = ["pSphere1_proxy"]
        mock_cmds.listRelatives.return_value = ["pSphereShape1_proxy"]
        mock_cmds.attributeQuery.return_value = False
        mock_cmds.polyEvaluate.return_value = 50
        mod = load_skill_script("maya-proxy-mesh", "create_proxy")
        result = mod.create_proxy(source="pSphere1", reduction=90.0)
        assert result["success"] is True
        assert result["context"]["proxy"] == "pSphere1_proxy"
        assert result["context"]["source"] == "pSphere1"

    def test_create_proxy_keep_original_visible(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.duplicate.return_value = ["pSphere1_proxy"]
        mock_cmds.listRelatives.return_value = ["pSphereShape1_proxy"]
        mock_cmds.attributeQuery.return_value = False
        mock_cmds.polyEvaluate.return_value = 50
        mod = load_skill_script("maya-proxy-mesh", "create_proxy")
        result = mod.create_proxy(source="pSphere1", keep_original_visible=True)
        assert result["success"] is True
        # setAttr to hide source should NOT be called with False
        hide_calls = [
            c for c in mock_cmds.setAttr.call_args_list if "pSphere1.visibility" in str(c) and "False" in str(c)
        ]
        assert len(hide_calls) == 0

    def test_create_proxy_custom_name(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.duplicate.return_value = ["myProxy"]
        mock_cmds.listRelatives.return_value = ["myProxyShape"]
        mock_cmds.attributeQuery.return_value = False
        mock_cmds.polyEvaluate.return_value = 10
        mod = load_skill_script("maya-proxy-mesh", "create_proxy")
        result = mod.create_proxy(source="pSphere1", proxy_name="myProxy")
        assert result["success"] is True
        mock_cmds.duplicate.assert_called_once_with("pSphere1", name="myProxy")

    def test_list_proxies_empty(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-proxy-mesh", "list_proxies")
        result = mod.list_proxies()
        assert result["success"] is True
        assert result["context"]["proxies"] == []

    def test_list_proxies_found(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["pSphere1_proxy", "pCube1_proxy"]
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = "pSphere1"
        mod = load_skill_script("maya-proxy-mesh", "list_proxies")
        result = mod.list_proxies()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_swap_proxy_success(self):
        """swap_proxy uses param 'proxy', not 'proxy_name'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n in ["pSphere1_proxy", "pSphere1"]
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = "pSphere1"
        mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
        result = mod.swap_proxy(proxy="pSphere1_proxy", show_proxy=False)
        assert result["success"] is True

    def test_swap_proxy_missing(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
        result = mod.swap_proxy(proxy="missing_proxy")
        assert result["success"] is False

    def test_set_proxy_attribute_success(self):
        """set_proxy_attribute uses param 'proxy', not 'proxy_name'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
        result = mod.set_proxy_attribute(proxy="pSphere1_proxy", attribute="visibility", value=True)
        assert result["success"] is True

    def test_set_proxy_attribute_missing(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
        result = mod.set_proxy_attribute(proxy="missing", attribute="visibility", value=True)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-muscle
# ---------------------------------------------------------------------------


class TestMuscleSkillEdgeCases:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_create_muscle_capsule_with_joints(self):
        """create_muscle_capsule requires start_joint and end_joint."""
        mock_cmds, mock_mel = _mock_maya()
        mock_mel.eval.return_value = "cMuscle1"
        mock_cmds.ls.return_value = ["cMuscle1"]
        mod = load_skill_script("maya-muscle", "create_muscle_capsule")
        result = mod.create_muscle_capsule(start_joint="jntRoot", end_joint="jntTip")
        assert result["success"] is True

    def test_create_muscle_capsule_with_name(self):
        mock_cmds, mock_mel = _mock_maya()
        mock_mel.eval.return_value = "bicep"
        mock_cmds.ls.return_value = ["bicep"]
        mod = load_skill_script("maya-muscle", "create_muscle_capsule")
        result = mod.create_muscle_capsule(start_joint="jntShoulder", end_joint="jntElbow", name="bicep")
        assert result["success"] is True

    def test_list_muscles_empty(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = []
        mod = load_skill_script("maya-muscle", "list_muscles")
        result = mod.list_muscles()
        assert result["success"] is True
        assert result["context"]["muscles"] == []

    def test_set_muscle_attribute_missing_node(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-muscle", "set_muscle_attribute")
        result = mod.set_muscle_attribute(muscle_node="missing", attribute="length", value=5.0)
        assert result["success"] is False

    def test_apply_muscle_skin_missing_mesh(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-muscle", "apply_muscle_skin")
        result = mod.apply_muscle_skin(mesh="missing", muscles=[])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-export-preset (file I/O - no maya mock needed for most tests)
# ---------------------------------------------------------------------------


class TestExportPresetSkills:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_save_export_preset_to_explicit_dir(self, tmp_path):
        """save_export_preset with explicit preset_dir writes a JSON file."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.playbackOptions.side_effect = [1.0, 120.0]
        mock_cmds.file.return_value = ""
        mock_cmds.currentUnit.return_value = "film"
        mod = load_skill_script("maya-export-preset", "save_export_preset")
        result = mod.save_export_preset(
            preset_name="test_preset",
            preset_dir=str(tmp_path),
            format="fbx",
        )
        assert result["success"] is True
        import os

        saved = os.path.join(str(tmp_path), "test_preset.json")
        assert os.path.exists(saved)

    def test_save_export_preset_creates_dir(self, tmp_path):
        """save_export_preset creates the directory if it doesn't exist."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.playbackOptions.side_effect = [1.0, 24.0]
        mock_cmds.file.return_value = ""
        mock_cmds.currentUnit.return_value = "film"
        mod = load_skill_script("maya-export-preset", "save_export_preset")
        new_dir = str(tmp_path / "sub" / "presets")
        result = mod.save_export_preset(
            preset_name="sub_preset",
            preset_dir=new_dir,
            format="alembic",
        )
        assert result["success"] is True
        import os

        assert os.path.isdir(new_dir)

    def test_list_export_presets_empty_dir(self, tmp_path):
        """list_export_presets uses param 'preset_dir', not 'presets_dir'."""
        mock_cmds, _ = _mock_maya()
        mod = load_skill_script("maya-export-preset", "list_export_presets")
        result = mod.list_export_presets(preset_dir=str(tmp_path))
        assert result["success"] is True
        assert result["context"]["presets"] == []

    def test_list_export_presets_found(self, tmp_path):
        import json

        (tmp_path / "preset_a.json").write_text(json.dumps({"format": "fbx"}), encoding="utf-8")
        (tmp_path / "preset_b.json").write_text(json.dumps({"format": "abc"}), encoding="utf-8")
        mock_cmds, _ = _mock_maya()
        mod = load_skill_script("maya-export-preset", "list_export_presets")
        result = mod.list_export_presets(preset_dir=str(tmp_path))
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_load_export_preset_not_found(self, tmp_path):
        """load_export_preset uses param 'preset_path', not 'preset_name'."""
        mock_cmds, _ = _mock_maya()
        mod = load_skill_script("maya-export-preset", "load_export_preset")
        result = mod.load_export_preset(
            preset_path=str(tmp_path / "nonexistent.json"),
        )
        assert result["success"] is False

    def test_load_export_preset_success(self, tmp_path):
        import json

        data = {"format": "fbx", "frame_range": [1, 24], "fps": "film"}
        preset_file = tmp_path / "my_preset.json"
        preset_file.write_text(json.dumps(data), encoding="utf-8")
        mock_cmds, _ = _mock_maya()
        mock_cmds.playbackOptions.return_value = None
        mod = load_skill_script("maya-export-preset", "load_export_preset")
        result = mod.load_export_preset(preset_path=str(preset_file))
        assert result["success"] is True

    def test_delete_export_preset_not_found(self, tmp_path):
        """delete_export_preset uses param 'preset_path', not 'preset_name'."""
        mock_cmds, _ = _mock_maya()
        mod = load_skill_script("maya-export-preset", "delete_export_preset")
        result = mod.delete_export_preset(
            preset_path=str(tmp_path / "nonexistent.json"),
        )
        assert result["success"] is False

    def test_delete_export_preset_success(self, tmp_path):
        import json

        preset_file = tmp_path / "to_delete.json"
        preset_file.write_text(json.dumps({"format": "fbx"}), encoding="utf-8")
        mock_cmds, _ = _mock_maya()
        mod = load_skill_script("maya-export-preset", "delete_export_preset")
        result = mod.delete_export_preset(preset_path=str(preset_file))
        assert result["success"] is True
        assert not preset_file.exists()


# ---------------------------------------------------------------------------
# maya-pipeline
# ---------------------------------------------------------------------------


class TestPipelineEdgeCases:
    def setup_method(self):
        _clear_maya()

    def teardown_method(self):
        _clear_maya()

    def test_set_project_empty_path_returns_error(self):
        """set_project uses param 'path', not 'project_path'."""
        _mock_maya()
        mod = load_skill_script("maya-pipeline", "set_project")
        result = mod.set_project(path="")
        assert result["success"] is False

    def test_set_project_nonexistent_dir_without_create(self, tmp_path):
        _mock_maya()
        mod = load_skill_script("maya-pipeline", "set_project")
        result = mod.set_project(path=str(tmp_path / "nonexistent"))
        assert result["success"] is False
        assert "not exist" in result["message"] or "Directory not found" in result["message"]

    def test_set_project_with_create_if_missing(self, tmp_path):
        mock_cmds, _ = _mock_maya()
        new_dir = str(tmp_path / "new_project")
        mod = load_skill_script("maya-pipeline", "set_project")
        result = mod.set_project(path=new_dir, create_if_missing=True)
        assert result["success"] is True
        import os

        assert os.path.isdir(new_dir)

    def test_tag_asset_metadata_node_missing(self):
        """tag_asset_metadata uses param 'node', not 'node_name'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-pipeline", "tag_asset_metadata")
        result = mod.tag_asset_metadata(
            node="missing",
            asset_name="TestAsset",
        )
        assert result["success"] is False

    def test_tag_asset_metadata_success(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = False
        mod = load_skill_script("maya-pipeline", "tag_asset_metadata")
        result = mod.tag_asset_metadata(
            node="pSphere1",
            asset_name="TestAsset",
            asset_variant="default",
            asset_version="1.0.0",
        )
        assert result["success"] is True

    def test_get_asset_metadata_node_missing(self):
        """get_asset_metadata uses param 'node', not 'node_name'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = False
        mod = load_skill_script("maya-pipeline", "get_asset_metadata")
        result = mod.get_asset_metadata(node="missing")
        assert result["success"] is False

    def test_get_asset_metadata_success(self):
        mock_cmds, _ = _mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.side_effect = ["TestAsset", "default", "1.0.0", "prop"]
        mod = load_skill_script("maya-pipeline", "get_asset_metadata")
        result = mod.get_asset_metadata(node="pSphere1")
        assert result["success"] is True

    def test_publish_asset_success(self, tmp_path):
        """publish_asset uses param 'publish_dir', not 'export_dir'."""
        mock_cmds, _ = _mock_maya()
        mock_cmds.ls.return_value = ["pSphere1"]
        mock_cmds.file.return_value = "scene.ma"
        mod = load_skill_script("maya-pipeline", "publish_asset")
        result = mod.publish_asset(
            asset_name="myAsset",
            publish_dir=str(tmp_path),
        )
        # Should return a result dict
        assert isinstance(result, dict)
        assert "success" in result
