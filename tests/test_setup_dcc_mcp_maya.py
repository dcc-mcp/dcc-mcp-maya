"""Tests for the agent-facing Maya setup script."""

from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.7-3.10
    import tomli as tomllib

SETUP_SCRIPT = Path(__file__).parent.parent / "skills" / "dcc-mcp-maya-setup" / "scripts" / "setup_dcc_mcp_maya.py"
_SPEC = importlib.util.spec_from_file_location("setup_dcc_mcp_maya", str(SETUP_SCRIPT))
setup_dcc_mcp_maya = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(setup_dcc_mcp_maya)


def test_setup_skill_core_requirement_matches_package_metadata():
    project = tomllib.loads((SETUP_SCRIPT.parents[3] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    canonical = next(item for item in project["dependencies"] if item.startswith("dcc-mcp-core"))

    assert setup_dcc_mcp_maya.CORE_REQUIREMENT == canonical


def test_install_package_selects_one_pip_requirement_for_python_310(monkeypatch, tmp_path):
    commands = []

    monkeypatch.setattr(
        setup_dcc_mcp_maya.subprocess,
        "check_output",
        lambda *args, **kwargs: "3.10\n",
    )
    monkeypatch.setattr(
        setup_dcc_mcp_maya,
        "run",
        lambda command, cwd=None: commands.append(command),
    )

    setup_dcc_mcp_maya.install_package(Path("mayapy"), "pypi", tmp_path, skip_install=False)

    assert commands[1][5:] == ["pip"]


def test_install_package_keeps_python_37_compatible_pip(monkeypatch, tmp_path):
    commands = []

    monkeypatch.setattr(
        setup_dcc_mcp_maya.subprocess,
        "check_output",
        lambda *args, **kwargs: "3.7\n",
    )
    monkeypatch.setattr(
        setup_dcc_mcp_maya,
        "run",
        lambda command, cwd=None: commands.append(command),
    )

    setup_dcc_mcp_maya.install_package(Path("mayapy"), "pypi", tmp_path, skip_install=False)

    assert commands[1][5:] == ["pip<25"]


@pytest.mark.parametrize(
    ("core_version", "accepted"),
    (
        ("0.19.45", True),
        ("0.19.45.0", True),
        ("0.19.45+local", True),
        ("0.19.44", False),
        ("1.0.0", False),
        ("1.0.0rc1", False),
        ("1.0.0.dev1", False),
        ("garbage 0.19.45", False),
    ),
)
def test_verify_import_enforces_canonical_core_requirement(monkeypatch, core_version, accepted):
    commands = []
    monkeypatch.setattr(setup_dcc_mcp_maya, "run", lambda command, cwd=None: commands.append(command))

    setup_dcc_mcp_maya.verify_import(Path("mayapy"))

    monkeypatch.setitem(sys.modules, "dcc_mcp_maya", SimpleNamespace(__version__="0.9.25"))
    monkeypatch.setitem(sys.modules, "dcc_mcp_core", SimpleNamespace(__version__=core_version))
    if accepted:
        exec(commands[0][2], {})
    else:
        with pytest.raises((SystemExit, ValueError)):
            exec(commands[0][2], {})


def test_skip_install_core_failure_stops_before_writing_snippets(monkeypatch, tmp_path):
    mayapy = tmp_path / "mayapy"
    monkeypatch.setattr(
        setup_dcc_mcp_maya,
        "parse_args",
        lambda _argv: Namespace(
            mayapy=str(mayapy),
            source="local",
            mcp_url="http://127.0.0.1:9765/mcp",
            server_name="maya",
            out_dir="out",
            skip_install=True,
        ),
    )
    monkeypatch.setattr(setup_dcc_mcp_maya, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(setup_dcc_mcp_maya, "resolve_mayapy", lambda _explicit: mayapy)
    monkeypatch.setattr(setup_dcc_mcp_maya, "install_package", lambda *_args: None)
    monkeypatch.setattr(
        setup_dcc_mcp_maya,
        "verify_import",
        lambda _mayapy: (_ for _ in ()).throw(SystemExit("unsupported Core")),
    )
    writes = []
    monkeypatch.setattr(setup_dcc_mcp_maya, "write_mcp_snippets", lambda *_args: writes.append(True))

    with pytest.raises(SystemExit, match="unsupported Core"):
        setup_dcc_mcp_maya.main([])

    assert writes == []
