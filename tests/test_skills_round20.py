"""Round 20 - Tests for maya-fluid, maya-ocean, maya-cloth-sim, maya-grooming, maya-export-preset skills."""

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
        "{}.{}".format(skill_dir.replace("-", "_"), script_name),
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_mock_maya(cmds_attrs=None):
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    return mock_maya, mock_cmds


# ===========================================================================
# maya-fluid
# ===========================================================================

class TestCreateFluidContainer:
    def test_create_default(self):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.ls.return_value = ["fluidShape1"]
        mc.listRelatives.side_effect = [
            ["fluid1"],       # parent of fluidShape
            ["myFluidShape"], # shapes after rename
        ]
        mc.rename.return_value = "myFluid"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container(name="myFluid", size_x=20, resolution=5)

        assert result["success"] is True
        mc.rename.assert_called_once()

    def test_create_no_fluid_shapes(self):
        mock_maya, mc = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()

        assert result["success"] is True
        assert result["context"]["fluid_shape"] == ""

    def test_create_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.create3dFluid.side_effect = RuntimeError("no fluid plugin")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()

        assert result["success"] is False
        assert "no fluid plugin" in result["error"]


class TestSetFluidAttribute:
    def test_set_density(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "density", 0.5)

        assert result["success"] is True
        mc.setAttr.assert_called_with("fluidShape1.density", 0.5)

    def test_node_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("ghost", "density", 0.5)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("locked attr")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "density", 0.5)

        assert result["success"] is False
        assert "locked attr" in result["error"]


class TestListFluidContainers:
    def test_list_empty(self):
        mock_maya, mc = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_container(self):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()

        assert result["success"] is False


class TestDeleteFluidContainer:
    def test_delete_ok(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("fluid1")

        assert result["success"] is True
        mc.delete.assert_called_with("fluid1")

    def test_delete_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("ghost")

        assert result["success"] is False

    def test_delete_exception(self):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.polyPlane.return_value = ["myOcean", "polyPlane1"]
        mc.shadingNode.return_value = "myOcean_shader"
        mc.sets.return_value = "myOcean_SG"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "create_ocean")
            result = mod.create_ocean(name="myOcean", subdivisions_x=100, scale=200.0)

        assert result["success"] is True
        call_kwargs = mc.polyPlane.call_args
        assert call_kwargs.kwargs.get("subdivisionsX") == 100 or 100 in call_kwargs.args

    def test_create_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.polyPlane.side_effect = RuntimeError("polyPlane failed")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "create_ocean")
            result = mod.create_ocean()

        assert result["success"] is False


class TestSetOceanAttribute:
    def test_set_wave_height(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "set_ocean_attribute")
            result = mod.set_ocean_attribute("oceanShader1", "waveHeight", 2.5)

        assert result["success"] is True
        mc.setAttr.assert_called_with("oceanShader1.waveHeight", 2.5)

    def test_node_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "set_ocean_attribute")
            result = mod.set_ocean_attribute("ghost", "waveHeight", 1.0)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("read only")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "set_ocean_attribute")
            result = mod.set_ocean_attribute("oceanShader1", "waveHeight", 2.5)

        assert result["success"] is False


