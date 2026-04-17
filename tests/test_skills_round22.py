"""Round 22 - Tests for maya-fluid, maya-ocean, maya-cloth-sim, maya-grooming,
maya-export-preset, maya-scripting, maya-utility, and maya-pipeline.

Covers all scripts across these skill domains.
Scripts use the project-standard pattern: named args, lazy imports of
``maya.cmds`` / ``maya.mel``, and return ``ToolResult.to_dict()``.
"""

# Import built-in modules
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir, script_name):
    """Load a skill script module by path."""
    script_path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "r22_{}_{}".format(skill_dir.replace("-", "_"), script_name),
        str(script_path),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_mock_maya(cmds_attrs=None, mel_attrs=None):
    mc = MagicMock()
    mock_mel = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mc
    mock_maya.mel = mock_mel
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mc, k, v)
    if mel_attrs:
        for k, v in mel_attrs.items():
            setattr(mock_mel, k, v)
    return mock_maya, mc, mock_mel


# ===========================================================================
# maya-fluid
# ===========================================================================


class TestCreateFluidContainer:
    def test_create_default(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = ["fluidShape1"]
        mc.listRelatives.return_value = ["fluid1"]
        mc.attributeQuery.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()

        assert result["success"] is True
        assert result["context"]["fluid_shape"] == "fluidShape1"
        assert result["context"]["fluid_transform"] == "fluid1"

    def test_create_with_name(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = ["fluidShape1"]
        mc.listRelatives.side_effect = [
            ["fluid1"],  # parent of fluidShape
            ["myFluidShape"],  # shapes after rename
        ]
        mc.rename.return_value = "myFluid"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container(name="myFluid", size_x=20, resolution=5)

        assert result["success"] is True
        mc.rename.assert_called_once()

    def test_create_no_fluid_shapes(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()

        assert result["success"] is True
        assert result["context"]["fluid_shape"] == ""

    def test_create_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.create3dFluid.side_effect = RuntimeError("no fluid plugin")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()

        assert result["success"] is False
        assert "no fluid plugin" in result["error"]


class TestSetFluidAttribute:
    def test_set_density(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "density", 0.5)

        assert result["success"] is True
        mc.setAttr.assert_called_with("fluidShape1.density", 0.5)

    def test_node_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("ghost", "density", 0.5)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("locked attr")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "density", 0.5)

        assert result["success"] is False
        assert "locked attr" in result["error"]


class TestListFluidContainers:
    def test_list_empty(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_container(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = ["fluidShape1"]
        mc.listRelatives.return_value = ["fluid1"]
        mc.attributeQuery.return_value = True
        mc.getAttr.return_value = [(10, 10, 10)]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()

        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["containers"][0]["shape"] == "fluidShape1"

    def test_list_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()

        assert result["success"] is False


class TestDeleteFluidContainer:
    def test_delete_ok(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("fluid1")

        assert result["success"] is True
        mc.delete.assert_called_with("fluid1")

    def test_delete_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("ghost")

        assert result["success"] is False

    def test_delete_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.delete.side_effect = RuntimeError("locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("fluid1")

        assert result["success"] is False


# ===========================================================================
# maya-ocean
# ===========================================================================


class TestCreateOcean:
    def test_create_default(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.polyPlane.return_value = ["ocean_surface", "polyPlane1"]
        mc.shadingNode.return_value = "ocean_surface_shader"
        mc.sets.return_value = "ocean_surface_SG"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "create_ocean")
            result = mod.create_ocean()

        assert result["success"] is True
        assert result["context"]["ocean_transform"] == "ocean_surface"
        assert result["context"]["shader_name"] == "ocean_surface_shader"

    def test_create_with_params(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.polyPlane.return_value = ["myOcean", "polyPlane1"]
        mc.shadingNode.return_value = "myOcean_shader"
        mc.sets.return_value = "myOcean_SG"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "create_ocean")
            result = mod.create_ocean(name="myOcean", subdivisions_x=100, scale=200.0)

        assert result["success"] is True
        call_args = mc.polyPlane.call_args
        # Python 3.7 compat: call_args[1] is kwargs dict, call_args[0] is args tuple
        call_kw = call_args[1] if call_args[1] else {}
        call_pos = call_args[0] if call_args[0] else ()
        assert call_kw.get("subdivisionsX") == 100 or 100 in call_pos

    def test_create_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.polyPlane.side_effect = RuntimeError("polyPlane failed")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "create_ocean")
            result = mod.create_ocean()

        assert result["success"] is False


class TestSetOceanAttribute:
    def test_set_wave_height(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "set_ocean_attribute")
            result = mod.set_ocean_attribute("oceanShader1", "waveHeight", 2.5)

        assert result["success"] is True
        mc.setAttr.assert_called_with("oceanShader1.waveHeight", 2.5)

    def test_node_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "set_ocean_attribute")
            result = mod.set_ocean_attribute("ghost", "waveHeight", 1.0)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("read only")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "set_ocean_attribute")
            result = mod.set_ocean_attribute("oceanShader1", "waveHeight", 2.5)

        assert result["success"] is False


class TestAddOceanWake:
    def test_add_wake_basic(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["oceanShader1_wake_loc"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("oceanShader1")

        assert result["success"] is True
        assert result["context"]["wake_locator"] == "oceanShader1_wake_loc"

    def test_add_wake_with_object(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["oceanShader1_wake_loc"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("oceanShader1", wake_object="boat1", wake_size=2.0)

        assert result["success"] is True
        mc.parentConstraint.assert_called()

    def test_shader_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("ghost")

        assert result["success"] is False

    def test_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.spaceLocator.side_effect = RuntimeError("locator fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("oceanShader1")

        assert result["success"] is False


class TestListOceanSurfaces:
    def test_list_empty(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "list_ocean_surfaces")
            result = mod.list_ocean_surfaces()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_shader(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = ["oceanShader1"]
        mc.listConnections.return_value = ["oceanSG1"]
        mc.sets.return_value = ["oceanPlane1"]
        mc.attributeQuery.return_value = True
        mc.getAttr.return_value = 1.5

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "list_ocean_surfaces")
            result = mod.list_ocean_surfaces()

        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["surfaces"][0]["shader"] == "oceanShader1"

    def test_list_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "list_ocean_surfaces")
            result = mod.list_ocean_surfaces()

        assert result["success"] is False


# ===========================================================================
# maya-cloth-sim
# ===========================================================================


class TestCreateNCloth:
    def test_create_ok(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1")

        assert result["success"] is True
        assert result["context"]["ncloth_shape"] == "nCloth1"
        assert result["context"]["nucleus"] == "nucleus1"

    def test_create_mesh_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("ghost")

        assert result["success"] is False

    def test_create_preset_denim(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1", preset="denim")

        assert result["success"] is True
        assert result["context"]["preset"] == "denim"

    def test_create_preset_silk(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1", preset="silk")

        assert result["success"] is True

    def test_create_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.nClothCreate.side_effect = RuntimeError("nucleus error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1")

        assert result["success"] is False


class TestSetNClothAttribute:
    def test_set_ok(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "set_ncloth_attribute")
            result = mod.set_ncloth_attribute("nCloth1", "thickness", 0.1)

        assert result["success"] is True
        mc.setAttr.assert_called_with("nCloth1.thickness", 0.1)

    def test_node_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "set_ncloth_attribute")
            result = mod.set_ncloth_attribute("ghost", "thickness", 0.1)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("read only")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "set_ncloth_attribute")
            result = mod.set_ncloth_attribute("nCloth1", "thickness", 0.1)

        assert result["success"] is False


class TestBakeClothCache:
    def test_bake_default_range(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.listRelatives.return_value = ["nClothMesh"]
        mc.mel = mock_mel

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("nCloth1")

        assert result["success"] is True
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 24

    def test_bake_explicit_range(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.listRelatives.return_value = ["nClothMesh"]
        mc.mel = mock_mel

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("nCloth1", start_frame=10, end_frame=50)

        assert result["success"] is True
        assert result["context"]["end_frame"] == 50

    def test_bake_node_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("ghost")

        assert result["success"] is False

    def test_bake_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.listRelatives.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("nCloth1")

        assert result["success"] is False


class TestListNClothObjects:
    def test_list_empty(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "list_ncloth_objects")
            result = mod.list_ncloth_objects()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_ncloth(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]
        mc.listRelatives.return_value = ["nClothMesh"]
        mc.listConnections.side_effect = [["nucleus1"], []]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "list_ncloth_objects")
            result = mod.list_ncloth_objects()

        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["cloth_objects"][0]["shape"] == "nCloth1"

    def test_list_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "list_ncloth_objects")
            result = mod.list_ncloth_objects()

        assert result["success"] is False


# ===========================================================================
# maya-grooming
# ===========================================================================


class TestCreateNHairSystem:
    def test_create_ok(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["hairSystem1"], ["follicle1", "follicle2"]]
        mc.mel = mock_mel

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("pSphere1")

        assert result["success"] is True
        assert result["context"]["hair_system"] == "hairSystem1"
        assert result["context"]["follicle_count"] == 2

    def test_create_mesh_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("ghost")

        assert result["success"] is False

    def test_create_custom_density(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["hairSystem1"], ["follicle1"]]
        mc.mel = mock_mel

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("pSphere1", uv_density=5, hair_length=10.0)

        assert result["success"] is True

    def test_create_exception(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.mel = mock_mel
        mock_mel.eval.side_effect = RuntimeError("no hair plugin")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("pSphere1")

        assert result["success"] is False


class TestSetNHairAttribute:
    def test_set_stiffness(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "set_nhair_attribute")
            result = mod.set_nhair_attribute("hairSystem1", "stiffness", 0.8)

        assert result["success"] is True
        mc.setAttr.assert_called_with("hairSystem1.stiffness", 0.8)

    def test_node_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "set_nhair_attribute")
            result = mod.set_nhair_attribute("ghost", "stiffness", 0.8)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "set_nhair_attribute")
            result = mod.set_nhair_attribute("hairSystem1", "stiffness", 0.8)

        assert result["success"] is False


class TestListHairSystems:
    def test_list_empty(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "list_hair_systems")
            result = mod.list_hair_systems()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_system(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.return_value = ["hairSystem1"]
        mc.listRelatives.return_value = ["hairSystem1Transform"]
        mc.listConnections.side_effect = [
            ["follicle1", "follicle2"],
            ["nucleus1"],
        ]
        mc.attributeQuery.return_value = True
        mc.getAttr.return_value = 0.5

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "list_hair_systems")
            result = mod.list_hair_systems()

        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["hair_systems"][0]["hair_system"] == "hairSystem1"

    def test_list_exception(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "list_hair_systems")
            result = mod.list_hair_systems()

        assert result["success"] is False


class TestAddNHairCache:
    def test_bake_default_range(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 48.0]
        mc.mel = mock_mel

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("hairSystem1")

        assert result["success"] is True
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 48

    def test_bake_explicit_range(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.mel = mock_mel

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("hairSystem1", start_frame=5, end_frame=30)

        assert result["success"] is True
        assert result["context"]["end_frame"] == 30

    def test_bake_node_not_found(self):
        mock_maya, mc, _ = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("ghost")

        assert result["success"] is False

    def test_bake_exception(self):
        mock_maya, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 48.0]
        mc.mel = mock_mel
        mc.select.side_effect = RuntimeError("select fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("hairSystem1")

        assert result["success"] is False


# ===========================================================================
# maya-export-preset
# ===========================================================================


class TestSaveExportPreset:
    def test_save_ok(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()
        mc.playbackOptions.side_effect = [1.0, 100.0]
        mc.file.return_value = "/tmp/scene.ma"
        mc.currentUnit.return_value = "film"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "save_export_preset")
            result = mod.save_export_preset(
                "my_fbx",
                preset_dir=str(tmp_path),
                format="fbx",
                frame_range=[1, 100],
            )

        assert result["success"] is True
        saved_path = result["context"]["preset_path"]
        assert os.path.isfile(saved_path)
        with open(saved_path) as fh:
            data = json.load(fh)
        assert data["preset_name"] == "my_fbx"
        assert data["frame_range"] == [1, 100]

    def test_save_default_frame_range(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.file.return_value = ""
        mc.currentUnit.return_value = "film"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "save_export_preset")
            result = mod.save_export_preset("auto_range", preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["preset_data"]["frame_range"] == [1, 24]

    def test_save_creates_nested_dir(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.file.return_value = ""
        mc.currentUnit.return_value = "film"
        new_dir = str(tmp_path / "nested" / "presets")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "save_export_preset")
            result = mod.save_export_preset("test", preset_dir=new_dir)

        assert result["success"] is True
        assert os.path.isdir(new_dir)

    def test_save_with_custom_settings(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.file.return_value = ""
        mc.currentUnit.return_value = "film"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "save_export_preset")
            result = mod.save_export_preset(
                "custom",
                preset_dir=str(tmp_path),
                custom_settings={"triangulate": True},
            )

        assert result["success"] is True
        with open(result["context"]["preset_path"]) as fh:
            data = json.load(fh)
        assert data["triangulate"] is True

    def test_save_exception(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()
        mc.playbackOptions.side_effect = RuntimeError("playback error")
        mc.file.return_value = ""
        mc.currentUnit.return_value = "film"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "save_export_preset")
            # frame_range provided so playbackOptions not called -> should succeed
            result = mod.save_export_preset("fail", preset_dir=str(tmp_path), frame_range=[1, 10])

        assert result["success"] is True


class TestLoadExportPreset:
    def _create_preset(self, tmp_path, name="test_preset"):
        preset_data = {
            "preset_name": name,
            "format": "fbx",
            "frame_range": [10, 50],
            "fps": "film",
        }
        path = str(tmp_path / "{}.json".format(name))
        with open(path, "w") as fh:
            json.dump(preset_data, fh)
        return path

    def test_load_ok(self, tmp_path):
        path = self._create_preset(tmp_path)
        mock_maya, mc, _ = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "load_export_preset")
            result = mod.load_export_preset(path)

        assert result["success"] is True
        assert result["context"]["preset_data"]["preset_name"] == "test_preset"
        mc.playbackOptions.assert_called()

    def test_load_no_apply_range(self, tmp_path):
        path = self._create_preset(tmp_path)
        mock_maya, mc, _ = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "load_export_preset")
            result = mod.load_export_preset(path, apply_frame_range=False)

        assert result["success"] is True
        mc.playbackOptions.assert_not_called()

    def test_load_file_not_found(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "load_export_preset")
            result = mod.load_export_preset(str(tmp_path / "ghost.json"))

        assert result["success"] is False


class TestListExportPresets:
    def test_list_empty_dir(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "list_export_presets")
            result = mod.list_export_presets(preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_no_dir(self, tmp_path):
        mock_maya, mc, _ = _make_mock_maya()
        non_existent = str(tmp_path / "no_such_dir")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "list_export_presets")
            result = mod.list_export_presets(preset_dir=non_existent)

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_presets(self, tmp_path):
        for i in range(3):
            path = str(tmp_path / "preset_{}.json".format(i))
            with open(path, "w") as fh:
                json.dump({"preset_name": "preset_{}".format(i), "format": "fbx", "frame_range": [1, 10]}, fh)

        mock_maya, mc, _ = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "list_export_presets")
            result = mod.list_export_presets(preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_list_invalid_json(self, tmp_path):
        bad = str(tmp_path / "bad.json")
        with open(bad, "w") as fh:
            fh.write("not json {{")

        mock_maya, mc, _ = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "list_export_presets")
            result = mod.list_export_presets(preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["presets"][0].get("error") is not None


class TestDeleteExportPreset:
    def test_delete_ok(self, tmp_path):
        path = str(tmp_path / "my_preset.json")
        with open(path, "w") as fh:
            json.dump({}, fh)

        mod = _load_script("maya-export-preset", "delete_export_preset")
        result = mod.delete_export_preset(path)

        assert result["success"] is True
        assert not os.path.exists(path)
        assert result["context"]["preset_name"] == "my_preset"

    def test_delete_file_not_found(self, tmp_path):
        mod = _load_script("maya-export-preset", "delete_export_preset")
        result = mod.delete_export_preset(str(tmp_path / "ghost.json"))

        assert result["success"] is False

    def test_delete_exception(self, tmp_path):
        # Pass a directory instead of a file to trigger an error path
        mod = _load_script("maya-export-preset", "delete_export_preset")
        result = mod.delete_export_preset(str(tmp_path))

        assert result["success"] is False


# ===========================================================================
# maya-scripting / execute_mel
# ===========================================================================


class TestExecuteMel:
    def test_empty_code_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("")
        assert result["success"] is False

    def test_whitespace_only_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("   ")
        assert result["success"] is False

    def test_successful_mel(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.return_value = "sphere1"
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("polySphere -n sphere1;")
        assert result["success"] is True
        assert result["context"]["output"] == "sphere1"

    def test_mel_returns_none(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.return_value = None
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("print 1;")
        assert result["success"] is True
        assert result["context"]["output"] == ""

    def test_mel_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.side_effect = RuntimeError("MEL error")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("badMEL;")
        assert result["success"] is False
        assert "MEL error" in str(result)


# ===========================================================================
# maya-scripting / execute_python
# ===========================================================================


class TestExecutePython:
    def test_empty_code_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("")
        assert result["success"] is False

    def test_valid_python(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("x = 1 + 1")
        assert result["success"] is True

    def test_capture_output(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("print('hello')", capture_output=True)
        assert result["success"] is True
        assert "hello" in result["context"]["stdout"]

    def test_syntax_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("def broken(")
        assert result["success"] is False

    def test_runtime_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("raise ValueError('boom')")
        assert result["success"] is False
        assert "boom" in str(result)


# ===========================================================================
# maya-scripting / list_mel_procedures
# ===========================================================================


class TestListMelProcedures:
    def test_returns_list(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.side_effect = [
            "",  # warm-up whatIs call
            ["doCreateSphere", "doPolyCube", "doSomethingElse"],  # globalProcs()
        ]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "list_mel_procedures")
            result = mod.list_mel_procedures()
        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_pattern_filter(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.side_effect = [
            "",
            ["doPolyCube", "doPolySphere", "doSomething"],
        ]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "list_mel_procedures")
            result = mod.list_mel_procedures(pattern="poly")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_limit_applied(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.side_effect = [
            "",
            ["proc{}".format(i) for i in range(100)],
        ]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "list_mel_procedures")
            result = mod.list_mel_procedures(limit=10)
        assert result["success"] is True
        assert result["context"]["count"] <= 10

    def test_mel_eval_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mock_mel.eval.side_effect = RuntimeError("not available")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-scripting", "list_mel_procedures")
            result = mod.list_mel_procedures()
        assert result["success"] is False


# ===========================================================================
# maya-scripting / get_script_node
# ===========================================================================


class TestGetScriptNode:
    def test_no_name_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("")
        assert result["success"] is False

    def test_get_existing(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.getAttr.side_effect = lambda plug: "print('hi')" if ".before" in plug else 0
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("myScript", action="get")
        assert result["success"] is True
        assert result["context"]["script_node"]["name"] == "myScript"

    def test_get_nonexistent(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("missing", action="get")
        assert result["success"] is False

    def test_create_script_node(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.scriptNode.return_value = "myScript"
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("myScript", action="create", script="print(1)")
        assert result["success"] is True
        assert result["context"]["script_node"]["name"] == "myScript"

    def test_create_missing_script_body(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("myScript", action="create")
        assert result["success"] is False

    def test_delete_script_node(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("myScript", action="delete")
        assert result["success"] is True

    def test_unknown_action(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-scripting", "get_script_node")
            result = mod.get_script_node("myScript", action="fly")
        assert result["success"] is False


# ===========================================================================
# maya-utility / create_utility_node
# ===========================================================================


class TestCreateUtilityNode:
    def test_no_type_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("")
        assert result["success"] is False

    def test_create_without_name(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.shadingNode.return_value = "multiplyDivide1"
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("multiplyDivide")
        assert result["success"] is True
        assert result["context"]["node_name"] == "multiplyDivide1"
        assert result["context"]["node_type"] == "multiplyDivide"

    def test_create_with_name(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.shadingNode.return_value = "multiplyDivide1"
        mc.rename.return_value = "myMult"
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("multiplyDivide", name="myMult")
        assert result["success"] is True
        mc.shadingNode.assert_called_once_with("multiplyDivide", asUtility=True)
        mc.rename.assert_called_once_with("multiplyDivide1", "myMult")

    def test_create_with_connection(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.shadingNode.return_value = "rev1"
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("reverse", connect_from="lambert1.outColor")
        assert result["success"] is True
        mc.connectAttr.assert_called_once()

    def test_shading_node_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.shadingNode.side_effect = RuntimeError("invalid type")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("badType")
        assert result["success"] is False


# ===========================================================================
# maya-utility / get_scene_statistics
# ===========================================================================


class TestGetSceneStatistics:
    def test_basic_stats(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.side_effect = lambda **kw: (
            ["pSphere1", "pCube1"]
            if kw.get("type") == "mesh"
            else ["transform1"]
            if kw.get("type") == "transform"
            else ["n1", "n2", "n3", "n4", "n5"]
        )
        mc.polyEvaluate.return_value = 100
        mc.memory.return_value = 2048
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics()
        assert result["success"] is True
        ctx = result["context"]
        assert "mesh_count" in ctx
        assert "poly_vertex_count" in ctx

    def test_no_memory(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = []
        mc.polyEvaluate.return_value = 0
        mc.memory.side_effect = RuntimeError("no memory")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics(include_memory=True)
        assert result["success"] is True
        assert result["context"]["memory_mb"] is None

    def test_extra_node_types(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = []
        mc.polyEvaluate.return_value = 0
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics(node_types=["camera", "joint"])
        assert result["success"] is True
        assert "camera_count" in result["context"]

    def test_ls_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene not loaded")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics()
        assert result["success"] is False


# ===========================================================================
# maya-utility / list_node_connections
# ===========================================================================


class TestListNodeConnections:
    def test_no_node_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "list_node_connections")
            result = mod.list_node_connections("")
        assert result["success"] is False

    def test_node_not_found(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "list_node_connections")
            result = mod.list_node_connections("missing")
        assert result["success"] is False

    def test_both_directions(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        # connections=True, plugs=True -> [dst0, src0, dst1, src1, ...]
        mc.listConnections.side_effect = [
            ["lambert1.outColor", "file1.outColor"],  # incoming pairs
            ["lambert1.color", "shaderGlow1.glowColor"],  # outgoing pairs
        ]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "list_node_connections")
            result = mod.list_node_connections("lambert1", direction="both")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_incoming_only(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.listConnections.return_value = ["lambert1.outColor", "file1.outColor"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "list_node_connections")
            result = mod.list_node_connections("lambert1", direction="incoming")
        assert result["success"] is True

    def test_outgoing_only(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.listConnections.return_value = ["lambert1.color", "shaderGlow1.glowColor"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "list_node_connections")
            result = mod.list_node_connections("lambert1", direction="outgoing")
        assert result["success"] is True

    def test_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.listConnections.side_effect = RuntimeError("oops")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "list_node_connections")
            result = mod.list_node_connections("lambert1")
        assert result["success"] is False


# ===========================================================================
# maya-utility / clean_scene
# ===========================================================================


class TestCleanScene:
    def test_dry_run(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.side_effect = lambda type=None: (
            ["unknownNode1"] if type == "unknown" else ["layer1"] if type == "displayLayer" else []
        )
        mc.unknownPlugin.return_value = ["plug1"]
        mc.editDisplayLayerMembers.return_value = []
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "clean_scene")
            result = mod.clean_scene(dry_run=True)
        assert result["success"] is True
        assert result["context"]["removed_count"] == 0
        assert result["context"]["flagged_count"] > 0

    def test_remove_unknown_nodes(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.side_effect = lambda type=None: (
            ["unknownNode1"] if type == "unknown" else ["defaultLayer"] if type == "displayLayer" else []
        )
        mc.unknownPlugin.return_value = []
        mc.editDisplayLayerMembers.return_value = ["obj1"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "clean_scene")
            result = mod.clean_scene(
                remove_unknown_nodes=True,
                remove_unknown_plugins=False,
                remove_empty_display_layers=True,
            )
        assert result["success"] is True
        mc.delete.assert_called()

    def test_no_cleanup_needed(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = []
        mc.unknownPlugin.return_value = []
        mc.editDisplayLayerMembers.return_value = ["obj1"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "clean_scene")
            result = mod.clean_scene()
        assert result["success"] is True
        assert result["context"]["removed_count"] == 0

    def test_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("crash")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-utility", "clean_scene")
            result = mod.clean_scene()
        assert result["success"] is False


# ===========================================================================
# maya-pipeline / set_project
# ===========================================================================


class TestSetProject:
    def test_no_path_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "set_project")
            result = mod.set_project("")
        assert result["success"] is False

    def test_nonexistent_dir_no_create(self, tmp_path):
        missing = str(tmp_path / "nonexistent" / "proj")
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "set_project")
            result = mod.set_project(missing)
        assert result["success"] is False

    def test_nonexistent_dir_with_create(self, tmp_path):
        new_dir = str(tmp_path / "new_project")
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "set_project")
            result = mod.set_project(new_dir, create_if_missing=True)
        assert result["success"] is True
        assert os.path.isdir(new_dir)

    def test_existing_dir(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "set_project")
            result = mod.set_project(str(tmp_path))
        assert result["success"] is True
        assert result["context"]["project_path"] == str(tmp_path)

    def test_cmds_workspace_exception(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        mc.workspace.side_effect = RuntimeError("workspace error")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "set_project")
            result = mod.set_project(str(tmp_path))
        assert result["success"] is False


# ===========================================================================
# maya-pipeline / publish_asset
# ===========================================================================


class TestPublishAsset:
    def test_no_asset_name_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("", publish_dir="/tmp")
        assert result["success"] is False

    def test_no_publish_dir_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("hero", publish_dir="")
        assert result["success"] is False

    def test_nothing_selected_error(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("hero", publish_dir=str(tmp_path))
        assert result["success"] is False

    def test_publish_ma_format(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("hero", publish_dir=str(tmp_path), format="ma")
        assert result["success"] is True
        assert result["context"]["version"] == 1
        assert result["context"]["publish_path"].endswith(".ma")

    def test_publish_fbx_format(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("hero", publish_dir=str(tmp_path), format="fbx")
        assert result["success"] is True
        assert result["context"]["publish_path"].endswith(".fbx")

    def test_explicit_version(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = ["pCube1"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("prop", publish_dir=str(tmp_path), format="ma", version=5)
        assert result["success"] is True
        assert result["context"]["version"] == 5

    def test_unsupported_format(self, tmp_path):
        mm, mc, mock_mel = _make_mock_maya()
        mc.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = _load_script("maya-pipeline", "publish_asset")
            result = mod.publish_asset("hero", publish_dir=str(tmp_path), format="abc")
        assert result["success"] is False


# ===========================================================================
# maya-pipeline / tag_asset_metadata
# ===========================================================================


class TestTagAssetMetadata:
    def test_no_node_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "tag_asset_metadata")
            result = mod.tag_asset_metadata("")
        assert result["success"] is False

    def test_node_not_found(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "tag_asset_metadata")
            result = mod.tag_asset_metadata("missing", asset_name="hero")
        assert result["success"] is False

    def test_no_metadata_provided(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "tag_asset_metadata")
            result = mod.tag_asset_metadata("pSphere1")
        assert result["success"] is False

    def test_tag_creates_attr_if_missing(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = False  # attr doesn't exist -> must addAttr
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "tag_asset_metadata")
            result = mod.tag_asset_metadata("pSphere1", asset_name="hero", asset_version="v001")
        assert result["success"] is True
        assert mc.addAttr.call_count >= 2

    def test_tag_existing_attr(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = True  # attr already exists -> no addAttr
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "tag_asset_metadata")
            result = mod.tag_asset_metadata("pSphere1", pipeline_step="rigging")
        assert result["success"] is True
        mc.addAttr.assert_not_called()

    def test_setattr_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = True
        mc.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "tag_asset_metadata")
            result = mod.tag_asset_metadata("pSphere1", asset_name="hero")
        assert result["success"] is False


# ===========================================================================
# maya-pipeline / get_asset_metadata
# ===========================================================================


class TestGetAssetMetadata:
    def test_no_node_error(self):
        mm, mc, mock_mel = _make_mock_maya()
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "get_asset_metadata")
            result = mod.get_asset_metadata("")
        assert result["success"] is False

    def test_node_not_found(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "get_asset_metadata")
            result = mod.get_asset_metadata("missing")
        assert result["success"] is False

    def test_no_attrs_tagged(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "get_asset_metadata")
            result = mod.get_asset_metadata("pSphere1")
        assert result["success"] is True
        assert result["context"]["tagged_count"] == 0

    def test_some_attrs_tagged(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True

        def attr_exists(attr, node, exists):
            return attr in ("asset_name", "asset_version")

        mc.attributeQuery.side_effect = attr_exists
        mc.getAttr.side_effect = lambda plug: "hero" if "asset_name" in plug else "v003"
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "get_asset_metadata")
            result = mod.get_asset_metadata("pSphere1")
        assert result["success"] is True
        assert result["context"]["tagged_count"] == 2
        assert result["context"]["metadata"]["asset_name"] == "hero"

    def test_getattr_exception(self):
        mm, mc, mock_mel = _make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.side_effect = RuntimeError("attr query failed")
        with patch.dict(sys.modules, {"maya": mm, "maya.cmds": mc}):
            mod = _load_script("maya-pipeline", "get_asset_metadata")
            result = mod.get_asset_metadata("pSphere1")
        assert result["success"] is False
