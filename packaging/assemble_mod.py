#!/usr/bin/env python3
"""Assemble a Maya .mod module directory for dcc-mcp-maya.

Usage:
    python assemble_mod.py --version 0.3.0 --platform win64 --output dist/mod

This script:
1. Creates the .mod module directory structure
2. Copies the Python package and plugin files
3. Extracts dcc_mcp_core from a downloaded wheel into python/dcc_mcp_core/
4. Generates dcc_mcp_maya.mod with relative paths
5. Produces two ZIP variants:
   - Portable (with install scripts)
   - Pipeline (with module-info.json, no install scripts)
"""

from __future__ import annotations

import argparse
import json
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


def generate_mod_file(version: str, platform: str, has_cp37: bool = False, path: str = ".") -> str:
    """Generate .mod file content for given platform and Maya versions.

    Args:
        version: Package version string.
        platform: Platform string (win64, linux, macos).
        has_cp37: Whether cp37 (Maya 2022) extensions are available.
        path: Module root path. Use ``"."`` for relative paths (pipeline),
              or an absolute path for deployed installations.
    """
    lines = []
    maya_versions = []
    if has_cp37:
        maya_versions.append("2022")
    maya_versions.extend(["2023", "2024", "2025", "2026"])

    for mv in maya_versions:
        lines.append(f"+ MAYAVERSION:{mv} PLATFORM:{platform} dcc_mcp_maya {version} {path}")
        # Maya 2022 uses python37/ if cp37 extensions are available
        if mv == "2022" and has_cp37:
            lines.append("PYTHONPATH+:=python37")
        else:
            lines.append("PYTHONPATH+:=python")
        lines.append("PLUG_IN_PATH+:=plug-ins")

    return "\n".join(lines) + "\n"


def generate_module_info(version: str, has_cp37: bool = False) -> str:
    """Generate module-info.json content with build metadata.

    Included only in the pipeline ZIP for programmatic version queries.
    """
    supported = ["2023", "2024", "2025", "2026"]
    if has_cp37:
        supported.insert(0, "2022")

    info = {
        "name": "dcc_mcp_maya",
        "version": version,
        "has_cp37": has_cp37,
        "supported_maya_versions": supported,
    }
    return json.dumps(info, indent=2) + "\n"


def assemble(project_root: Path, version: str, platform: str, output: Path) -> Path:
    """Assemble the shared .mod module directory structure.

    Creates the common directory layout with python packages, plugin,
    scripts, and a pre-generated .mod file with relative paths.
    Returns the module directory path.
    """
    module_name = "dcc-mcp-maya"
    module_dir = output / module_name

    # Clean output
    if module_dir.exists():
        shutil.rmtree(module_dir)

    # Create directories
    (module_dir / "plug-ins").mkdir(parents=True)
    (module_dir / "scripts").mkdir(parents=True)
    (module_dir / "python").mkdir(parents=True)

    # 1. Download and extract dcc_mcp_core
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
            python37_dir = module_dir / "python37"
            python37_dir.mkdir(parents=True)
            python_dir = module_dir / "python"
            for item in python_dir.iterdir():
                dest_item = python37_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
            for wheel in cp37_wheels:
                print(f"  Extracting {wheel.name} (cp37 overlay to python37/)...")
                extract_wheel(wheel, python37_dir, extensions_only=True)
                has_cp37 = True
    print("  Extracted dcc_mcp_core to python/" + (" and python37/" if has_cp37 else ""))

    # 2. Copy Maya plugin
    plugin_src = project_root / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
    shutil.copy2(plugin_src, module_dir / "plug-ins" / "dcc_mcp_maya_plugin.py")
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

    # 5. Generate .mod file with relative paths
    mod_content = generate_mod_file(version, platform, has_cp37=has_cp37, path=".")
    (module_dir / "dcc_mcp_maya.mod").write_text(mod_content, encoding="utf-8")
    print(f"  Generated dcc_mcp_maya.mod (version={version}, platform={platform}, has_cp37={has_cp37})")

    return module_dir


def assemble_portable(project_root: Path, version: str, platform: str, output: Path) -> Path:
    """Assemble the portable ZIP with install scripts."""
    module_dir = assemble(project_root, version, platform, output)

    packaging_dir = project_root / "packaging"
    if platform == "win64":
        shutil.copy2(packaging_dir / "install.bat", module_dir / "install.bat")
        shutil.copy2(packaging_dir / "uninstall.bat", module_dir / "uninstall.bat")
    else:
        shutil.copy2(packaging_dir / "install.sh", module_dir / "install.sh")
        shutil.copy2(packaging_dir / "uninstall.sh", module_dir / "uninstall.sh")

    readme_src = packaging_dir / "README.txt"
    if readme_src.exists():
        shutil.copy2(readme_src, module_dir / "README.txt")

    print("  Added install scripts and README (portable)")
    return module_dir


def assemble_pipeline(project_root: Path, version: str, platform: str, output: Path) -> Path:
    """Assemble the pipeline ZIP with module-info.json, no install scripts."""
    module_dir = assemble(project_root, version, platform, output)

    # Determine has_cp37 from python37/ existence
    has_cp37 = (module_dir / "python37").is_dir()

    # Add module-info.json
    info_content = generate_module_info(version, has_cp37=has_cp37)
    (module_dir / "module-info.json").write_text(info_content, encoding="utf-8")
    print(f"  Generated module-info.json (version={version}, has_cp37={has_cp37})")

    # Add README-pipeline.txt
    readme_src = project_root / "packaging" / "README-pipeline.txt"
    if readme_src.exists():
        shutil.copy2(readme_src, module_dir / "README-pipeline.txt")

    print("  Added module-info.json and README-pipeline.txt (pipeline)")
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

    # --- Portable ZIP ---
    print(f"\nAssembling portable .mod module for platform={args.platform}, version={args.version}")
    portable_output = output_dir / "portable"
    portable_output.mkdir(parents=True, exist_ok=True)
    assemble_portable(project_root, args.version, args.platform, portable_output)
    zip_path = portable_output / f"dcc-mcp-maya-{args.version}-{args.platform}"
    shutil.make_archive(str(zip_path), "zip", root_dir=portable_output, base_dir="dcc-mcp-maya")
    print(f"Created: {zip_path}.zip")

    # --- Pipeline ZIP ---
    print(f"\nAssembling pipeline .mod module for platform={args.platform}, version={args.version}")
    pipeline_output = output_dir / "pipeline"
    pipeline_output.mkdir(parents=True, exist_ok=True)
    assemble_pipeline(project_root, args.version, args.platform, pipeline_output)
    zip_path = pipeline_output / f"dcc-mcp-maya-{args.version}-{args.platform}-pipeline"
    shutil.make_archive(str(zip_path), "zip", root_dir=pipeline_output, base_dir="dcc-mcp-maya")
    print(f"Created: {zip_path}.zip")


if __name__ == "__main__":
    main()
