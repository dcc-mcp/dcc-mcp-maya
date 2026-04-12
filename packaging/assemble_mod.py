#!/usr/bin/env python3
"""Assemble a Maya .mod module directory for dcc-mcp-maya.

Usage:
    python assemble_mod.py --version 0.3.0 --platform win64 --output dist/mod

This script:
1. Creates the .mod module directory structure
2. Copies the Python package and plugin files
3. Extracts dcc_mcp_core from a downloaded wheel into python/dcc_mcp_core/
4. Generates the .mod file with correct platform/version
5. Copies install/uninstall scripts and README
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], **kwargs) -> str:
    """Run a subprocess and return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)
    return result.stdout.strip()


def resolve_core_version(project_root: Path) -> str:
    """Read the dcc-mcp-core minimum version from pyproject.toml."""
    import re

    toml_path = project_root / "pyproject.toml"
    content = toml_path.read_text(encoding="utf-8")
    m = re.search(r"dcc-mcp-core>=(\d+\.\d+\.\d+)", content)
    if m:
        return m.group(1)
    m = re.search(r"dcc-mcp-core>=([\d.]+)", content)
    if m:
        return m.group(1)
    raise RuntimeError("Cannot find dcc-mcp-core version in pyproject.toml")


def download_core_wheels(version: str, platform: str, dest: Path) -> list[Path]:
    """Download dcc-mcp-core wheels for the target platform.

    Downloads both abi3 (cp38+, covers Maya 2023+) and cp37 (Maya 2022)
    wheels where available.
    """
    # Wheel specs: (python_tag, abi_tag, pip_platform_tag)
    wheel_specs: list[tuple[str, str, str]] = []

    if platform == "win64":
        wheel_specs = [
            ("cp38", "abi3", "win_amd64"),
            ("cp37", "cp37m", "win_amd64"),
        ]
    elif platform == "linux":
        wheel_specs = [
            ("cp38", "abi3", "manylinux_2_17_x86_64.manylinux2014_x86_64"),
            ("cp37", "cp37m", "manylinux_2_17_x86_64.manylinux2014_x86_64"),
        ]
    elif platform == "macos":
        # No cp37 wheel on macOS — Maya 2022 not supported
        wheel_specs = [
            ("cp38", "abi3", "macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2"),
        ]

    for py_tag, abi_tag, plat_tag in wheel_specs:
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "download",
            f"dcc-mcp-core=={version}",
            "--no-deps",
            "--only-binary=:all:",
            f"--platform={plat_tag}",
            f"--python-tag={py_tag}",
            f"--abi={abi_tag}",
            "-d",
            str(dest),
        ]
        print(f"  Downloading core wheel ({py_tag}-{abi_tag}, {plat_tag})...")
        run(cmd)

    wheels = list(dest.glob("dcc_mcp_core-*.whl"))
    print(f"  Downloaded {len(wheels)} wheel(s)")
    return wheels


def extract_wheel(wheel_path: Path, dest: Path, *, extensions_only: bool = False) -> None:
    """Extract a wheel into dest.

    If extensions_only is True, only copy compiled extension files (.pyd/.so)
    to avoid overwriting Python source files from the abi3 wheel.
    """
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--target", tmp, str(wheel_path)],
            check=True,
            capture_output=True,
        )
        tmp_path = Path(tmp)
        for item in tmp_path.rglob("*"):
            if not item.is_file():
                continue
            rel = item.relative_to(tmp_path)
            dest_file = dest / rel
            if extensions_only:
                # Only copy compiled extensions (.pyd, .so, .dylib)
                if item.suffix not in (".pyd", ".so", ".dylib"):
                    continue
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_file)


def generate_mod_file(version: str, platform: str) -> str:
    """Generate the .mod file content."""
    platform_str = {
        "win64": "win64",
        "linux": "linux",
        "macos": "macos",
    }[platform]

    maya_versions = ["2022", "2023", "2024", "2025"]
    # macOS has no cp37 wheel, skip Maya 2022
    if platform == "macos":
        maya_versions = ["2023", "2024", "2025"]

    lines = []
    for mv in maya_versions:
        lines.append(f"+ MAYAVERSION:{mv} PLATFORM:{platform_str} dcc_mcp_maya {version} .")
        lines.append("PYTHONPATH+:=python")

    return "\n".join(lines) + "\n"


