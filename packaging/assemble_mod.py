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
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import List, Optional, Tuple

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

SUPPORTED_MAYA_VERSIONS = ("2022", "2023", "2024", "2025", "2026")
MAYA_PYTHONPATH_BY_VERSION = {
    "2022": "python37",
    "2023": "python",
    "2024": "python",
    "2025": "python",
    "2026": "python",
}
PLATFORMS_WITH_CP37_WHEELS = {"win64", "linux"}
CORE_PROVENANCE_PATH = "core-provenance.json"

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("creation_time", wintypes.FILETIME),
            ("last_access_time", wintypes.FILETIME),
            ("last_write_time", wintypes.FILETIME),
            ("volume_serial_number", wintypes.DWORD),
            ("file_size_high", wintypes.DWORD),
            ("file_size_low", wintypes.DWORD),
            ("number_of_links", wintypes.DWORD),
            ("file_index_high", wintypes.DWORD),
            ("file_index_low", wintypes.DWORD),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _create_file = _kernel32.CreateFileW
    _create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _create_file.restype = wintypes.HANDLE
    _get_file_information = _kernel32.GetFileInformationByHandle
    _get_file_information.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation)]
    _get_file_information.restype = wintypes.BOOL
    _close_handle = _kernel32.CloseHandle
    _close_handle.argtypes = [wintypes.HANDLE]
    _close_handle.restype = wintypes.BOOL

    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    _FILE_ATTRIBUTE_DIRECTORY = 0x10
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004
    _OPEN_EXISTING = 3


def resolve_core_version(project_root: Path) -> str:
    """Resolve the best available dcc-mcp-core version from PyPI."""
    return _resolve_dependency_version(project_root, "dcc-mcp-core")


def resolve_server_version(project_root: Path) -> str:
    """Resolve the best available dcc-mcp-server version from PyPI."""
    return _resolve_dependency_version(project_root, "dcc-mcp-server")


def _resolve_dependency_version(project_root: Path, package_name: str) -> str:
    """Resolve the best available dependency version from PyPI.

    Reads the version bounds from pyproject.toml, then queries PyPI for
    the latest compatible version. Falls back to the minimum version when
    PyPI is unreachable.
    """
    min_version, max_version = dependency_bounds(project_root, package_name)

    # Try to get the latest compatible version from PyPI so we download
    # a version that actually has compiled wheels for all platforms.
    try:
        import urllib.request

        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        releases = sorted(data.get("releases", {}).keys(), key=_version_key)
        compatible = [
            version
            for version in releases
            if _version_gte(version, min_version) and (max_version is None or _version_lt(version, max_version))
        ]
        if compatible:
            selected = compatible[-1]
            if max_version:
                print(f"  PyPI selected {package_name}: {selected} (>= {min_version}, < {max_version})")
            else:
                print(f"  PyPI latest {package_name}: {selected} (>= {min_version})")
            return selected
    except Exception as exc:
        print(f"  Warning: could not query PyPI for latest {package_name} ({exc}), using minimum {min_version}")

    return min_version


def dependency_bounds(project_root: Path, package_name: str) -> Tuple[str, str]:
    """Read the canonical inclusive-minimum/exclusive-maximum package range."""
    import re

    content = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    escaped = re.escape(package_name)
    match = re.search(rf'"{escaped}(?P<spec>[^"]+)"', content)
    if not match:
        raise RuntimeError(f"Cannot find {package_name} version in pyproject.toml")
    bounds = re.fullmatch(r"\s*>=\s*(\d+(?:\.\d+)*)\s*,\s*<\s*(\d+(?:\.\d+)*)\s*", match.group("spec"))
    if not bounds:
        raise RuntimeError(f"{package_name} must have exactly one >= minimum and < maximum in pyproject.toml")
    return bounds.group(1), bounds.group(2)


def _version_key(ver: str) -> Tuple[int, ...]:
    """Return a sortable key for dotted numeric versions."""
    return tuple(int(x) for x in ver.split("."))


