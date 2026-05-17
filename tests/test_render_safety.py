"""Regression tests for render output validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent


def _load_render_script(script_name: str):
    path = _ROOT / "src" / "dcc_mcp_maya" / "skills" / "maya-render" / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location("test_render_{}".format(script_name), str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("script_name", ["capture_viewport", "playblast"])
def test_empty_playblast_png_is_rejected(script_name: str, tmp_path: Path) -> None:
    mod = _load_render_script(script_name)
    empty_png = tmp_path / "empty.png"
    empty_png.write_bytes(b"")

    with pytest.raises(ValueError, match="EMPTY_PLAYBLAST"):
        mod._read_nonempty_png(str(empty_png))


@pytest.mark.parametrize("script_name", ["capture_viewport", "playblast"])
def test_nonempty_playblast_png_is_read(script_name: str, tmp_path: Path) -> None:
    mod = _load_render_script(script_name)
    png = tmp_path / "image.png"
    png.write_bytes(b"not-really-a-png")

    assert mod._read_nonempty_png(str(png)) == b"not-really-a-png"
