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
import tempfile
from pathlib import Path


def resolve_core_version(project_root: Path) -> str:
    """Resolve the best available dcc-mcp-core version from PyPI.

    Reads the minimum version from pyproject.toml, then queries PyPI
    for the latest compatible version.  Falls back to the minimum
    version when PyPI is unreachable.
    """
    import re

    toml_path = project_root / "pyproject.toml"
    content = toml_path.read_text(encoding="utf-8")
    m = re.search(r"dcc-mcp-core>=(\d+\.\d+\.\d+)", content)
    if not m:
        m = re.search(r"dcc-mcp-core>=([\d.]+)", content)
    if not m:
        raise RuntimeError("Cannot find dcc-mcp-core version in pyproject.toml")
    min_version = m.group(1)

    # Try to get the latest version from PyPI so we download a version
    # that actually has compiled wheels for all platforms.
    try:
        import json
        import urllib.request

        url = "https://pypi.org/pypi/dcc-mcp-core/json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        latest = data.get("info", {}).get("version", "")
        if latest and _version_gte(latest, min_version):
            print(f"  PyPI latest dcc-mcp-core: {latest} (>= {min_version})")
            return latest
    except Exception as exc:
        print(f"  Warning: could not query PyPI for latest version ({exc}), using minimum {min_version}")

    return min_version


def _version_gte(ver: str, minimum: str) -> bool:
    """Return True if *ver* >= *minimum* (simple dotted comparison)."""
    v_parts = [int(x) for x in ver.split(".")]
    m_parts = [int(x) for x in minimum.split(".")]
    return v_parts >= m_parts


def download_core_wheels(version: str, platform: str, dest: Path) -> list[Path]:
    """Download dcc-mcp-core wheels for the target platform.

    Uses the PyPI JSON API to find the exact wheel URLs, then downloads
    them directly with urllib.  This avoids ``pip download`` cross-platform
    tag-filtering issues (e.g. ``--python-tag`` is not a valid pip option,
    and ``--platform`` filtering is unreliable when the runner OS differs
    from the target platform).

    Downloads both abi3 (cp38+, covers Maya 2023+) and cp37 (Maya 2022)
    wheels where available.
    """
    import json
    import urllib.request

    # Wheel filename patterns per platform.
    # Each entry: (substring that must appear in filename, description)
    wheel_patterns: list[tuple[str, str]] = []

    if platform == "win64":
        wheel_patterns = [
            ("cp38-abi3-win_amd64", "cp38-abi3, win_amd64"),
            ("cp37-cp37m-win_amd64", "cp37-cp37m, win_amd64"),
        ]
    elif platform == "linux":
        wheel_patterns = [
            ("cp38-abi3-manylinux", "cp38-abi3, manylinux x86_64"),
            ("cp37-cp37m-manylinux", "cp37-cp37m, manylinux x86_64"),
        ]
    elif platform == "macos":
        # No cp37 wheel on macOS — Maya 2022 not supported
        wheel_patterns = [
            ("cp38-abi3-macosx", "cp38-abi3, macosx universal2"),
        ]

    # Query PyPI JSON API for available wheels
    pypi_url = f"https://pypi.org/pypi/dcc-mcp-core/{version}/json"
    print(f"  Querying PyPI: {pypi_url}")
    with urllib.request.urlopen(pypi_url, timeout=30) as resp:
        pypi_data = json.loads(resp.read())

    releases = pypi_data.get("releases", {})
    version_files = releases.get(version, [])
    if not version_files:
        # Fallback: use urls from the top-level data
        version_files = pypi_data.get("urls", [])

    # Build a map from filename → download URL
    file_map: dict[str, str] = {f["filename"]: f["url"] for f in version_files if f.get("packagetype") == "bdist_wheel"}

    for pattern, desc in wheel_patterns:
        matching = [fn for fn in file_map if pattern in fn]
        if not matching:
            print(f"  Warning: no wheel matching '{pattern}' found on PyPI for v{version}")
            continue
        # Pick the first (should be exactly one)
        filename = matching[0]
        url = file_map[filename]
        dest_file = dest / filename
        if dest_file.exists():
            print(f"  Already cached: {filename}")
            continue
        print(f"  Downloading {filename} ({desc})...")
        urllib.request.urlretrieve(url, str(dest_file))

    wheels = list(dest.glob("dcc_mcp_core-*.whl"))
    if not wheels:
        raise RuntimeError(f"No dcc-mcp-core wheels could be downloaded for platform={platform}, version={version}")
    print(f"  Downloaded {len(wheels)} wheel(s)")
    return wheels