def _version_gte(ver: str, minimum: str) -> bool:
    """Return True if *ver* >= *minimum* (simple dotted comparison)."""
    return _version_key(ver) >= _version_key(minimum)


def _version_lt(ver: str, maximum: str) -> bool:
    """Return True if *ver* < *maximum* (simple dotted comparison)."""
    return _version_key(ver) < _version_key(maximum)


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_digest(content: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")


def _assembled_file_fingerprint(stat_result) -> tuple:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        getattr(stat_result, "st_mtime_ns", int(stat_result.st_mtime * 1_000_000_000)),
        stat_result.st_nlink,
    )


def _windows_handle_snapshot(handle) -> dict:
    information = _ByHandleFileInformation()
    if not _get_file_information(handle, ctypes.byref(information)):
        raise OSError(ctypes.get_last_error(), "GetFileInformationByHandle failed")
    return {
        "attributes": information.file_attributes,
        "identity": (
            information.volume_serial_number,
            (information.file_index_high << 32) | information.file_index_low,
        ),
        "last_write": (information.last_write_time.dwHighDateTime << 32) | information.last_write_time.dwLowDateTime,
        "links": information.number_of_links,
        "size": (information.file_size_high << 32) | information.file_size_low,
    }


def _windows_path_snapshot(path: Path) -> dict:
    raw_path = os.path.abspath(str(path))
    extended_path = "\\\\?\\UNC\\" + raw_path[2:] if raw_path.startswith("\\\\") else "\\\\?\\" + raw_path
    handle = _create_file(
        extended_path,
        0,
        _FILE_SHARE_ALL,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        raise OSError(ctypes.get_last_error(), "CreateFileW failed", raw_path)
    try:
        return _windows_handle_snapshot(handle)
    finally:
        _close_handle(handle)


def _assert_safe_windows_file(snapshot: dict, path: Path) -> None:
    if (
        snapshot["attributes"] & (_FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT)
        or snapshot["links"] != 1
        or not snapshot["identity"][1]
    ):
        raise RuntimeError(f"Core assembly requires a non-reparse single-link regular file: {path}")


def _capture_windows_assembled_file(path: Path) -> dict:
    path_before = _windows_path_snapshot(path)
    _assert_safe_windows_file(path_before, path)
    with path.open("rb") as stream:
        before = _windows_handle_snapshot(msvcrt.get_osfhandle(stream.fileno()))
        _assert_safe_windows_file(before, path)
        content = stream.read()
        after = _windows_handle_snapshot(msvcrt.get_osfhandle(stream.fileno()))
        _assert_safe_windows_file(after, path)
    current = _windows_path_snapshot(path)
    _assert_safe_windows_file(current, path)
    fingerprint = (before["identity"], before["size"], before["last_write"], before["links"])
    if any(
        (item["identity"], item["size"], item["last_write"], item["links"]) != fingerprint
        for item in (path_before, after, current)
    ):
        raise RuntimeError(f"Assembled file object changed during capture: {path}")
    return {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content), "identity": before["identity"]}


def _capture_posix_assembled_file(path: Path) -> dict:
    try:
        path_before = path.lstat()
        if not stat.S_ISREG(path_before.st_mode) or path_before.st_nlink != 1:
            raise RuntimeError(f"Core assembly requires a non-reparse single-link regular file: {path}")
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise RuntimeError(f"Core assembly requires a non-reparse single-link regular file: {path}")
            content = stream.read()
            after = os.fstat(stream.fileno())
            if not stat.S_ISREG(after.st_mode) or after.st_nlink != 1:
                raise RuntimeError(f"Core assembly requires a non-reparse single-link regular file: {path}")
        current = path.lstat()
        if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1:
            raise RuntimeError(f"Core assembly requires a non-reparse single-link regular file: {path}")
    except OSError as exc:
        raise RuntimeError(f"Unable to capture assembled file object: {path}") from exc
    fingerprint = _assembled_file_fingerprint(before)
    if any(_assembled_file_fingerprint(item) != fingerprint for item in (path_before, after, current)):
        raise RuntimeError(f"Assembled file object changed during capture: {path}")
    identity = (before.st_dev, before.st_ino)
    if not before.st_ino:
        raise RuntimeError(f"Assembled file object identity is unavailable: {path}")
    return {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content), "identity": identity}


