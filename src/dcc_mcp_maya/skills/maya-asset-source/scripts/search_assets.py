"""Search a directory tree for 3D asset files and return AssetDescriptor records."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import hashlib
import os
from typing import Any, Dict, List, Optional

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_EXTENSIONS = {
    ".fbx": "fbx",
    ".obj": "obj",
    ".usd": "usd",
    ".usda": "usda",
    ".usdc": "usdc",
    ".ma": "ma",
    ".mb": "mb",
}


def _normalize_path(path: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(path))
    return os.path.normpath(expanded)


def _asset_id(path: str) -> str:
    """Derive a stable short ID from an absolute path using SHA-1."""
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]


def _make_descriptor(abs_path: str) -> Dict[str, Any]:
    ext = os.path.splitext(abs_path)[1].lower()
    return {
        "id": _asset_id(abs_path),
        "name": os.path.splitext(os.path.basename(abs_path))[0],
        "path": abs_path.replace("\\", "/"),
        "format": _SUPPORTED_EXTENSIONS[ext],
        "size_bytes": os.path.getsize(abs_path),
        "metadata": {},
    }


def search_assets(
    root_dir: str,
    query: Optional[str] = None,
    formats: Optional[List[str]] = None,
    max_results: int = 100,
    recursive: bool = True,
) -> Dict[str, Any]:
    """Search *root_dir* for supported 3D asset files.

    Parameters
    ----------
    root_dir
        Root directory to search. Environment variables and ``~`` are expanded.
    query
        Case-insensitive substring to match against the file stem.  When
        ``None`` or empty, all supported files are returned.
    formats
        Restrict results to these format strings (e.g. ``["fbx", "obj"]``).
        Defaults to all supported formats when omitted.
    max_results
        Hard cap on the number of returned descriptors.
    recursive
        Search subdirectories when ``True`` (default).

    Returns
    -------
    dict
        Success envelope with ``context.assets`` list of AssetDescriptor dicts.
    """
    try:
        normalized_root = _normalize_path(root_dir)
        if not os.path.isdir(normalized_root):
            return skill_error(
                "Directory not found",
                "{} is not a directory".format(normalized_root),
                root_dir=normalized_root,
                possible_solutions=["Pass an absolute path to an existing directory"],
            )

        allowed_exts: Optional[set] = None
        if formats:
            allowed_exts = set()
            for fmt in formats:
                for ext, name in _SUPPORTED_EXTENSIONS.items():
                    if name == fmt.lower():
                        allowed_exts.add(ext)

        query_lower = query.lower().strip() if query else None

        results: List[Dict[str, Any]] = []

        def _visit(dirpath: str) -> None:
            try:
                entries = sorted(os.listdir(dirpath))
            except PermissionError:
                return
            for entry in entries:
                if len(results) >= max_results:
                    return
                full_path = os.path.join(dirpath, entry)
                if os.path.isdir(full_path):
                    if recursive:
                        _visit(full_path)
                    continue
                ext = os.path.splitext(entry)[1].lower()
                if ext not in _SUPPORTED_EXTENSIONS:
                    continue
                if allowed_exts is not None and ext not in allowed_exts:
                    continue
                stem = os.path.splitext(entry)[0].lower()
                if query_lower and query_lower not in stem:
                    continue
                results.append(_make_descriptor(full_path))

        _visit(normalized_root)

        return skill_success(
            "Found {} asset(s)".format(len(results)),
            assets=results,
            count=len(results),
            root_dir=normalized_root.replace("\\", "/"),
            query=query,
            prompt=(
                "Pass an AssetDescriptor from context.assets to "
                "maya_import_to_scene__import_to_scene to load into the scene."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to search assets in {}".format(root_dir))


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`search_assets`."""
    return search_assets(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
