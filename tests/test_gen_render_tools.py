"""Drift test for ``tools/_gen_render_tools.py``.

``maya-render-setup`` advertises its ``tools.yaml`` as derived from the code,
but nothing enforced that: regenerating the manifest produced a diff against
the committed file (``plan_comp_outputs`` shipped ``affinity: main`` while the
generator said ``any``) and nobody noticed. These tests make the generator the
single source of truth.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "_gen_render_tools.py"


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("_gen_render_tools_uut", _TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_gen_render_tools_uut"] = module
    spec.loader.exec_module(module)
    return module


def test_committed_tools_yaml_matches_the_generator(gen):
    """The manifest must be exactly what the generator produces.

    A failing diff means someone edited ``tools.yaml`` by hand or changed a
    script signature without re-running the generator. Fix it by running
    ``python tools/_gen_render_tools.py`` and committing the result.
    """
    expected = gen.render()
    actual = gen.target_path().read_text(encoding="utf-8")

    assert actual == expected, (
        "maya-render-setup/tools.yaml has drifted from tools/_gen_render_tools.py. "
        "Re-run 'python tools/_gen_render_tools.py' and commit the result."
    )


def test_generator_spec_covers_every_script(gen):
    """Every script in the skill must have a SPEC entry, or it is unreachable."""
    scripts = sorted(path.stem for path in (gen.SKILL_ROOT / "scripts").glob("*.py") if path.stem != "__init__")

    assert sorted(gen.SPEC) == scripts


def test_plan_comp_outputs_runs_off_the_main_thread(gen):
    """It only composes path strings, so it must not queue behind Maya's UI pump."""
    execution, affinity, group, _annotations = gen.SPEC["plan_comp_outputs"]

    assert (execution, affinity) == ("sync", "any")
    assert group == "precomp"
