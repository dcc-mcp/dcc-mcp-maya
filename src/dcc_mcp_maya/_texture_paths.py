"""Bounded local texture-path validation shared by Maya texture tools."""

from __future__ import annotations

import glob
import itertools
import re
from pathlib import Path
from typing import Dict, List, Tuple

MAX_TEXTURE_PATH_LENGTH = 4096
MAX_UDIM_TILES = 256


def _resolve_texture_files(texture_path: str, udim_mode: str) -> Tuple[Path, List[Path]]:
    if not isinstance(texture_path, str) or not texture_path.strip():
        raise ValueError("texture path must be a non-empty string")
    if len(texture_path) > MAX_TEXTURE_PATH_LENGTH:
        raise ValueError("texture path exceeds {} characters".format(MAX_TEXTURE_PATH_LENGTH))
    if udim_mode not in {"off", "udim"}:
        raise ValueError("udim mode must be off or udim")

    unresolved_path = Path(texture_path).expanduser()
    if udim_mode == "off":
        path = unresolved_path.resolve()
        if "<UDIM>" in path.name:
            raise ValueError("udim_mode='off' cannot use a <UDIM> token")
        if not path.is_file():
            raise ValueError("texture file was not found")
        return path, [path]

    if unresolved_path.name.count("<UDIM>") != 1:
        raise ValueError("udim_mode='udim' requires exactly one <UDIM> token in the filename")
    path = unresolved_path.parent.resolve() / unresolved_path.name
    if not path.parent.is_dir():
        raise ValueError("UDIM texture directory was not found")
    pattern = glob.escape(path.name).replace("<UDIM>", "[0-9][0-9][0-9][0-9]")
    candidates = list(itertools.islice(path.parent.glob(pattern), MAX_UDIM_TILES + 1))
    if len(candidates) > MAX_UDIM_TILES:
        raise ValueError("UDIM pattern matched more than {} tiles".format(MAX_UDIM_TILES))
    matcher = re.compile("^{}$".format(re.escape(path.name).replace(re.escape("<UDIM>"), r"([0-9]{4})")))
    tiles = []
    for candidate in candidates:
        match = matcher.fullmatch(candidate.name)
        if candidate.is_file() and match and int(match.group(1)) >= 1001:
            tiles.append(candidate)
    if not tiles:
        raise ValueError("UDIM pattern did not match any tile numbered 1001 or higher")
    return path, tiles


def resolve_texture_path(texture_path: str, udim_mode: str) -> Tuple[Path, int]:
    """Resolve one concrete file or bounded ``<UDIM>`` pattern."""

    path, files = _resolve_texture_files(texture_path, udim_mode)
    return path, len(files)


def texture_disk_evidence(texture_path: str, udim_mode: str) -> Tuple[Path, Dict[str, int]]:
    """Return aggregate bounded disk evidence for a texture or UDIM set."""

    path, files = _resolve_texture_files(texture_path, udim_mode)
    stats = [file_path.stat() for file_path in files]
    return path, {
        "tile_count": len(files),
        "bytes": sum(item.st_size for item in stats),
        "mtime_ns": max(item.st_mtime_ns for item in stats),
    }
