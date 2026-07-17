from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya.procedural_house_showcase import (
    HouseShowcaseContractError,
    build_house_showcase,
    design_house_showcase,
    showcase_spec_to_dict,
)


def test_showcase_design_is_deterministic_and_covers_every_style() -> None:
    first = design_house_showcase(seed=42, position=(10, 0, -2), spacing=8, frame_count=72)
    second = design_house_showcase(seed=42, position=(10, 0, -2), spacing=8, frame_count=72)

    assert first == second
    assert [entry.style for entry in first.entries] == ["cabin", "cottage", "modern", "townhouse"]
    assert [entry.seed for entry in first.entries] == [42, 43, 44, 45]
    assert sum(entry.position[0] for entry in first.entries) / 4 == 10
    assert first.entries[0].reveal_frame == 1
    assert showcase_spec_to_dict(first)["frame_count"] == 72


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"spacing": 5}, "spacing must be between"),
        ({"spacing": float("inf")}, "finite number"),
        ({"frame_count": 12}, "frame_count must be between"),
        ({"frame_count": True}, "frame_count must be an integer"),
        ({"position": (1, 2)}, "exactly three"),
    ],
)
def test_showcase_design_rejects_invalid_contracts(kwargs: dict, message: str) -> None:
    with pytest.raises(HouseShowcaseContractError, match=message):
        design_house_showcase(seed=1, **kwargs)


def test_build_showcase_reuses_house_builder_and_stages_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    cmds = MagicMock()
    cmds.objExists.return_value = False
    cmds.group.side_effect = lambda **kwargs: kwargs["name"]
    cmds.shadingNode.side_effect = lambda _kind, **kwargs: kwargs["name"]
    cmds.sets.side_effect = lambda *_args, **kwargs: kwargs.get("name")
    cmds.polyPlane.return_value = ["DemoGround"]
    cmds.listRelatives.return_value = ["|Demo|DemoGround|DemoGroundShape"]
    cmds.camera.return_value = ["DemoCamera", "DemoCameraShape"]
    cmds.aimConstraint.return_value = ["DemoAimConstraint"]
    cmds.parent.side_effect = lambda child, _parent: [child]
    cmds.getPanel.return_value = []
    built = []

    def fake_build(_cmds, house_spec, name=None):
        built.append((house_spec, name))
        return {
            "graph": "{}Shape".format(name),
            "transform": "|{}".format(name),
            "bounds": [-1, 0, -1, 1, 5, 1],
            "part_count": len(house_spec.parts),
            "node_count": 8,
        }

    # Patch the exact globals used by this imported function. Other integration
    # tests deliberately reload skill modules, so a dotted sys.modules lookup
    # may otherwise target a newer module object during a full-suite run.
    monkeypatch.setitem(build_house_showcase.__globals__, "build_house_graph", fake_build)
    spec = design_house_showcase(seed=100, name="Demo", frame_count=48)

    result = build_house_showcase(cmds, spec)

    assert [house_spec.style for house_spec, _name in built] == ["cabin", "cottage", "modern", "townhouse"]
    assert result["root"] == "Demo"
    assert result["house_count"] == 4
    assert result["ground_shape"] == "|Demo|DemoGround|DemoGroundShape"
    assert result["camera"] == "DemoCamera"
    assert result["frame_range"] == [1, 48]
    assert result["capture"]["tool"] == "capture_playblast_sequence"
    assert result["capture"]["arguments"]["camera"] == "DemoCamera"
    assert cmds.setKeyframe.call_count > 10
    assert all(keyframe.kwargs.get("attribute") != "visibility" for keyframe in cmds.setKeyframe.call_args_list)
    cmds.currentTime.assert_called_once_with(48, edit=True)
