"""Tests for the agent-facing Maya setup script."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SETUP_SCRIPT = Path(__file__).parent.parent / "skills" / "dcc-mcp-maya-setup" / "scripts" / "setup_dcc_mcp_maya.py"
_SPEC = importlib.util.spec_from_file_location("setup_dcc_mcp_maya", str(SETUP_SCRIPT))
setup_dcc_mcp_maya = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(setup_dcc_mcp_maya)


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