def _capture_assembled_file(path: Path) -> dict:
    if os.name == "nt":
        return _capture_windows_assembled_file(path)
    return _capture_posix_assembled_file(path)


def _assert_safe_assembled_directory(path: Path) -> None:
    if os.name == "nt":
        snapshot = _windows_path_snapshot(path)
        if (
            not snapshot["attributes"] & _FILE_ATTRIBUTE_DIRECTORY
            or snapshot["attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise RuntimeError(f"Core assembly directory must not be a link or reparse point: {path}")
        return
    path_stat = path.lstat()
    if not stat.S_ISDIR(path_stat.st_mode):
        raise RuntimeError(f"Core assembly directory must not be a link or reparse point: {path}")


def _capture_assembled_directory(path: Path) -> tuple:
    """Capture one real directory object without following links or reparse points."""
    try:
        if os.name == "nt":
            before = _windows_path_snapshot(path)
            if (
                not before["attributes"] & _FILE_ATTRIBUTE_DIRECTORY
                or before["attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT
                or not before["identity"][1]
            ):
                raise RuntimeError(f"Core assembly directory must not be a link or reparse point: {path}")
            current = _windows_path_snapshot(path)
            if (
                not current["attributes"] & _FILE_ATTRIBUTE_DIRECTORY
                or current["attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT
                or current["identity"] != before["identity"]
            ):
                raise RuntimeError(f"Core assembly directory object changed during capture: {path}")
            return before["identity"]

        before = path.lstat()
        if not stat.S_ISDIR(before.st_mode) or not before.st_ino:
            raise RuntimeError(f"Core assembly directory must not be a link or reparse point: {path}")
        current = path.lstat()
        identity = (before.st_dev, before.st_ino)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != identity:
            raise RuntimeError(f"Core assembly directory object changed during capture: {path}")
        return identity
    except OSError as exc:
        raise RuntimeError(f"Unable to capture Core assembly directory: {path}") from exc


def _classify_assembled_path(path: Path) -> str:
    """Classify a direct child without following a link-like object."""
    try:
        if os.name == "nt":
            snapshot = _windows_path_snapshot(path)
            if snapshot["attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT:
                raise RuntimeError(f"Core assembly directory must not be a link or reparse point: {path}")
            return "directory" if snapshot["attributes"] & _FILE_ATTRIBUTE_DIRECTORY else "file"

        path_stat = path.lstat()
        if stat.S_ISLNK(path_stat.st_mode):
            raise RuntimeError(f"Core assembly directory must not be a link or reparse point: {path}")
        if stat.S_ISDIR(path_stat.st_mode):
            return "directory"
        if stat.S_ISREG(path_stat.st_mode):
            return "file"
        raise RuntimeError(f"Core assembly path must be a regular file or directory: {path}")
    except OSError as exc:
        raise RuntimeError(f"Unable to classify Core assembly path: {path}") from exc


def _safe_regular_file_paths(root: Path, runtime_root: Path) -> set:
    """Enumerate regular files while rejecting every link/reparse directory component."""
    paths = set()
    pending = [root]
    while pending:
        directory = pending.pop()
        identity = _capture_assembled_directory(directory)
        try:
            entries = list(os.scandir(str(directory)))
        except OSError as exc:
            raise RuntimeError(f"Unable to enumerate Core assembly directory: {directory}") from exc
        if _capture_assembled_directory(directory) != identity:
            raise RuntimeError(f"Core assembly directory object changed during enumeration: {directory}")
        for entry in entries:
            path = Path(entry.path)
            kind = _classify_assembled_path(path)
            if kind == "directory":
                pending.append(path)
            else:
                paths.add(path.relative_to(runtime_root).as_posix())
    return paths


def _capture_ancestor_chain(runtime_root: Path, file_path: Path, expected: Optional[dict] = None) -> dict:
    """Capture every lexical parent before a file is opened."""
    relative = file_path.relative_to(runtime_root)
    directories = [runtime_root]
    current = runtime_root
    for part in relative.parts[:-1]:
        current = current / part
        directories.append(current)
    captured = {}
    for directory in directories:
        key = "." if directory == runtime_root else directory.relative_to(runtime_root).as_posix()
        identity = _capture_assembled_directory(directory)
        if expected is not None and expected.get(key) != identity:
            raise RuntimeError(f"Core assembly directory object changed after provenance binding: {directory}")
        captured[key] = identity
    return captured


def _capture_bound_assembled_file(
    runtime_root: Path, file_path: Path, expected_directories: Optional[dict] = None
) -> tuple:
    """Capture a file between two stable, non-link ancestor-chain snapshots."""
    before = _capture_ancestor_chain(runtime_root, file_path, expected_directories)
    captured = _capture_assembled_file(file_path)
    after = _capture_ancestor_chain(runtime_root, file_path, expected_directories)
    if before != after:
        raise RuntimeError(f"Core assembly directory object changed while reading: {file_path}")
    return captured, before


def _parse_core_metadata(metadata_content: bytes, wheel_name: str) -> Tuple[str, Version]:
    try:
        package_metadata = Parser().parsestr(metadata_content.decode("utf-8"))
        names = package_metadata.get_all("Name", [])
        versions = package_metadata.get_all("Version", [])
        if len(names) != 1 or len(versions) != 1:
            raise ValueError("ambiguous identity headers")
        name = names[0].strip()
        version = Version(versions[0].strip())
    except (UnicodeDecodeError, InvalidVersion, ValueError, TypeError) as exc:
        raise RuntimeError(f"Core wheel {wheel_name} has invalid METADATA") from exc
    if canonicalize_name(name) != "dcc-mcp-core":
        raise RuntimeError(f"Core wheel {wheel_name} has invalid METADATA identity")
    return name, version


def verify_core_wheel(wheel_path: Path, expected_version: str) -> dict:
    """Verify one selected Core wheel and return immutable provenance."""
    import zipfile

    wheel_bytes = wheel_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        file_names = [info.filename for info in archive.infolist() if not info.is_dir()]
        metadata_names = [
            name for name in file_names if name.casefold().endswith(".dist-info/metadata") and name.count("/") == 1
        ]
        if len(metadata_names) != 1:
            raise RuntimeError(f"Core wheel {wheel_path.name} must contain exactly one top-level METADATA")
        metadata_name = metadata_names[0]
        metadata_content = archive.read(metadata_name)
        _metadata_name, metadata_version = _parse_core_metadata(metadata_content, wheel_path.name)
        try:
            expected = Version(expected_version)
        except InvalidVersion as exc:
            raise RuntimeError(f"Core wheel {wheel_path.name} expected version is invalid") from exc
        if metadata_version != expected:
            raise RuntimeError(f"Core wheel {wheel_path.name} identity does not match dcc-mcp-core {expected_version}")

        dist_info_dir = metadata_name.rsplit("/", 1)[0]
        record_name = dist_info_dir + "/RECORD"
        if record_name not in file_names:
            raise RuntimeError(f"Core wheel {wheel_path.name} is missing RECORD")
        try:
            rows = list(csv.reader(io.StringIO(archive.read(record_name).decode("utf-8"))))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise RuntimeError(f"Core wheel {wheel_path.name} has invalid RECORD") from exc
        records = {}
        for row in rows:
            if len(row) != 3 or not row[0] or row[0] in records:
                raise RuntimeError(f"Core wheel {wheel_path.name} has ambiguous RECORD entries")
            records[row[0]] = (row[1], row[2])

        bound_names = [name for name in file_names if name.startswith("dcc_mcp_core/")]
        bound_names.append(metadata_name)
        if not any(name.startswith("dcc_mcp_core/") for name in bound_names):
            raise RuntimeError(f"Core wheel {wheel_path.name} has no dcc_mcp_core payload")
        payload_files = {}
        for name in bound_names:
            digest_value, size_value = records.get(name, (None, None))
            content = archive.read(name)
            if digest_value != "sha256=" + _record_digest(content) or size_value != str(len(content)):
                raise RuntimeError(f"Core wheel {wheel_path.name} RECORD does not bind {name}")
            if name.startswith("dcc_mcp_core/"):
                payload_files[name] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}

    return {
        "filename": wheel_path.name,
        "sha256": hashlib.sha256(wheel_bytes).hexdigest(),
        "metadata": metadata_content,
        "payload_files": payload_files,
        "wheel_bytes": wheel_bytes,
    }


def _bind_extracted_core_objects(module_dir: Path, expected_roots: dict) -> None:
    for root_name, expected in expected_roots.items():
        runtime_root = module_dir / root_name
        core_root = runtime_root / "dcc_mcp_core"
        _assert_safe_assembled_directory(runtime_root)
        _assert_safe_assembled_directory(core_root)
        actual_paths = _safe_regular_file_paths(core_root, runtime_root)
        if actual_paths != set(expected["files"]):
            raise RuntimeError("Core payload changed after verified wheel extraction")
        identities = {}
        directory_identities = {}
        for relative_path, record in expected["files"].items():
            captured, directories = _capture_bound_assembled_file(runtime_root, runtime_root / relative_path)
            if {"sha256": captured["sha256"], "size": captured["size"]} != record:
                raise RuntimeError("Core payload changed after verified wheel extraction")
            identities[relative_path] = captured["identity"]
            directory_identities.update(directories)
        metadata_path = runtime_root / expected["metadata_path"]
        _assert_safe_assembled_directory(metadata_path.parent)
        metadata, metadata_directories = _capture_bound_assembled_file(runtime_root, metadata_path)
        if {"sha256": metadata["sha256"], "size": metadata["size"]} != expected["metadata"]:
            raise RuntimeError("Core payload changed after verified wheel extraction")
        directory_identities.update(metadata_directories)
        expected["identities"] = identities
        expected["metadata_identity"] = metadata["identity"]
        expected["directory_identities"] = directory_identities


def _write_core_provenance(
    module_dir: Path, core_version: str, wheel_provenance: List[dict], expected_roots: dict
) -> dict:
    roots = {}
    metadata_name = f"dcc_mcp_core-{core_version}.dist-info/METADATA"
    for root_name in ("python", "python37"):
        runtime_root = module_dir / root_name
        core_root = runtime_root / "dcc_mcp_core"
        if not core_root.is_dir():
            continue
        _assert_safe_assembled_directory(runtime_root)
        _assert_safe_assembled_directory(core_root)
        metadata_path = runtime_root / metadata_name
        if not metadata_path.is_file():
            raise RuntimeError(f"Missing preserved Core METADATA for {root_name}")
        _assert_safe_assembled_directory(metadata_path.parent)
        actual_paths = _safe_regular_file_paths(core_root, runtime_root)
        actual_files = {}
        actual_identities = {}
        expected = expected_roots.get(root_name)
        if expected is None or actual_paths != set(expected["files"]):
            raise RuntimeError("Core payload changed after verified wheel extraction")
        for relative_path in sorted(actual_paths):
            captured, _ = _capture_bound_assembled_file(
                runtime_root,
                runtime_root / relative_path,
                expected.get("directory_identities"),
            )
            actual_files[relative_path] = {"sha256": captured["sha256"], "size": captured["size"]}
            actual_identities[relative_path] = captured["identity"]
        if not actual_files:
            raise RuntimeError(f"Missing bundled Core payload for {root_name}")
        captured_metadata, _ = _capture_bound_assembled_file(
            runtime_root,
            metadata_path,
            expected.get("directory_identities"),
        )
        actual_metadata = {"sha256": captured_metadata["sha256"], "size": captured_metadata["size"]}
        if expected is None or actual_files != expected["files"] or actual_metadata != expected["metadata"]:
            raise RuntimeError("Core payload changed after verified wheel extraction")
        if actual_identities != expected.get("identities") or captured_metadata["identity"] != expected.get(
            "metadata_identity"
        ):
            raise RuntimeError("Core payload object changed after verified wheel extraction")
        files = [
            {"path": f"{root_name}/{relative_path}", **record} for relative_path, record in sorted(actual_files.items())
        ]
        roots[root_name] = {
            "metadata": {
                "path": metadata_path.relative_to(module_dir).as_posix(),
                **actual_metadata,
            },
            "files": files,
        }
    if not roots:
        raise RuntimeError("No bundled Core runtime roots were assembled")
    provenance = {
        "schema_version": 1,
        "name": "dcc-mcp-core",
        "version": core_version,
        "source_wheels": [
            {"filename": item["filename"], "sha256": item["sha256"]}
            for item in sorted(wheel_provenance, key=lambda item: item["filename"])
        ],
        "roots": roots,
    }
    content = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (module_dir / CORE_PROVENANCE_PATH).write_bytes(content)
    _assert_bound_core_objects(module_dir, expected_roots)
    return {"path": CORE_PROVENANCE_PATH, "sha256": hashlib.sha256(content).hexdigest()}


def _assert_bound_core_objects(module_dir: Path, expected_roots: dict) -> None:
    for root_name, expected in expected_roots.items():
        runtime_root = module_dir / root_name
        core_root = runtime_root / "dcc_mcp_core"
        _assert_safe_assembled_directory(runtime_root)
        _assert_safe_assembled_directory(core_root)
        actual_paths = _safe_regular_file_paths(core_root, runtime_root)
        if actual_paths != set(expected["files"]):
            raise RuntimeError("Core payload root set changed after provenance binding")
        for relative_path, record in expected["files"].items():
            captured, _ = _capture_bound_assembled_file(
                runtime_root,
                runtime_root / relative_path,
                expected.get("directory_identities"),
            )
            if {"sha256": captured["sha256"], "size": captured["size"]} != record or captured["identity"] != expected[
                "identities"
            ].get(relative_path):
                raise RuntimeError("Core payload changed after provenance binding")
        metadata_path = runtime_root / expected["metadata_path"]
        _assert_safe_assembled_directory(metadata_path.parent)
        metadata, _ = _capture_bound_assembled_file(
            runtime_root,
            metadata_path,
            expected.get("directory_identities"),
        )
        if {"sha256": metadata["sha256"], "size": metadata["size"]} != expected["metadata"] or metadata[
            "identity"
        ] != expected["metadata_identity"]:
            raise RuntimeError("Core METADATA changed after provenance binding")


def _validate_archive_core_payload(archive_path: Path, base_dir: str, expected_roots: dict) -> None:
    with zipfile.ZipFile(str(archive_path)) as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        if len(names) != len(set(names)):
            raise RuntimeError("Archive contains duplicate paths")
        name_set = set(names)
        for root_name, expected in expected_roots.items():
            core_prefix = f"{base_dir}/{root_name}/dcc_mcp_core/"
            actual_core = {name for name in name_set if name.startswith(core_prefix)}
            expected_core = {f"{base_dir}/{root_name}/{relative}" for relative in expected["files"]}
            if actual_core != expected_core:
                raise RuntimeError("Archive Core payload root set does not match the verified wheel")
            for relative_path, record in expected["files"].items():
                content = archive.read(f"{base_dir}/{root_name}/{relative_path}")
                if {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)} != record:
                    raise RuntimeError("Archive Core payload does not match the verified wheel")
            metadata_content = archive.read(f"{base_dir}/{root_name}/{expected['metadata_path']}")
            if {
                "sha256": hashlib.sha256(metadata_content).hexdigest(),
                "size": len(metadata_content),
            } != expected["metadata"]:
                raise RuntimeError("Archive Core METADATA does not match the verified wheel")


def _make_bound_archive(base_name: Path, root_dir: Path, base_dir: str, expected_roots: dict) -> Path:
    module_dir = root_dir / base_dir
    try:
        _assert_bound_core_objects(module_dir, expected_roots)
        archive_path = Path(shutil.make_archive(str(base_name), "zip", root_dir=root_dir, base_dir=base_dir))
        _assert_bound_core_objects(module_dir, expected_roots)
        _validate_archive_core_payload(archive_path, base_dir, expected_roots)
        _assert_bound_core_objects(module_dir, expected_roots)
    except (OSError, RuntimeError, zipfile.BadZipFile, KeyError) as exc:
        raise RuntimeError("Core payload changed during archive consumption") from exc
    return archive_path


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
    _extract_wheel_bytes(wheel_path.read_bytes(), dest, extensions_only=extensions_only, alt_dest=alt_dest)


def _extract_wheel_bytes(
    wheel_bytes: bytes, dest: Path, *, extensions_only: bool = False, alt_dest: Optional[Path] = None
) -> None:
    """Extract one already-captured wheel payload without reopening its source path."""
    import zipfile

    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as zf:
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


def generate_module_info(
    version: str,
    platform: str = "win64",
    *,
    project_root: Optional[Path] = None,
    embedded_core_version: Optional[str] = None,
    bundled_server_version: Optional[str] = None,
    core_provenance: Optional[dict] = None,
) -> str:
    """Generate module-info.json content with build metadata."""
    minimum_core, maximum_core = dependency_bounds(
        project_root or Path(__file__).resolve().parents[1],
        "dcc-mcp-core",
    )
    info = {
        "name": "dcc_mcp_maya",
        "version": version,
        "adapter_version": version,
        "embedded_core_version": embedded_core_version,
        "bundled_server_version": bundled_server_version,
        "core_provenance": core_provenance,
        "min_core_version": minimum_core,
        "max_core_version_exclusive": maximum_core,
        "supported_maya_versions": supported_maya_versions(platform),
        "has_python37": platform in PLATFORMS_WITH_CP37_WHEELS,
    }
    return json.dumps(info, indent=2) + "\n"


def assemble(project_root: Path, version: str, platform: str, output: Path, *, _with_core_contract: bool = False):
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
        full_wheels = abi3_wheels or wheels
        if len(full_wheels) != 1 or len(cp37_wheels) > 1:
            raise RuntimeError("Core wheel selection is missing or ambiguous")
        verified_wheels = [verify_core_wheel(wheel, core_version) for wheel in wheels]
        verified_by_name = {item["filename"]: item for item in verified_wheels}

        for wheel in full_wheels:
            print(f"  Extracting {wheel.name} to python/...")
            _extract_wheel_bytes(verified_by_name[wheel.name]["wheel_bytes"], python_dir)
        metadata_name = f"dcc_mcp_core-{core_version}.dist-info"
        metadata_dir = python_dir / metadata_name
        metadata_dir.mkdir()
        full_verified = verified_by_name[full_wheels[0].name]
        metadata_dir.joinpath("METADATA").write_bytes(full_verified["metadata"])
        expected_roots = {
            "python": {
                "metadata_path": f"{metadata_name}/METADATA",
                "metadata": {
                    "sha256": hashlib.sha256(full_verified["metadata"]).hexdigest(),
                    "size": len(full_verified["metadata"]),
                },
                "files": dict(full_verified["payload_files"]),
            }
        }

        if cp37_wheels:
            shutil.copytree(str(python_dir), str(python37_dir))
            python37_files = dict(full_verified["payload_files"])
            for wheel in cp37_wheels:
                print(f"  Extracting {wheel.name} extensions to python37/...")
                cp37_verified = verified_by_name[wheel.name]
                _extract_wheel_bytes(cp37_verified["wheel_bytes"], python37_dir, extensions_only=True)
                python37_files.update(
                    {
                        path: record
                        for path, record in cp37_verified["payload_files"].items()
                        if Path(path).suffix in (".pyd", ".so", ".dylib")
                    }
                )
            expected_roots["python37"] = {
                "metadata_path": f"{metadata_name}/METADATA",
                "metadata": dict(expected_roots["python"]["metadata"]),
                "files": python37_files,
            }

        for package_root in (python_dir, python37_dir):
            if not package_root.is_dir():
                continue
            print(f"  Extracting {server_wheel.name} to {package_root.name}/...")
            extract_server_wheel(server_wheel, package_root)
        _bind_extracted_core_objects(module_dir, expected_roots)
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

    # 6. Bind every bundled Core payload file to verified wheel provenance.
    core_provenance = _write_core_provenance(module_dir, core_version, verified_wheels, expected_roots)
    print("  Generated core-provenance.json")

    # 7. Generate version contract metadata for release smoke reports
    info_content = generate_module_info(
        version,
        platform,
        project_root=project_root,
        embedded_core_version=core_version,
        bundled_server_version=server_version,
        core_provenance=core_provenance,
    )
    (module_dir / "module-info.json").write_text(info_content, encoding="utf-8")
    print("  Generated module-info.json")

    return (module_dir, expected_roots) if _with_core_contract else module_dir


def assemble_portable(
    project_root: Path, version: str, platform: str, output: Path, *, _with_core_contract: bool = False
):
    """Assemble the portable ZIP with install scripts."""
    module_dir, expected_roots = assemble(project_root, version, platform, output, _with_core_contract=True)

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
    return (module_dir, expected_roots) if _with_core_contract else module_dir


def assemble_pipeline(
    project_root: Path, version: str, platform: str, output: Path, *, _with_core_contract: bool = False
):
    """Assemble the pipeline ZIP with module-info.json, no install scripts."""
    module_dir, expected_roots = assemble(project_root, version, platform, output, _with_core_contract=True)

    # Add README-pipeline.txt
    readme_src = project_root / "packaging" / "README-pipeline.txt"
    if readme_src.exists():
        shutil.copy2(readme_src, module_dir / "README-pipeline.txt")

    print("  Added module-info.json and README-pipeline.txt (pipeline)")
    return (module_dir, expected_roots) if _with_core_contract else module_dir


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
    _portable_module, portable_contract = assemble_portable(
        project_root, args.version, args.platform, portable_output, _with_core_contract=True
    )
    zip_path = portable_output / f"dcc-mcp-maya-{args.version}-{args.platform}"
    archive_path = _make_bound_archive(zip_path, portable_output, "dcc-mcp-maya", portable_contract)
    print(f"Created: {archive_path}")

    # --- Pipeline ZIP ---
    print(f"\nAssembling pipeline .mod module for platform={args.platform}, version={args.version}")
    pipeline_output = output_dir / "pipeline"
    pipeline_output.mkdir(parents=True, exist_ok=True)
    _pipeline_module, pipeline_contract = assemble_pipeline(
        project_root, args.version, args.platform, pipeline_output, _with_core_contract=True
    )
    zip_path = pipeline_output / f"dcc-mcp-maya-{args.version}-{args.platform}-pipeline"
    archive_path = _make_bound_archive(zip_path, pipeline_output, "dcc-mcp-maya", pipeline_contract)
    print(f"Created: {archive_path}")


if __name__ == "__main__":
    main()
