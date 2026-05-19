"""Prepare a Maya mayapy environment for dcc-mcp-maya MCP use."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_GATEWAY_URL = "http://127.0.0.1:9765/mcp"
DEFAULT_DIRECT_URL = "http://127.0.0.1:8765/mcp"


def run(command: list[str], cwd: Optional[Path] = None) -> None:
    print("+ " + " ".join(command))
    subprocess.check_call(command, cwd=str(cwd) if cwd else None)


def candidate_mayapy_paths() -> Iterable[Path]:
    env_value = os.environ.get("MAYAPY") or os.environ.get("DCC_MCP_MAYA_MAYAPY")
    if env_value:
        yield Path(env_value)

    path_match = shutil.which("mayapy")
    if path_match:
        yield Path(path_match)

    if os.name == "nt":
        program_files = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
        ]
        for root in program_files:
            if not root:
                continue
            autodesk = Path(root) / "Autodesk"
            for year in range(2027, 2019, -1):
                yield autodesk / ("Maya%s" % year) / "bin" / "mayapy.exe"
    else:
        for year in range(2027, 2019, -1):
            yield Path("/Applications/Autodesk/maya%s/Maya.app/Contents/bin/mayapy" % year)
            yield Path("/usr/autodesk/maya%s/bin/mayapy" % year)


def resolve_mayapy(explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists():
            return path
        raise SystemExit("mayapy does not exist: %s" % path)

    seen = set()
    for path in candidate_mayapy_paths():
        expanded = path.expanduser()
        key = str(expanded).lower()
        if key in seen:
            continue
        seen.add(key)
        if expanded.exists():
            return expanded

    raise SystemExit(
        "Could not find mayapy. Re-run with --mayapy, or set MAYAPY to the full path."
    )


def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() and (parent / "src" / "dcc_mcp_maya").exists():
            return parent
    return Path.cwd()


def install_package(mayapy: Path, source: str, repo_root: Path, skip_install: bool) -> None:
    if skip_install:
        print("Skipping pip install because --skip-install was passed.")
        return

    run([str(mayapy), "-m", "ensurepip", "--upgrade"])
    run(
        [
            str(mayapy),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip<25; python_version<'3.8'",
            "pip; python_version>='3.8'",
        ]
    )

    if source == "local":
        run([str(mayapy), "-m", "pip", "install", "-e", ".[sidecar]"], cwd=repo_root)
    elif source == "pypi":
        run([str(mayapy), "-m", "pip", "install", "--upgrade", "dcc-mcp-maya[sidecar]"])
    else:
        raise SystemExit("Unknown source: %s" % source)


def verify_import(mayapy: Path) -> None:
    code = (
        "import dcc_mcp_maya; "
        "print('dcc-mcp-maya', dcc_mcp_maya.__version__); "
        "import dcc_mcp_core; "
        "print('dcc-mcp-core import ok')"
    )
    run([str(mayapy), "-c", code])


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("Wrote %s" % path)


def write_mcp_snippets(out_dir: Path, server_name: str, mcp_url: str) -> None:
    payload = {"mcpServers": {server_name: {"url": mcp_url}}}
    write_json(out_dir / "mcp-streamable-http.json", payload)

    direct_payload = {"mcpServers": {server_name: {"url": DEFAULT_DIRECT_URL}}}
    write_json(out_dir / "mcp-direct-8765.json", direct_payload)

    smoke_prompt = """Use the Maya MCP server. First call dcc_capability_manifest with loaded_only=false.
Then load the maya-primitives skill, create a sphere named mcp_setup_smoke_sphere
with radius 2, list scene objects, and tell me the MCP URL and created object name.
Use typed tools where available and avoid execute_python unless no typed tool fits.
"""
    smoke_path = out_dir / "smoke-prompt.txt"
    smoke_path.write_text(smoke_prompt, encoding="utf-8")
    print("Wrote %s" % smoke_path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mayapy", help="Full path to Autodesk Maya mayapy.")
    parser.add_argument(
        "--source",
        choices=["local", "pypi"],
        default="local",
        help="Install from this checkout or from PyPI. Default: local.",
    )
    parser.add_argument(
        "--mcp-url",
        default=DEFAULT_GATEWAY_URL,
        help="MCP URL to write into generated host config. Default: plugin gateway URL.",
    )
    parser.add_argument(
        "--server-name",
        default="maya",
        help="MCP server name in generated config. Default: maya.",
    )
    parser.add_argument(
        "--out-dir",
        default=".dcc-mcp/agent-setup",
        help="Directory for generated MCP snippets. Default: .dcc-mcp/agent-setup.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Only verify imports and write MCP snippets.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = find_repo_root()
    mayapy = resolve_mayapy(args.mayapy)
    out_dir = (repo_root / args.out_dir).resolve()

    print("Repository: %s" % repo_root)
    print("mayapy: %s" % mayapy)
    print("MCP URL: %s" % args.mcp_url)

    install_package(mayapy, args.source, repo_root, args.skip_install)
    verify_import(mayapy)
    write_mcp_snippets(out_dir, args.server_name, args.mcp_url)

    print("")
    print("Next:")
    print("1. Open Maya.")
    print("2. Load dcc_mcp_maya_plugin.py in Window > Settings/Preferences > Plug-in Manager.")
    print("3. Configure the MCP host with %s." % (out_dir / "mcp-streamable-http.json"))
    print("4. Run the smoke prompt in %s." % (out_dir / "smoke-prompt.txt"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
