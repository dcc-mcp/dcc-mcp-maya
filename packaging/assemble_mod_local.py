#!/usr/bin/env python3
"""Assemble a Maya .mod module from a **local** dcc-mcp-core wheel + dcc-mcp-maya source.

Does **not** query PyPI. Use after building core, for example::

    cd ../dcc-mcp-core && vx just build
    cd ../dcc-mcp-maya && python packaging/assemble_mod_local.py --abi3-wheel ..\\\\dcc-mcp-core\\\\dist\\\\dcc_mcp_core-*-cp311-*.whl

On Windows, installs by default under ``%USERPROFILE%\\\\Documents\\\\maya\\\\``:

- ``<module-dir>/`` — ``python/``, optional ``python37/``, ``plug-ins/``, ``scripts/``
- ``modules/dcc_mcp_maya_local.mod`` — points Maya at ``<module-dir>`` (absolute path)

Maya 2022 (embedded Python 3.7) on Windows/Linux: also pass ``--cp37-wheel`` with a
``cp37-cp37m`` wheel; the script mirrors the layout used by ``assemble_mod.py``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Import sibling assemble_mod (extract_wheel, generate_mod_file, …)
_PACK = Path(__file__).resolve().parent
if str(_PACK) not in sys.path:
    sys.path.insert(0, str(_PACK))
import assemble_mod as am  # noqa: E402


def _detect_platform(wheel: Path) -> str:
    name = wheel.name.lower()
    if "win_amd64" in name or "win32" in name:
        return "win64"
    if "macosx" in name or "darwin" in name:
        return "macos"
    if "manylinux" in name or "linux" in name:
        return "linux"
    raise SystemExit(f"Cannot infer --platform from wheel name: {wheel.name}")


def _default_maya_documents() -> Path:
    return Path.home() / "Documents" / "maya"


def _generate_mod_body(mod_label: str, platform: str, mod_path: str, *, has_python37: bool) -> str:
    """Build .mod text; omit Maya 2022 when ``python37/`` is not populated (cp37 wheel missing)."""
    if platform in am.PLATFORMS_WITH_CP37_WHEELS and not has_python37:
        versions = [v for v in am.supported_maya_versions(platform) if v != "2022"]
        lines = []
        for maya_version in versions:
            lines.append(
                f"+ MAYAVERSION:{maya_version} PLATFORM:{platform} dcc_mcp_maya {mod_label} {mod_path}"
            )
            lines.append(f"PYTHONPATH+:={am.MAYA_PYTHONPATH_BY_VERSION[maya_version]}")
            lines.append("PLUG_IN_PATH+:=plug-ins")
        return "\n".join(lines) + "\n"
    return am.generate_mod_file(mod_label, platform, path=mod_path)


def assemble_local(
    project_root: Path,
    *,
    abi3_wheel: Path,
    cp37_wheel: Path | None,
    platform: str,
    maya_documents: Path,
    module_dir_name: str,
    mod_label: str,
    write_modules_mod: bool,
) -> Path:
    module_root = maya_documents / module_dir_name
    if module_root.exists():
        shutil.rmtree(module_root)

    (module_root / "plug-ins").mkdir(parents=True)
    (module_root / "scripts").mkdir(parents=True)
    python_dir = module_root / "python"
    python_dir.mkdir(parents=True)

    abi3_wheel = abi3_wheel.resolve()
    if not abi3_wheel.is_file():
        raise SystemExit(f"ABI3 wheel not found: {abi3_wheel}")

    print(f"  Extracting {abi3_wheel.name} -> {python_dir}/ ...")
    am.extract_wheel(abi3_wheel, python_dir)

    if cp37_wheel:
        cp37_wheel = cp37_wheel.resolve()
        if not cp37_wheel.is_file():
            raise SystemExit(f"cp37 wheel not found: {cp37_wheel}")
        python37_dir = module_root / "python37"
        shutil.copytree(str(python_dir), str(python37_dir))
        print(f"  Extracting {cp37_wheel.name} extensions -> {python37_dir}/ ...")
        am.extract_wheel(cp37_wheel, python37_dir, extensions_only=True, alt_dest=None)

    plugin_src = project_root / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
    shutil.copy2(plugin_src, module_root / "plug-ins" / "dcc_mcp_maya_plugin.py")
    usersetup_src = project_root / "maya" / "userSetup.py"
    shutil.copy2(usersetup_src, module_root / "scripts" / "userSetup.py")

    pkg_src = project_root / "src" / "dcc_mcp_maya"
    for package_root in (python_dir,):
        pkg_dest = package_root / "dcc_mcp_maya"
        if pkg_dest.exists():
            shutil.rmtree(pkg_dest)
        shutil.copytree(str(pkg_src), str(pkg_dest))
    if (module_root / "python37").is_dir():
        pkg_dest37 = module_root / "python37" / "dcc_mcp_maya"
        if pkg_dest37.exists():
            shutil.rmtree(pkg_dest37)
        shutil.copytree(str(pkg_src), str(pkg_dest37))

    mod_path = module_root.as_posix()
    if sys.platform == "win32" and len(mod_path) > 1 and mod_path[1] == ":":
        mod_path = mod_path[0].upper() + mod_path[1:]

    mod_body = _generate_mod_body(mod_label, platform, mod_path, has_python37=cp37_wheel is not None)
    (module_root / "dcc_mcp_maya.mod").write_text(mod_body, encoding="utf-8")

    if write_modules_mod:
        modules_dir = maya_documents / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)
        mod_link = modules_dir / "dcc_mcp_maya_local.mod"
        mod_link.write_text(mod_body, encoding="utf-8")
        print(f"  Wrote {mod_link}")

    print(f"  Module root: {module_root}")
    return module_root


def main() -> None:
    default_root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Assemble Maya module from local core wheel(s)")
    p.add_argument("--project-root", type=Path, default=default_root, help="dcc-mcp-maya repo root")
    p.add_argument(
        "--abi3-wheel",
        type=Path,
        required=True,
        help="Path to local dcc-mcp-core cp38-abi3 (or non-abi3) wheel for Maya 2023+",
    )
    p.add_argument(
        "--cp37-wheel",
        type=Path,
        default=None,
        help="Optional cp37-cp37m wheel for Maya 2022 (Windows/Linux)",
    )
    p.add_argument(
        "--platform",
        choices=("win64", "linux", "macos"),
        default=None,
        help="Override platform in .mod (default: inferred from wheel name)",
    )
    p.add_argument(
        "--maya-documents",
        type=Path,
        default=_default_maya_documents(),
        help="Maya user directory (default: ~/Documents/maya)",
    )
    p.add_argument(
        "--module-dir-name",
        default="dcc-mcp-maya-dev",
        help="Folder name under maya-documents for the module root",
    )
    p.add_argument(
        "--mod-label",
        default="0.0.0+local",
        help="Version string written into the .mod file",
    )
    p.add_argument(
        "--no-install-mod",
        action="store_true",
        help="Do not write modules/dcc_mcp_maya_local.mod (only dcc_mcp_maya.mod inside module root)",
    )
    args = p.parse_args()

    plat = args.platform or _detect_platform(args.abi3_wheel)
    assemble_local(
        args.project_root.resolve(),
        abi3_wheel=args.abi3_wheel,
        cp37_wheel=args.cp37_wheel,
        platform=plat,
        maya_documents=args.maya_documents.resolve(),
        module_dir_name=args.module_dir_name,
        mod_label=args.mod_label,
        write_modules_mod=not args.no_install_mod,
    )
    print("Done. Restart Maya or run Modules Manager → Refresh if the module does not appear.")


if __name__ == "__main__":
    main()
