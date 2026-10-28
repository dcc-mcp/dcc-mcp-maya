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


def test_capture_prefers_exact_host_result_over_extra_candidates(tmp_path):
    mod = _load_render_script("capture_viewport")
    actual = tmp_path / "capture.0000.PNG"
    actual.write_bytes(b"actual")
    (tmp_path / "capture.0001.png").write_bytes(b"extra")
    assert mod._capture_image_path(str(tmp_path), str(actual)) == str(actual)


def test_capture_rejects_returned_subdirectory_image(tmp_path):
    mod = _load_render_script("capture_viewport")
    child = tmp_path / "nested"
    child.mkdir()
    image = child / "capture.png"
    image.write_bytes(b"not-direct-output")
    with pytest.raises(RuntimeError, match="invalid captured PNG path"):
        mod._capture_image_path(str(tmp_path), str(image))


@pytest.mark.parametrize("kind", ["external", "symlink", "broken_symlink", "nested", "non_png", "directory"])
def test_existing_invalid_return_never_falls_back_to_another_capture(tmp_path, kind):
    mod = _load_render_script("capture_viewport")
    capture = tmp_path / "private"
    capture.mkdir()
    (capture / "capture.0000.png").write_bytes(b"different-image")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"external-image")
    if kind == "external":
        returned = outside
    elif kind in ("symlink", "broken_symlink"):
        returned = capture / "returned.png"
        try:
            returned.symlink_to(outside if kind == "symlink" else tmp_path / "missing.png")
        except (PermissionError, NotImplementedError) as exc:
            pytest.skip("Filesystem cannot create the symlink fixture: {}".format(exc))
    elif kind == "nested":
        (capture / "nested").mkdir()
        returned = capture / "nested" / "returned.png"
        returned.write_bytes(b"nested-image")
    elif kind == "non_png":
        returned = capture / "returned.txt"
        returned.write_bytes(b"text")
    else:
        returned = capture / "returned.png"
        returned.mkdir()
    with pytest.raises(RuntimeError, match="invalid captured PNG path"):
        mod._capture_image_path(str(capture), str(returned))
    assert outside.read_bytes() == b"external-image"


def test_nonexistent_sequence_template_still_resolves_actual_image(tmp_path):
    mod = _load_render_script("capture_viewport")
    actual = tmp_path / "capture.0000.png"
    actual.write_bytes(b"image")
    assert mod._capture_image_path(str(tmp_path), str(tmp_path / "capture.####.png")) == str(actual)
