"""Exercise the release assembler without project/dev dependency side effects."""

from __future__ import annotations

import copy
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def release_steps():
    return yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())["jobs"]["build-mod"]["steps"]


def preparation(steps):
    consumer = next(i for i, step in enumerate(steps) if "python packaging/assemble_mod.py" in step.get("run", ""))
    commands = [step["run"] for step in steps[:consumer] if "run" in step]
    assert len(commands) == 1, "assembler preparation must precede its consumer"
    command = shlex.split(commands[0])
    assert command[:2] == ["pip", "install"]
    return command


def test_release_declares_assembler_dependency_before_consumption():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    requirement = next(value for value in project["dependencies"] if value.startswith("packaging>="))
    assert requirement in preparation(release_steps())


@pytest.mark.parametrize("mutation", ["missing", "late"])
def test_missing_or_late_preparation_is_not_a_valid_release_plan(mutation):
    steps = copy.deepcopy(release_steps())
    index = next(i for i, step in enumerate(steps) if step.get("name") == "Install assemble dependencies")
    step = steps.pop(index)
    if mutation == "late":
        steps.append(step)
    with pytest.raises(AssertionError, match="precede"):
        preparation(steps)


@pytest.mark.packaging
def test_clean_release_preparation_builds_actual_module_archives(tmp_path):
    """Network gate: DCC_MCP_RELEASE_PYTHON selects the workflow's Python."""
    steps = release_steps()
    version = next(step["with"]["python-version"] for step in steps if "setup-python@" in step.get("uses", ""))
    interpreter = os.environ.get("DCC_MCP_RELEASE_PYTHON", sys.executable)
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "DCC_MCP_LOG_DIR"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIP_CONFIG_FILE"] = os.devnull
    environment["PIP_INDEX_URL"] = "https://pypi.org/simple"
    environment.pop("PIP_EXTRA_INDEX_URL", None)

    def run(label, argv, timeout=180):
        result = subprocess.run(
            argv, env=environment, cwd=str(ROOT), capture_output=True, universal_newlines=True, timeout=timeout
        )
        (tmp_path / (label + ".stdout")).write_text(result.stdout, encoding="utf-8")
        (tmp_path / (label + ".stderr")).write_text(result.stderr, encoding="utf-8")
        (tmp_path / (label + ".json")).write_text(
            json.dumps({"argv": argv, "exit": result.returncode}), encoding="utf-8"
        )
        return result

    selected = run(
        "python-version", [interpreter, "-I", "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"]
    )
    assert selected.returncode == 0 and selected.stdout.strip() == version, selected.stdout + selected.stderr
    venv = tmp_path / "release-venv"
    created = run("venv", [interpreter, "-I", "-m", "venv", str(venv)])
    assert created.returncode == 0, created.stderr
    python = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    consumer = [python, "-I", str(ROOT / "packaging/assemble_mod.py")]
    # Missing or late preparation must fail at the real consumer, not pass
    # because pytest/the adapter leaked dependencies into the child environment.
    missing = run("before-preparation", consumer + ["--help"])
    assert missing.returncode != 0 and "No module named 'packaging'" in missing.stderr
    command = preparation(steps)
    installed = run("preparation", [python, "-I", "-m", "pip"] + command[1:])
    assert installed.returncode == 0, installed.stdout + installed.stderr
    inventory = run("inventory", [python, "-I", "-m", "pip", "list", "--format=json"])
    assert inventory.returncode == 0, inventory.stderr
    names = {entry["name"].lower().replace("_", "-") for entry in json.loads(inventory.stdout)}
    assert {"dcc-mcp-maya", "pytest", "build", "hatchling"}.isdisjoint(names), names
    prepared = run("prepared-consumer", consumer + ["--help"])
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    # Use the actual workflow assembler arguments, substituting only runner
    # inputs and the test-owned output directory (never a release publication).
    script = next(step["run"] for step in steps if "python packaging/assemble_mod.py" in step.get("run", ""))
    platform = {"win32": "win64", "linux": "linux", "darwin": "macos"}[sys.platform]
    script = script[script.index("python packaging/assemble_mod.py") :].replace("\\\n", " ")
    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    script = script.replace("${{ matrix.platform }}", platform).replace('"$VERSION"', project_version)
    args = shlex.split(script)[2:]
    args[args.index("--output") + 1] = str(tmp_path / "artifacts")
    built = run("assembly", consumer + args, timeout=600)
    assert built.returncode == 0, built.stdout + built.stderr
    for variant in ("portable", "pipeline"):
        assert len(list((tmp_path / "artifacts" / variant).glob("*.zip"))) == 1
