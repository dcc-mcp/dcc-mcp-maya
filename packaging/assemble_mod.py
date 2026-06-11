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
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

SUPPORTED_MAYA_VERSIONS = ("2022", "2023", "2024", "2025", "2026")
MAYA_PYTHONPATH_BY_VERSION = {
    "2022": "python37",
    "2023": "python",
    "2024": "python",
    "2025": "python",
    "2026": "python",
}
PLATFORMS_WITH_CP37_WHEELS = {"win64", "linux"}


def resolve_core_version(project_root: Path) -> str:
    """Resolve the best available dcc-mcp-core version from PyPI."""
    return _resolve_dependency_version(project_root, "dcc-mcp-core")


def resolve_server_version(project_root: Path) -> str:
    """Resolve the best available dcc-mcp-server version from PyPI."""
    return _resolve_dependency_version(project_root, "dcc-mcp-server")


def _resolve_dependency_version(project_root: Path, package_name: str) -> str:
    """Resolve the best available dependency version from PyPI.

    Reads the minimum version from pyproject.toml, then queries PyPI
    for the latest compatible version.  Falls back to the minimum
    version when PyPI is unreachable.
    """
    import re

    toml_path = project_root / "pyproject.toml"
    content = toml_path.read_text(encoding="utf-8")
    escaped = re.escape(package_name)
    m = re.search(rf"{escaped}>=(\d+\.\d+\.\d+)", content)
    if not m:
        m = re.search(rf"{escaped}>=([\d.]+)", content)
    if not m:
        raise RuntimeError(f"Cannot find {package_name} version in pyproject.toml")
    min_version = m.group(1)

    # Try to get the latest version from PyPI so we download a version
    # that actually has compiled wheels for all platforms.
    try:
        import urllib.request

        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        latest = data.get("info", {}).get("version", "")
        if latest and _version_gte(latest, min_version):
            print(f"  PyPI latest {package_name}: {latest} (>= {min_version})")
            return latest
    except Exception as exc:
        print(f"  Warning: could not query PyPI for latest {package_name} ({exc}), using minimum {min_version}")

    return min_version


def _version_gte(ver: str, minimum: str) -> bool:
    """Return True if *ver* >= *minimum* (simple dotted comparison)."""
    v_parts = [int(x) for x in ver.split(".")]
    m_parts = [int(x) for x in minimum.split(".")]
    return v_parts >= m_parts


def download_core_wheels(version: str, platform: str, dest: Path) -> List[Path]:
    """Download dcc-mcp-core wheels for the target platform.

    Maya 2022 embeds Python 3.7, which cannot import ``cp38-abi3``
    extension wheels.  For platforms where core publishes cp37 wheels,
    download both the cp37 wheel and the cp38-abi3 wheel so the module
    package can route Maya 2022 to ``python37/`` and newer Maya versions
    to ``python/``.
    """
    import urllib.request

    wheel_patterns = _core_wheel_patterns(platform)

    pypi_url = f"https://pypi.org/pypi/dcc-mcp-core/{version}/json"
    print(f"  Querying PyPI: {pypi_url}")
    with urllib.request.urlopen(pypi_url, timeout=30) as resp:
        pypi_data = json.loads(resp.read())

    releases = pypi_data.get("releases", {})
    version_files = releases.get(version, [])
    if not version_files:
        version_files = pypi_data.get("urls", [])

    file_map = {f["filename"]: f["url"] for f in version_files if f.get("packagetype") == "bdist_wheel"}

    for pattern, desc in wheel_patterns:
        matching = [fn for fn in file_map if pattern in fn]
        if not matching:
            print(f"  Warning: no wheel matching '{pattern}' found on PyPI for v{version}")
            continue
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


