"""Unit / up-axis semantics for the maya-import-to-scene skill (PIP-3930).

OBJ carries neither a unit nor an up-axis, so an undeclared import is read in
whatever the target scene happens to use: a metres-authored asset lands 100x
too small in a centimetre scene, and a Z-up asset lies down in a Y-up scene.
Geometry stays fully intact, so nothing looks broken. These tests lock in that
the tool converts when told, and says so out loud when not.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call, load_and_call_with_mel

_SCRIPT = "maya-import-to-scene/scripts/import_to_scene.py"


def _make_asset(path: str, fmt: str = "obj", name: str = "cal") -> dict:
    return {"id": "abc123", "name": name, "path": path, "format": fmt, "size_bytes": 100, "metadata": {}}


def _semantics_cmds(unit="cm", up="y", before=None, after=None):
    """Return a cmds mock that also reports a target scene unit and up axis."""
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    _before = before or []
    _after = after if after is not None else ["|Mesh", "|Mesh|MeshShape"]
    calls = [0]

    def ls_side_effect(*args, **kwargs):
        if kwargs.get("long") or (args and args[0] == "-long"):
            calls[0] += 1
            return list(_before) if calls[0] == 1 else list(_after)
        return []

    cmds.ls.side_effect = ls_side_effect
    cmds.objectType.return_value = "transform"
    cmds.xform.return_value = [1.0, 1.0, 1.0]
    cmds.currentUnit.return_value = unit
    cmds.upAxis.return_value = up
    return cmds


def _xform_calls_with(cmds, keyword):
    """xform calls that *set* ``keyword``, skipping ``query=True`` reads.

    Uses ``call[1]`` rather than ``call.kwargs``: the latter only exists on
    Python 3.8+, and this module must also run under the Maya 2022 (py3.7)
    CI lane.
    """
    out = []
    for call in cmds.xform.call_args_list:
        kwargs = call[1]
        if kwargs.get("query") is True:
            continue
        if keyword in kwargs:
            out.append(call)
    return out


# ---------------------------------------------------------------------------
# Undeclared semantics must be reported, not swallowed
# ---------------------------------------------------------------------------


def test_undeclared_obj_unit_warns_with_the_target_unit(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)))

    assert result["success"] is True, result
    ctx = result["context"]
    assert any("declares no unit" in w for w in ctx["warnings"])
    assert any("'cm'" in w for w in ctx["warnings"])
    assert ctx["source_unit"] is None
    assert ctx["unit_conversion_factor"] == 1.0


def test_undeclared_obj_up_axis_warns_and_imports_as_authored(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)))

    assert result["success"] is True, result
    assert any("declares no up-axis" in w for w in result["context"]["warnings"])
    assert result["context"]["axis_conversion"] == "none"


def test_warnings_are_mirrored_to_the_script_editor(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)))

    warned = [str(c) for c in cmds.warning.call_args_list]
    assert any("declares no unit" in c for c in warned)
    assert any("declares no up-axis" in c for c in warned)


def test_warnings_are_surfaced_in_the_success_message(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)))

    assert "declares no unit" in result["message"]


# ---------------------------------------------------------------------------
# Declared semantics must convert
# ---------------------------------------------------------------------------


def test_declared_metres_into_centimetre_scene_scales_by_100(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="m")

    assert result["success"] is True, result
    ctx = result["context"]
    assert ctx["source_unit"] == "m"
    assert ctx["target_unit"] == "cm"
    assert ctx["unit_conversion_factor"] == 100.0
    assert ctx["unit_scale"] == 100.0
    assert not any("declares no unit" in w for w in ctx["warnings"])
    scales = _xform_calls_with(cmds, "scale")
    assert scales
    assert scales[0][1]["scale"] == [100.0, 100.0, 100.0]


def test_declared_millimetres_into_metre_scene_scales_down(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="m", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="mm")

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 0.001


def test_matching_source_and_target_unit_is_a_no_op(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="cm")

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 1.0
    assert _xform_calls_with(cmds, "scale") == []


def test_declared_z_up_into_y_up_scene_rotates(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_up_axis="z")

    assert result["success"] is True, result
    ctx = result["context"]
    assert ctx["source_up_axis"] == "z"
    assert ctx["target_up_axis"] == "y"
    assert ctx["axis_conversion"] == "z_to_y"
    assert _xform_calls_with(cmds, "rotation")


def test_declared_y_up_into_z_up_scene_rotates_the_other_way(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(up="z")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_up_axis="y")

    assert result["success"] is True, result
    assert result["context"]["axis_conversion"] == "y_to_z"


def test_matching_up_axis_does_not_rotate(tmp_path):
    for up in ("y", "z"):
        path = tmp_path / "cal{}.obj".format(up)
        path.write_bytes(b"OBJ")
        cmds = _semantics_cmds(up=up)

        result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_up_axis=up)

        assert result["success"] is True, result
        assert result["context"]["axis_conversion"] == "none"
        assert _xform_calls_with(cmds, "rotation") == []


def test_manual_unit_scale_composes_with_declared_conversion(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="m", unit_scale=2.0)

    assert result["success"] is True, result
    assert result["context"]["unit_scale"] == 200.0
    scales = _xform_calls_with(cmds, "scale")
    assert scales[0][1]["scale"] == [200.0, 200.0, 200.0]


# ---------------------------------------------------------------------------
# Bad input fails loudly, before the scene is touched
# ---------------------------------------------------------------------------


def test_unknown_source_unit_is_a_hard_error(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds()

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="parsec")

    assert result["success"] is False
    assert "source_unit" in result["message"]
    cmds.file.assert_not_called()


def test_unknown_source_up_axis_is_a_hard_error(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds()

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_up_axis="w")

    assert result["success"] is False
    assert "source_up_axis" in result["message"]
    cmds.file.assert_not_called()


def test_require_semantics_blocks_undeclared_obj(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds()

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), require_semantics=True)

    assert result["success"] is False
    cmds.file.assert_not_called()


def test_require_semantics_passes_when_both_declared(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call(
        _SCRIPT,
        cmds,
        "main",
        asset=_make_asset(str(path)),
        source_unit="m",
        source_up_axis="z",
        require_semantics=True,
    )

    assert result["success"] is True, result
    assert result["context"]["warnings"] == []
    assert result["context"]["unit_conversion_factor"] == 100.0
    assert result["context"]["axis_conversion"] == "z_to_y"


def test_require_semantics_does_not_block_formats_that_carry_metadata(tmp_path):
    """FBX describes its own unit and axis, so there is nothing to demand."""
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call_with_mel(
        _SCRIPT, cmds, MagicMock(), "main", asset=_make_asset(str(path), "fbx"), require_semantics=True
    )

    assert result["success"] is True, result
    assert result["context"]["warnings"] == []


# ---------------------------------------------------------------------------
# Degraded scenes
# ---------------------------------------------------------------------------


def test_fbx_does_not_warn_when_semantics_undeclared(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call_with_mel(_SCRIPT, cmds, MagicMock(), "main", asset=_make_asset(str(path), "fbx"))

    assert result["success"] is True, result
    assert result["context"]["warnings"] == []


def test_fbx_ignores_a_declared_unit_instead_of_double_scaling(tmp_path):
    """FBX carries its own units, so a declared source_unit must not scale again.

    Measured on Maya 2026: a metres-authored FBX (UnitScaleFactor 100) lands at
    100 cm in a centimetre scene -- the importer already converted. Applying the
    declared factor on top would scale twice, which is the same silent 100x
    class of error this tool exists to prevent, just on another format.
    """
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call_with_mel(
        _SCRIPT, cmds, MagicMock(), "main", asset=_make_asset(str(path), "fbx"), source_unit="m"
    )

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 1.0
    assert _xform_calls_with(cmds, "scale") == []
    warnings = result["context"]["warnings"]
    assert any("source_unit='m' was ignored" in w for w in warnings)


def test_fbx_ignores_a_declared_up_axis_instead_of_double_rotating(tmp_path):
    """Same double-apply guard for the up axis.

    Measured on Maya 2026: a Y-up FBX imported into a Z-up scene lands its
    height on Z -- the importer already aligned it, so rotating again would
    double-rotate.
    """
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call_with_mel(
        _SCRIPT, cmds, MagicMock(), "main", asset=_make_asset(str(path), "fbx"), source_up_axis="z"
    )

    assert result["success"] is True, result
    assert result["context"]["axis_conversion"] == "none"
    warnings = result["context"]["warnings"]
    assert any("source_up_axis='z' was ignored" in w for w in warnings)


def test_require_semantics_still_passes_for_fbx_with_a_declaration(tmp_path):
    """An ignored-declaration note is advisory and must not trip require_semantics.

    require_semantics refuses imports made under an *unauthorised* assumption.
    A self-describing format is not that, so a pipeline using the flag must not
    start failing on FBX that previously passed.
    """
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call_with_mel(
        _SCRIPT,
        cmds,
        MagicMock(),
        "main",
        asset=_make_asset(str(path), "fbx"),
        source_unit="m",
        source_up_axis="z",
        require_semantics=True,
    )

    assert result["success"] is True, result


def test_usd_ignores_declared_semantics_too(tmp_path):
    path = tmp_path / "hero.usd"
    path.write_bytes(b"USD")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call_with_mel(
        _SCRIPT, cmds, MagicMock(), "main", asset=_make_asset(str(path), "usd"), source_unit="m"
    )

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 1.0
    assert any("source_unit='m' was ignored" in w for w in result["context"]["warnings"])


def test_declared_unit_without_a_target_unit_warns_and_skips_conversion(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="m")

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 1.0
    assert any("source_unit='m' was ignored" in w for w in result["context"]["warnings"])


def test_declared_unit_with_an_unconvertible_target_unit_warns(tmp_path):
    """A target unit outside the conversion table must not silently drop source_unit.

    Maya reports eight linear units; if the table falls behind, a declared
    source_unit would be dropped with no conversion and no warning -- the exact
    silent failure this tool exists to prevent. The fallback branch keeps that
    gap loud.
    """
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="parsec", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="m")

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 1.0
    warnings = result["context"]["warnings"]
    assert warnings, "declared source_unit was dropped without a warning"
    assert any("source_unit='m' was ignored" in w for w in warnings)


def test_declared_miles_into_centimetre_scene_scales(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="mi", source_up_axis="y")

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 160934.4
    assert result["context"]["warnings"] == []


def test_declared_unit_into_a_mile_target_scene_converts(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="mi", up="y")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_unit="m", source_up_axis="y")

    assert result["success"] is True, result
    assert result["context"]["unit_conversion_factor"] == 100.0 / 160934.4
    assert result["context"]["warnings"] == []


def test_declared_up_axis_without_a_target_axis_warns_and_skips_rotation(tmp_path):
    path = tmp_path / "cal.obj"
    path.write_bytes(b"OBJ")
    cmds = _semantics_cmds(unit="cm", up="")

    result = load_and_call(_SCRIPT, cmds, "main", asset=_make_asset(str(path)), source_up_axis="z")

    assert result["success"] is True, result
    assert result["context"]["axis_conversion"] == "none"
    assert any("target scene up-axis" in w for w in result["context"]["warnings"])