def assemble(project_root: Path, version: str, platform: str, output: Path) -> Path:
    """Assemble the .mod module directory."""
    module_name = "dcc-mcp-maya"
    module_dir = output / module_name

    # Clean output
    if module_dir.exists():
        shutil.rmtree(module_dir)

    # Create directories
    (module_dir / "plug-ins").mkdir(parents=True)
    (module_dir / "scripts").mkdir(parents=True)
    (module_dir / "python").mkdir(parents=True)

    # 1. Generate .mod file
    mod_content = generate_mod_file(version, platform)
    (module_dir / "dcc_mcp_maya.mod").write_text(mod_content, encoding="utf-8")
    print(f"  Generated dcc_mcp_maya.mod (platform={platform}, version={version})")

    # 2. Copy Maya plugin
    plugin_src = project_root / "maya" / "plugin" / "dcc_mcp_maya.py"
    shutil.copy2(plugin_src, module_dir / "plug-ins" / "dcc_mcp_maya.py")
    print("  Copied plugin to plug-ins/")

    # 3. Copy userSetup.py
    usersetup_src = project_root / "maya" / "userSetup.py"
    shutil.copy2(usersetup_src, module_dir / "scripts" / "userSetup.py")
    print("  Copied userSetup.py to scripts/")

    # 4. Copy dcc_mcp_maya Python package
    pkg_src = project_root / "src" / "dcc_mcp_maya"
    pkg_dest = module_dir / "python" / "dcc_mcp_maya"
    if pkg_dest.exists():
        shutil.rmtree(pkg_dest)
    shutil.copytree(pkg_src, pkg_dest)
    print("  Copied dcc_mcp_maya package to python/")

    # 5. Download and extract dcc_mcp_core
    core_version = resolve_core_version(project_root)
    print(f"  Resolved dcc-mcp-core version: >={core_version}")

    with tempfile.TemporaryDirectory() as wheel_cache:
        wheels = download_core_wheels(core_version, platform, Path(wheel_cache))
        # Sort: abi3 first (full extract), then cp37 (extensions only)
        abi3_wheels = [w for w in wheels if "abi3" in w.name]
        cp37_wheels = [w for w in wheels if "abi3" not in w.name]
        for wheel in abi3_wheels:
            print(f"  Extracting {wheel.name} (full)...")
            extract_wheel(wheel, module_dir / "python")
        for wheel in cp37_wheels:
            print(f"  Extracting {wheel.name} (extensions only)...")
            extract_wheel(wheel, module_dir / "python", extensions_only=True)
    print("  Extracted dcc_mcp_core to python/")

    # 6. Copy install/uninstall scripts and README
    packaging_dir = project_root / "packaging"
    if platform == "win64":
        shutil.copy2(packaging_dir / "install.bat", module_dir / "install.bat")
        shutil.copy2(packaging_dir / "uninstall.bat", module_dir / "uninstall.bat")
    else:
        shutil.copy2(packaging_dir / "install.sh", module_dir / "install.sh")
        shutil.copy2(packaging_dir / "uninstall.sh", module_dir / "uninstall.sh")
    shutil.copy2(packaging_dir / "README.txt", module_dir / "README.txt")
    print("  Copied install/uninstall scripts and README")

    return module_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble Maya .mod module for dcc-mcp-maya")
    parser.add_argument("--version", required=True, help="Package version (e.g. 0.3.0)")
    parser.add_argument("--platform", required=True, choices=["win64", "linux", "macos"], help="Target platform")
    parser.add_argument("--output", default="dist/mod", help="Output directory")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Assembling .mod module for platform={args.platform}, version={args.version}")
    assemble(project_root, args.version, args.platform, output_dir)

    # Create ZIP
    zip_path = output_dir / f"dcc-mcp-maya-{args.version}-{args.platform}"
    shutil.make_archive(str(zip_path), "zip", root_dir=output_dir, base_dir="dcc-mcp-maya")
    print(f"\nCreated: {zip_path}.zip")


if __name__ == "__main__":
    main()
