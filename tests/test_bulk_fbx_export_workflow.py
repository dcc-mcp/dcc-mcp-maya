"""Mocked regression for bulk sphere creation + per-object FBX export.

Mirrors the agent workflow (skills-first, no ``execute_python``):
``create_sphere`` → ``set_transform`` → ``set_selection`` → ``export_fbx``
repeated ten times. Runs entirely on ``MagicMock`` so CI does not need Maya.

Live gateway election / process crash behaviour remains covered by
``tests/test_gateway_failover.py`` (currently skipped pending issue #58) and
manual ``mayapy`` / interactive sessions.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from pathlib import Path
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call, load_and_call_with_mel


def test_ten_spheres_transform_select_export_fbx_mocked(tmp_path: Path) -> None:
    """Ten typed-tool cycles succeed; each FBX path is non-empty on disk."""
    export_root = tmp_path / "fbx_out"
    export_root.mkdir()

    for i in range(1, 11):
        ball = f"mcp_rbd_ball_{i:02d}"
        fbx_path = export_root / f"PROJ_mcpRbd_ball_{i:02d}_v001.fbx"

        cmds_create = MagicMock()
        cmds_create.polySphere.return_value = [f"pSphere{i}", f"pSphereShape{i}"]
        cmds_create.rename.return_value = ball

        r_create = load_and_call(
            "maya-primitives/scripts/create_sphere.py",
            cmds_create,
            "main",
            radius=0.08 + 0.01 * i,
            name=ball,
        )
        assert r_create["success"] is True, r_create
        assert r_create["context"]["object_name"] == ball

        cmds_xform = MagicMock()
        cmds_xform.objExists.return_value = True
        r_xform = load_and_call(
            "maya-primitives/scripts/set_transform.py",
            cmds_xform,
            "main",
            object_name=ball,
            translate=[float(i) * 2.0, 0.0, 0.0],
        )
        assert r_xform["success"] is True, r_xform

        cmds_sel = MagicMock()
        r_sel = load_and_call(
            "maya-scene/scripts/set_selection.py",
            cmds_sel,
            "main",
            objects=[ball],
        )
        assert r_sel["success"] is True, r_sel
        cmds_sel.select.assert_called_once()

        cmds_exp = MagicMock()
        mel = MagicMock()
        cmds_exp.pluginInfo.return_value = False

        def _write_file(path: str, **_kwargs: object) -> str:
            Path(path).write_bytes(b"FBX")
            return str(path)

        cmds_exp.file.side_effect = _write_file

        r_exp = load_and_call_with_mel(
            "maya-geometry/scripts/export_fbx.py",
            cmds_exp,
            mel,
            "main",
            path=str(fbx_path),
            selected_only=True,
            bake_animation=False,
        )
        assert r_exp["success"] is True, r_exp
        assert fbx_path.is_file()
        assert fbx_path.stat().st_size > 0

    written = sorted(export_root.glob("*.fbx"))
    assert len(written) == 10
