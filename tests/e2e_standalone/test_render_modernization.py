"""Real mayapy coverage for bounded Arnold rendering controls."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


def _require_mtoa():
    try:
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa", quiet=True)
    except Exception as exc:
        pytest.skip("MtoA is unavailable: {}".format(exc))
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        pytest.skip("MtoA is not loaded")


def test_arnold_aov_exposure_and_sampling_round_trip_native_scene_state():
    _new_scene()
    _require_mtoa()
    aovs = _load_script("maya-render", "set_aov")
    exposure = _load_script("maya-render", "set_exposure")
    settings = _load_script("maya-render", "set_render_settings")
    aov_name = "dccMcpTypedBeauty"

    before = aovs.set_aov(action="list")
    assert before["success"] is True, before
    if any(item["name"] == aov_name for item in before["context"]["aovs"]):
        removed = aovs.set_aov(action="remove", name=aov_name)
        assert removed["success"] is True, removed

    added = aovs.set_aov(action="add", name=aov_name, data_type="rgba")
    assert added["success"] is True, added
    assert added["context"]["aov"]["name"] == aov_name
    assert added["context"]["aov"]["data_type"] == "rgba"

    light_shape = cmds.directionalLight(name="dccMcpTypedRenderKeyShape")
    written_exposure = exposure.set_exposure(target=light_shape, exposure=3.0)
    assert written_exposure["success"] is True, written_exposure
    assert written_exposure["context"]["exposure"] == 3.0

    written_settings = settings.set_render_settings(
        renderer="arnold",
        width=320,
        height=240,
        aa_samples=3,
    )
    assert written_settings["success"] is True, written_settings
    assert written_settings["context"]["verified"] is True

    removed = aovs.set_aov(action="remove", name=aov_name)
    assert removed["success"] is True, removed
    assert all(item["name"] != aov_name for item in removed["context"]["aovs"])
