"""Native translator readback; run with mayapy and an installed Maya USD plugin."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e

_USD_TRIANGLE = """#usda 1.0
(
    defaultPrim = "Asset"
    metersPerUnit = 0.01
    upAxis = "Y"
)
def Xform "Asset"
{
    def Mesh "Triangle"
    {
        int[] faceVertexCounts = [3]
        int[] faceVertexIndices = [0, 1, 2]
        point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 2, 0)]
        uniform token subdivisionScheme = "none"
    }
}
"""


@pytest.mark.parametrize("extension", ["obj", "usda"])
def test_import_file_reads_native_mesh(tmp_path, extension):
    _new_scene()
    path = tmp_path / ("asset." + extension)
    source = _USD_TRIANGLE if extension == "usda" else "o Triangle\nv 0 0 0\nv 1 0 0\nv 0 2 0\nf 1 2 3\n"
    path.write_text(source, encoding="utf-8")
    result = _load_script("maya-geometry", "import_file").import_file(str(path), namespace="acceptance")
    assert result["success"], result
    assert result["context"]["count"] > 0
    meshes = cmds.ls(type="mesh", long=True) or []
    assert len(meshes) == 1
    assert cmds.polyEvaluate(meshes[0], face=True) == 1
    assert cmds.polyEvaluate(meshes[0], vertex=True) == 3
    assert all(cmds.objExists(node) for node in result["context"]["imported_nodes"])
    if extension == "usda":
        assert result["context"]["file_type"] == "USD Import"
        assert not cmds.ls(type="mayaUsdProxyShape")