def download_server_wheel(version: str, platform: str, dest: Path) -> Path:
    """Download the dcc-mcp-server sidecar wheel for the target platform."""
    import urllib.request

    pypi_url = f"https://pypi.org/pypi/dcc-mcp-server/{version}/json"
    print(f"  Querying PyPI: {pypi_url}")
    with urllib.request.urlopen(pypi_url, timeout=30) as resp:
        pypi_data = json.loads(resp.read())

    releases = pypi_data.get("releases", {})
    version_files = releases.get(version, [])
    if not version_files:
        version_files = pypi_data.get("urls", [])

    file_map = {f["filename"]: f["url"] for f in version_files if f.get("packagetype") == "bdist_wheel"}
    patterns = _server_wheel_patterns(platform)
    for pattern in patterns:
        matching = [fn for fn in file_map if pattern in fn]
        if not matching:
            continue
        filename = matching[0]
        dest_file = dest / filename
        if dest_file.exists():
            print(f"  Already cached: {filename}")
            return dest_file
        print(f"  Downloading {filename} (sidecar server)...")
        urllib.request.urlretrieve(file_map[filename], str(dest_file))
        return dest_file
    raise RuntimeError(
        f"No dcc-mcp-server wheel matching {patterns!r} found on PyPI for platform={platform}, version={version}"
    )


def _core_wheel_patterns(platform: str) -> List[Tuple[str, str]]:
    if platform == "win64":
        return [("cp37-cp37m-win_amd64", "cp37, win_amd64"), ("cp38-abi3-win_amd64", "cp38-abi3, win_amd64")]
    if platform == "linux":
        return [
            ("cp37-cp37m-manylinux", "cp37, manylinux x86_64"),
            ("cp38-abi3-manylinux", "cp38-abi3, manylinux x86_64"),
        ]
    if platform == "macos":
        return [("cp38-abi3-macosx", "cp38-abi3, macosx universal2")]
    return []


def _server_wheel_patterns(platform: str) -> List[str]:
    if platform == "win64":
        return ["win_amd64"]
    if platform == "linux":
        return ["manylinux", "linux_x86_64"]
    if platform == "macos":
        return ["macosx"]
    return []