def extract_wheel(wheel_path: Path, dest: Path, *, extensions_only: bool = False, alt_dest: Path | None = None) -> None:
    """Extract a wheel into dest.

    Uses zipfile directly instead of ``pip install --target`` so that
    cross-Python-version wheels (e.g. cp37 on a py312 runner) can be
    extracted without compatibility errors.

    If extensions_only is True, only copy compiled extension files (.pyd/.so)
    to avoid overwriting Python source files from the abi3 wheel.  When
    *alt_dest* is provided and a file would overwrite an existing one in
    *dest*, the file is placed in *alt_dest* instead (used for cp37 wheels
    whose extensions share the same filename as abi3 but target Maya 2022).
    """
    import zipfile

    with zipfile.ZipFile(str(wheel_path)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            # Skip the .dist-info directory — we only need the package files
            parts = Path(info.filename).parts
            if any(p.endswith(".dist-info") for p in parts):
                continue
            dest_file = dest / info.filename
            if extensions_only:
                # Only copy compiled extensions (.pyd, .so, .dylib)
                if dest_file.suffix not in (".pyd", ".so", ".dylib"):
                    continue
                # If the file already exists (e.g. from the abi3 wheel),
                # put the cp37 extension in an alternate directory instead
                if dest_file.exists() and alt_dest is not None:
                    dest_file = alt_dest / info.filename
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest_file, "wb") as dst:
                dst.write(src.read())


def generate_mod_file(version: str, platform: str, has_cp37: bool = False) -> str:
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
        # Maya 2022 uses python37/ if cp37 extensions are available
        if mv == "2022" and has_cp37:
            lines.append("PYTHONPATH+:=python37")
        else:
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

    # 5. Download and extract dcc_mcp_core (early, so we know if cp37 is available)
    core_version = resolve_core_version(project_root)
    print(f"  Resolved dcc-mcp-core version: >={core_version}")

    has_cp37 = False
    with tempfile.TemporaryDirectory() as wheel_cache:
        wheels = download_core_wheels(core_version, platform, Path(wheel_cache))
        # Sort: abi3 first (full extract), then cp37 (extensions only)
        abi3_wheels = [w for w in wheels if "abi3" in w.name]
        cp37_wheels = [w for w in wheels if "abi3" not in w.name]
        for wheel in abi3_wheels:
            print(f"  Extracting {wheel.name} (full)...")
            extract_wheel(wheel, module_dir / "python")
        if cp37_wheels:
            # Create python37/ directory with symlinks/copies of pure Python
            # and cp37 native extensions for Maya 2022 compatibility
            python37_dir = module_dir / "python37"
            python37_dir.mkdir(parents=True)
            # Copy the entire python/ contents first, then overlay cp37 extensions
            # (This ensures python37 has all the pure-Python code too)
            python_dir = module_dir / "python"
            for item in python_dir.iterdir():
                dest_item = python37_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
            # Now overlay cp37 extensions
            for wheel in cp37_wheels:
                print(f"  Extracting {wheel.name} (cp37 overlay to python37/)...")
                extract_wheel(wheel, python37_dir, extensions_only=True)
                has_cp37 = True
    print("  Extracted dcc_mcp_core to python/" + (" and python37/" if has_cp37 else ""))

    # 1. Generate .mod file
    mod_content = generate_mod_file(version, platform, has_cp37=has_cp37)
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

    # 4. Copy dcc_mcp_maya Python package (to both python/ and python37/ if present)
    pkg_src = project_root / "src" / "dcc_mcp_maya"
    pkg_dest = module_dir / "python" / "dcc_mcp_maya"
    if pkg_dest.exists():
        shutil.rmtree(pkg_dest)
    shutil.copytree(pkg_src, pkg_dest)
    print("  Copied dcc_mcp_maya package to python/")
    if has_cp37:
        pkg_dest_37 = module_dir / "python37" / "dcc_mcp_maya"
        if pkg_dest_37.exists():
            shutil.rmtree(pkg_dest_37)
        shutil.copytree(pkg_src, pkg_dest_37)
        print("  Copied dcc_mcp_maya package to python37/")

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