class TestAddOceanWake:
    def test_add_wake_basic(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["oceanShader1_wake_loc"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("oceanShader1")

        assert result["success"] is True
        assert result["context"]["wake_locator"] == "oceanShader1_wake_loc"

    def test_add_wake_with_object(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["oceanShader1_wake_loc"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("oceanShader1", wake_object="boat1", wake_size=2.0)

        assert result["success"] is True
        mc.parentConstraint.assert_called()

    def test_shader_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("ghost")

        assert result["success"] is False

    def test_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.spaceLocator.side_effect = RuntimeError("locator fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "add_ocean_wake")
            result = mod.add_ocean_wake("oceanShader1")

        assert result["success"] is False


class TestListOceanSurfaces:
    def test_list_empty(self):
        mock_maya, mc = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-ocean", "list_ocean_surfaces")
            result = mod.list_ocean_surfaces()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_shader(self):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1")

        assert result["success"] is True
        assert result["context"]["ncloth_shape"] == "nCloth1"
        assert result["context"]["nucleus"] == "nucleus1"

    def test_create_mesh_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("ghost")

        assert result["success"] is False

    def test_create_preset_denim(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1", preset="denim")

        assert result["success"] is True
        assert result["context"]["preset"] == "denim"

    def test_create_preset_silk(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["nCloth1"], ["nucleus1"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1", preset="silk")

        assert result["success"] is True

    def test_create_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.nClothCreate.side_effect = RuntimeError("nucleus error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "create_ncloth")
            result = mod.create_ncloth("pPlane1")

        assert result["success"] is False


class TestSetNClothAttribute:
    def test_set_ok(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "set_ncloth_attribute")
            result = mod.set_ncloth_attribute("nCloth1", "thickness", 0.1)

        assert result["success"] is True
        mc.setAttr.assert_called_with("nCloth1.thickness", 0.1)

    def test_node_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "set_ncloth_attribute")
            result = mod.set_ncloth_attribute("ghost", "thickness", 0.1)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("read only")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "set_ncloth_attribute")
            result = mod.set_ncloth_attribute("nCloth1", "thickness", 0.1)

        assert result["success"] is False


class TestBakeClothCache:
    def test_bake_default_range(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.listRelatives.return_value = ["nClothMesh"]
        mc.mel = MagicMock()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("nCloth1")

        assert result["success"] is True
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 24

    def test_bake_explicit_range(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.listRelatives.return_value = ["nClothMesh"]
        mc.mel = MagicMock()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("nCloth1", start_frame=10, end_frame=50)

        assert result["success"] is True
        assert result["context"]["end_frame"] == 50

    def test_bake_node_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("ghost")

        assert result["success"] is False

    def test_bake_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.listRelatives.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "bake_cloth_cache")
            result = mod.bake_cloth_cache("nCloth1")

        assert result["success"] is False


class TestListNClothObjects:
    def test_list_empty(self):
        mock_maya, mc = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-cloth-sim", "list_ncloth_objects")
            result = mod.list_ncloth_objects()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_ncloth(self):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["hairSystem1"], ["follicle1", "follicle2"]]
        mc.mel = MagicMock()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("pSphere1")

        assert result["success"] is True
        assert result["context"]["hair_system"] == "hairSystem1"
        assert result["context"]["follicle_count"] == 2

    def test_create_mesh_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("ghost")

        assert result["success"] is False

    def test_create_custom_density(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["hairSystem1"], ["follicle1"]]
        mc.mel = MagicMock()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("pSphere1", uv_density=5, hair_length=10.0)

        assert result["success"] is True

    def test_create_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.mel = MagicMock()
        mc.mel.eval.side_effect = RuntimeError("no hair plugin")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "create_nhair_system")
            result = mod.create_nhair_system("pSphere1")

        assert result["success"] is False


class TestSetNHairAttribute:
    def test_set_stiffness(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "set_nhair_attribute")
            result = mod.set_nhair_attribute("hairSystem1", "stiffness", 0.8)

        assert result["success"] is True
        mc.setAttr.assert_called_with("hairSystem1.stiffness", 0.8)

    def test_node_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "set_nhair_attribute")
            result = mod.set_nhair_attribute("ghost", "stiffness", 0.8)

        assert result["success"] is False

    def test_setattr_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "set_nhair_attribute")
            result = mod.set_nhair_attribute("hairSystem1", "stiffness", 0.8)

        assert result["success"] is False


class TestListHairSystems:
    def test_list_empty(self):
        mock_maya, mc = _make_mock_maya()
        mc.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "list_hair_systems")
            result = mod.list_hair_systems()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_one_system(self):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "list_hair_systems")
            result = mod.list_hair_systems()

        assert result["success"] is False


class TestAddNHairCache:
    def test_bake_default_range(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 48.0]
        mc.mel = MagicMock()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("hairSystem1")

        assert result["success"] is True
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 48

    def test_bake_explicit_range(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.mel = MagicMock()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("hairSystem1", start_frame=5, end_frame=30)

        assert result["success"] is True
        assert result["context"]["end_frame"] == 30

    def test_bake_node_not_found(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-grooming", "add_nhair_cache")
            result = mod.add_nhair_cache("ghost")

        assert result["success"] is False

    def test_bake_exception(self):
        mock_maya, mc = _make_mock_maya()
        mc.objExists.return_value = True
        mc.playbackOptions.side_effect = [1.0, 48.0]
        mc.mel = MagicMock()
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
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
        mc.playbackOptions.side_effect = [1.0, 24.0]
        mc.file.return_value = ""
        mc.currentUnit.return_value = "film"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "save_export_preset")
            result = mod.save_export_preset("auto_range", preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["preset_data"]["frame_range"] == [1, 24]

    def test_save_creates_nested_dir(self, tmp_path):
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()
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
        mock_maya, mc = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "load_export_preset")
            result = mod.load_export_preset(path)

        assert result["success"] is True
        assert result["context"]["preset_data"]["preset_name"] == "test_preset"
        mc.playbackOptions.assert_called()

    def test_load_no_apply_range(self, tmp_path):
        path = self._create_preset(tmp_path)
        mock_maya, mc = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "load_export_preset")
            result = mod.load_export_preset(path, apply_frame_range=False)

        assert result["success"] is True
        mc.playbackOptions.assert_not_called()

    def test_load_file_not_found(self, tmp_path):
        mock_maya, mc = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "load_export_preset")
            result = mod.load_export_preset(str(tmp_path / "ghost.json"))

        assert result["success"] is False


class TestListExportPresets:
    def test_list_empty_dir(self, tmp_path):
        mock_maya, mc = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "list_export_presets")
            result = mod.list_export_presets(preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_no_dir(self, tmp_path):
        mock_maya, mc = _make_mock_maya()
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

        mock_maya, mc = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = _load_script("maya-export-preset", "list_export_presets")
            result = mod.list_export_presets(preset_dir=str(tmp_path))

        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_list_invalid_json(self, tmp_path):
        bad = str(tmp_path / "bad.json")
        with open(bad, "w") as fh:
            fh.write("not json {{")

        mock_maya, mc = _make_mock_maya()

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