def extract_wheel(
    wheel_path: Path, dest: Path, *, extensions_only: bool = False, alt_dest: Optional[Path] = None
) -> None:
    """Extract a wheel into dest.

    Uses zipfile directly instead of ``pip install --target`` so target
    platform wheels can be extracted on any build runner.

    If extensions_only is True, only copy compiled extension files (.pyd/.so)
    to avoid overwriting Python source files from the abi3 wheel.  When
    *alt_dest* is provided and a file would overwrite an existing one in
    *dest*, the file is placed in *alt_dest* instead.
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
                # put the extension in an alternate directory instead
                if dest_file.exists() and alt_dest is not None:
                    dest_file = alt_dest / info.filename
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest_file, "wb") as dst:
                dst.write(src.read())
            mode = info.external_attr >> 16
            if mode:
                os.chmod(dest_file, mode)


def extract_server_wheel(wheel_path: Path, dest: Path) -> None:
    """Extract dcc-mcp-server package files and its binary into *dest*.

    ``pip install`` maps ``*.data/scripts/dcc-mcp-server`` into the target
    environment's scripts directory.  Module ZIP assembly extracts wheels
    directly, so we perform that mapping explicitly.
    """
    import zipfile

    with zipfile.ZipFile(str(wheel_path)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            if any(p.endswith(".dist-info") for p in parts):
                continue
            if len(parts) >= 3 and parts[0].endswith(".data") and parts[1] == "scripts":
                dest_file = dest / "scripts" / Path(*parts[2:])
            elif parts[0] == "dcc_mcp_server":
                dest_file = dest / info.filename
            else:
                continue
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest_file, "wb") as dst:
                dst.write(src.read())
            mode = info.external_attr >> 16
            if mode:
                os.chmod(dest_file, mode)


def generate_mod_file(version: str, platform: str, path: str = ".") -> str:
    """Generate .mod file content for the supported Maya versions."""
    lines = []
    for maya_version in supported_maya_versions(platform):
        lines.append(f"+ MAYAVERSION:{maya_version} PLATFORM:{platform} dcc_mcp_maya {version} {path}")
        lines.append(f"PYTHONPATH+:={MAYA_PYTHONPATH_BY_VERSION[maya_version]}")
        lines.append("PLUG_IN_PATH+:=plug-ins")

    return "\n".join(lines) + "\n"


def supported_maya_versions(platform: str) -> List[str]:
    """Return Maya versions supported by the offline module for *platform*."""
    if platform in PLATFORMS_WITH_CP37_WHEELS:
        return list(SUPPORTED_MAYA_VERSIONS)
    return [version for version in SUPPORTED_MAYA_VERSIONS if version != "2022"]


def generate_module_info(version: str, platform: str = "win64") -> str:
    """Generate module-info.json content with build metadata."""
    info = {
        "name": "dcc_mcp_maya",
        "version": version,
        "supported_maya_versions": supported_maya_versions(platform),
        "has_python37": platform in PLATFORMS_WITH_CP37_WHEELS,
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
    python_dir = module_dir / "python"
    python_dir.mkdir(parents=True)
    python37_dir = module_dir / "python37"

    # 1. Download and extract dcc_mcp_core
    core_version = resolve_core_version(project_root)
    print(f"  Resolved dcc-mcp-core version: >={core_version}")
    server_version = resolve_server_version(project_root)
    print(f"  Resolved dcc-mcp-server version: >={server_version}")

    with tempfile.TemporaryDirectory() as wheel_cache:
        cache_dir = Path(wheel_cache)
        wheels = download_core_wheels(core_version, platform, cache_dir)
        server_wheel = download_server_wheel(server_version, platform, cache_dir)
        abi3_wheels = [wheel for wheel in wheels if "abi3" in wheel.name]
        cp37_wheels = [wheel for wheel in wheels if "cp37-cp37m" in wheel.name]

        for wheel in abi3_wheels or wheels:
            print(f"  Extracting {wheel.name} to python/...")
            extract_wheel(wheel, python_dir)

        if cp37_wheels:
            shutil.copytree(str(python_dir), str(python37_dir))
            for wheel in cp37_wheels:
                print(f"  Extracting {wheel.name} extensions to python37/...")
                extract_wheel(wheel, python37_dir, extensions_only=True)

        for package_root in (python_dir, python37_dir):
            if not package_root.is_dir():
                continue
            print(f"  Extracting {server_wheel.name} to {package_root.name}/...")
            extract_server_wheel(server_wheel, package_root)
    print("  Extracted dcc_mcp_core")
    print("  Extracted dcc_mcp_server")

    # 2. Copy Maya plugin
    plugin_src = project_root / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
    shutil.copy2(plugin_src, module_dir / "plug-ins" / "dcc_mcp_maya_plugin.py")
    print("  Copied plugin to plug-ins/")

    # 3. Copy userSetup.py
    usersetup_src = project_root / "maya" / "userSetup.py"
    shutil.copy2(usersetup_src, module_dir / "scripts" / "userSetup.py")
    print("  Copied userSetup.py to scripts/")

    # 4. Copy dcc_mcp_maya Python package
    pkg_src = project_root / "src" / "dcc_mcp_maya"
    for package_root in (python_dir, python37_dir):
        if not package_root.is_dir():
            continue
        pkg_dest = package_root / "dcc_mcp_maya"
        if pkg_dest.exists():
            shutil.rmtree(pkg_dest)
        shutil.copytree(str(pkg_src), str(pkg_dest))
    print("  Copied dcc_mcp_maya package")

    # 5. Generate .mod file with relative paths
    mod_content = generate_mod_file(version, platform, path=".")
    (module_dir / "dcc_mcp_maya.mod").write_text(mod_content, encoding="utf-8")
    print(f"  Generated dcc_mcp_maya.mod (version={version}, platform={platform})")

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

    # Add module-info.json
    info_content = generate_module_info(version, platform)
    (module_dir / "module-info.json").write_text(info_content, encoding="utf-8")
    print(f"  Generated module-info.json (version={version})")

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
