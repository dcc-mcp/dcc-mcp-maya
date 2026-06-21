"""Resolve a file path to a structured AssetDescriptor."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import hashlib
import os
from typing import Any, Dict

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
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]


def resolve_asset(path: str) -> Dict[str, Any]:
    """Resolve *path* to a single AssetDescriptor.

    Parameters
    ----------
    path
        Absolute path to an asset file.  Must exist on disk and have a
        supported extension.

    Returns
    -------
    dict
        Success envelope with ``context.asset`` AssetDescriptor dict.
    """
    try:
        if not path:
            return skill_error(
                "Missing path",
                "path is required",
                possible_solutions=["Pass an absolute path to an existing asset file"],
            )

        normalized = _normalize_path(path)
        if not os.path.isfile(normalized):
            return skill_error(
                "Asset file not found",
                "{} does not exist on disk".format(normalized),
                path=normalized,
                possible_solutions=["Verify the path", "Use search_assets to discover available assets"],
            )

        ext = os.path.splitext(normalized)[1].lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            return skill_error(
                "Unsupported format",
                "Extension '{}' is not supported. Supported: {}".format(ext, ", ".join(sorted(_SUPPORTED_EXTENSIONS))),
                path=normalized,
                extension=ext,
            )

        descriptor: Dict[str, Any] = {
            "id": _asset_id(normalized),
            "name": os.path.splitext(os.path.basename(normalized))[0],
            "path": normalized.replace("\\", "/"),
            "format": _SUPPORTED_EXTENSIONS[ext],
            "size_bytes": os.path.getsize(normalized),
            "metadata": {},
        }

        return skill_success(
            "Resolved asset: {}".format(descriptor["name"]),
            asset=descriptor,
            prompt=("Pass context.asset to maya_import_to_scene__import_to_scene to load into the current Maya scene."),
        )
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to resolve asset: {}".format(path))


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`resolve_asset`."""
    return resolve_asset(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
