"""Agent-first Install SOP v1 lifecycle for the Maya adapter."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import dcc_mcp_core
from dcc_mcp_core.install_lifecycle import inspect_install_root, safe_remove_tree, wait_for_sidecar_ready

from dcc_mcp_maya.__version__ import __version__

try:
    from dcc_mcp_core.deployment import (
        INSTALL_EXIT_ACQUIRE,
        INSTALL_EXIT_CODES,
        INSTALL_EXIT_INSTALL,
        INSTALL_EXIT_OK,
        INSTALL_EXIT_PREFLIGHT,
        INSTALL_EXIT_REQUIRES_RESTART,
        INSTALL_EXIT_VERIFY,
        INSTALL_SOP_SCHEMA_VERSION,
        load_install_sop_schema,
    )
except ImportError:
    INSTALL_SOP_SCHEMA_VERSION = 1
    INSTALL_EXIT_OK = 0
    INSTALL_EXIT_PREFLIGHT = 10
    INSTALL_EXIT_ACQUIRE = 20
    INSTALL_EXIT_INSTALL = 30
    INSTALL_EXIT_VERIFY = 40
    INSTALL_EXIT_REQUIRES_RESTART = 50
    INSTALL_EXIT_CODES = {
        "ok": INSTALL_EXIT_OK,
        "preflight": INSTALL_EXIT_PREFLIGHT,
        "acquire": INSTALL_EXIT_ACQUIRE,
        "install": INSTALL_EXIT_INSTALL,
        "verify": INSTALL_EXIT_VERIFY,
        "requires_restart": INSTALL_EXIT_REQUIRES_RESTART,
    }

    def load_install_sop_schema():
        schema_path = Path(__file__).resolve().parent / "schemas" / "adapter-install-sop-v1.schema.json"
        return json.loads(schema_path.read_text(encoding="utf-8"))


DCC_TYPE = "maya"
COMMAND = "dcc-mcp-maya"
MIN_CORE_VERSION = "0.19.45"
MIN_MAYA_VERSION = 2020
MAX_MAYA_VERSION = 2027
LIFECYCLE_COMMANDS = ("install", "status", "verify", "uninstall", "upgrade")
DEFAULT_RECEIPT_PATH = Path.home() / ".dcc-mcp" / "receipts" / "maya.json"
USER_SETUP_BEGIN = "# >>> dcc-mcp-maya Install SOP v1 >>>"
USER_SETUP_END = "# <<< dcc-mcp-maya Install SOP v1 <<<"
MAX_MODULE_ZIP_FILES = 20000
MAX_MODULE_ZIP_BYTES = 512 * 1024 * 1024


class LifecycleError(RuntimeError):
    """A stable, classified Install SOP failure."""

    def __init__(self, exit_code, stage, reason, message):
        super().__init__(message)
        self.exit_code = exit_code
        self.stage = stage
        self.reason = reason


@dataclass(frozen=True)
class InstallContext:
    host_path: Path
    host_version: str
    python_path: Path
    python_version: str
    python_selection_source: str
    core_version: str
    modules_dir: Path
    scripts_dir: Path
    module_root: Path
    descriptor_path: Path
    user_setup_path: Path
    receipt_path: Path
    state: str
    state_stage: str
    state_reason: str
    module_zip: Optional[Path]


def _version_tuple(value):
    match = re.search(r"\d+(?:\.\d+)*", str(value))
    if match is None:
        return ()
    return tuple(int(part) for part in match.group(0).split("."))


def _probe_target(python_path):
    script = (
        "import json,sys; import maya.cmds as cmds; "
        "import dcc_mcp_core,dcc_mcp_maya; "
        "print(json.dumps({'maya_version':str(cmds.about(version=True)),"
        "'python_version':'.'.join(map(str,sys.version_info[:3])),"
        "'core_version':dcc_mcp_core.__version__,"
        "'adapter_version':dcc_mcp_maya.__version__}))"
    )
    try:
        completed = subprocess.run(
            [str(python_path), "-c", script],
            check=False,
            capture_output=True,
            universal_newlines=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "python",
            "python_probe_failed",
            "Could not execute the selected mayapy: %s" % exc,
        ) from exc
    if completed.returncode != 0:
        diagnostic = (completed.stderr or completed.stdout).strip()[-2000:]
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "python",
            "target_import_failed",
            "The selected mayapy cannot import Maya, the adapter, and Core: %s" % diagnostic,
        )
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "python",
            "python_probe_invalid",
            "The selected mayapy returned invalid version metadata.",
        ) from exc
    return {str(key): str(value) for key, value in payload.items()}


def _default_maya_root():
    if os.name == "nt":
        return Path.home() / "Documents" / "maya"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Preferences" / "Autodesk" / "maya"
    return Path.home() / "maya"


def _candidate_host_paths(environ):
    for variable in ("DCC_MCP_MAYA_DCC_PATH", "MAYA_LOCATION"):
        value = environ.get(variable)
        if value:
            yield Path(value)
    mayapy_env = environ.get("DCC_MCP_MAYA_MAYAPY") or environ.get("MAYAPY")
    if mayapy_env:
        yield Path(mayapy_env)
    on_path = shutil.which("mayapy")
    if on_path:
        yield Path(on_path)
    if os.name == "nt":
        for root in (environ.get("ProgramFiles"), environ.get("ProgramFiles(x86)")):
            if not root:
                continue
            for year in range(MAX_MAYA_VERSION, MIN_MAYA_VERSION - 1, -1):
                yield Path(root) / "Autodesk" / ("Maya%s" % year)
    elif sys.platform == "darwin":
        for year in range(MAX_MAYA_VERSION, MIN_MAYA_VERSION - 1, -1):
            yield Path("/Applications/Autodesk/maya%s/Maya.app" % year)
    else:
        for year in range(MAX_MAYA_VERSION, MIN_MAYA_VERSION - 1, -1):
            yield Path("/usr/autodesk/maya%s" % year)


def _resolve_host_path(explicit, python_path, environ):
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if candidate.exists():
            return candidate
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "host",
            "dcc_path_missing",
            "Maya path does not exist: %s" % candidate,
        )
    if python_path:
        interpreter = Path(python_path).expanduser().resolve()
        if interpreter.is_file() and "mayapy" in interpreter.name.lower():
            return interpreter.parent.parent if interpreter.parent.name.lower() == "bin" else interpreter
    seen = set()
    for value in _candidate_host_paths(environ):
        candidate = value.expanduser().resolve()
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            if candidate.is_file() and "mayapy" in candidate.name.lower() and candidate.parent.name.lower() == "bin":
                return candidate.parent.parent
            return candidate
    raise LifecycleError(
        INSTALL_EXIT_PREFLIGHT,
        "host",
        "dcc_path_required",
        "Maya was not discovered; pass its installation or executable with --dcc-path.",
    )


def _resolve_python(host_path, explicit, environ):
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        source = "--python"
    elif environ.get("DCC_MCP_MAYA_MAYAPY") or environ.get("MAYAPY"):
        candidate = Path(environ.get("DCC_MCP_MAYA_MAYAPY") or environ["MAYAPY"]).expanduser().resolve()
        source = "environment"
    elif host_path.is_file() and "mayapy" in host_path.name.lower():
        candidate = host_path
        source = "discovered"
    elif host_path.is_dir() and host_path.suffix.lower() == ".app":
        candidate = host_path / "Contents" / "bin" / "mayapy"
        source = "discovered"
    elif host_path.is_dir():
        name = "mayapy.exe" if os.name == "nt" else "mayapy"
        candidate = host_path / "bin" / name
        source = "discovered"
    else:
        name = "mayapy.exe" if os.name == "nt" else "mayapy"
        candidate = host_path.parent / name
        source = "discovered"
    if not candidate.is_file():
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "python",
            "mayapy_missing",
            "Pass the exact Maya interpreter with --python; not found: %s" % candidate,
        )
    return candidate, source


def _resolve_context(dcc_path, python_path, environ, module_zip=None):
    host_path = _resolve_host_path(dcc_path, python_path, environ)
    interpreter, selection_source = _resolve_python(host_path, python_path, environ)
    probe = _probe_target(interpreter)
    maya_version = _version_tuple(probe.get("maya_version", ""))
    if not maya_version or not MIN_MAYA_VERSION <= maya_version[0] <= MAX_MAYA_VERSION:
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "host_version",
            "unsupported_maya_version",
            "Maya 2020 through 2027 is required; detected %r." % probe.get("maya_version"),
        )
    if probe.get("adapter_version") != __version__:
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "python",
            "adapter_version_mismatch",
            "The selected mayapy must import dcc-mcp-maya %s." % __version__,
        )
    if _version_tuple(probe.get("python_version", "")) < (3, 7):
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "python",
            "unsupported_python_version",
            "The selected mayapy must use Python 3.7 or newer.",
        )
    if _version_tuple(probe.get("core_version", "")) < _version_tuple(MIN_CORE_VERSION):
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "core_version",
            "core_version_unsupported",
            "dcc-mcp-core>=%s is required in the selected mayapy." % MIN_CORE_VERSION,
        )
    maya_root = _default_maya_root()
    modules_dir = Path(environ.get("DCC_MCP_MAYA_MODULES_DIR", str(maya_root / "modules"))).expanduser().resolve()
    scripts_dir = Path(environ.get("DCC_MCP_MAYA_SCRIPTS_DIR", str(maya_root / "scripts"))).expanduser().resolve()
    receipt_path = Path(environ.get("DCC_MCP_MAYA_RECEIPT", str(DEFAULT_RECEIPT_PATH))).expanduser().resolve()
    payload_path = Path(module_zip).expanduser().resolve() if module_zip else None
    if payload_path is not None and not payload_path.is_file():
        raise LifecycleError(
            INSTALL_EXIT_ACQUIRE,
            "acquire",
            "module_zip_missing",
            "The requested Maya module ZIP does not exist: %s" % payload_path,
        )
    module_root = modules_dir / "dcc-mcp-maya"
    descriptor_path = modules_dir / "dcc_mcp_maya.mod"
    user_setup_path = scripts_dir / "userSetup.py"
    state, state_stage, state_reason = _inspect_state(
        receipt_path,
        module_root,
        descriptor_path,
        user_setup_path,
    )
    return InstallContext(
        host_path=host_path,
        host_version=str(maya_version[0]),
        python_path=interpreter,
        python_version=probe["python_version"],
        python_selection_source=selection_source,
        core_version=probe["core_version"],
        modules_dir=modules_dir,
        scripts_dir=scripts_dir,
        module_root=module_root,
        descriptor_path=descriptor_path,
        user_setup_path=user_setup_path,
        receipt_path=receipt_path,
        state=state,
        state_stage=state_stage,
        state_reason=state_reason,
        module_zip=payload_path,
    )


def _base_report(ctx, command, status):
    return {
        "schema_version": INSTALL_SOP_SCHEMA_VERSION,
        "status": status,
        "dcc_type": DCC_TYPE,
        "command": command,
        "adapter_version": __version__,
        "core_version": ctx.core_version,
        "steps": [],
        "next_steps": [],
        "receipt_path": str(ctx.receipt_path),
        "verify": {"directly_usable": False, "failure_stage": None, "failure_reason": None},
        "host": {"path": str(ctx.host_path), "version": ctx.host_version},
        "python": {
            "path": str(ctx.python_path),
            "version": ctx.python_version,
            "selection_source": ctx.python_selection_source,
        },
        "install_state": ctx.state,
        "artifacts": {
            "module_root": str(ctx.module_root),
            "descriptor": str(ctx.descriptor_path),
            "user_setup": str(ctx.user_setup_path),
        },
    }


def _command_for(ctx, command, execute=False):
    command_line = [
        COMMAND,
        command,
        "--dcc-path",
        str(ctx.host_path),
        "--python",
        str(ctx.python_path),
        "--json",
    ]
    if execute:
        command_line.append("--yes")
    if ctx.module_zip is not None:
        command_line.extend(["--module-zip", str(ctx.module_zip)])
    return command_line


def _plan(ctx, command):
    report = _base_report(ctx, command, "planned")
    report["plan_type"] = "upgrade" if command == "upgrade" else ("repair" if ctx.state == "partial" else ctx.state)
    if command == "uninstall":
        step_ids = ("preflight", "receipt", "uninstall")
    else:
        step_ids = ("preflight", "stage", "commit", "verify")
    report["steps"] = [{"id": step, "status": "ok" if step == "preflight" else "planned"} for step in step_ids]
    report["next_steps"] = [
        {
            "id": "execute_%s" % command,
            "description": "Execute the validated Maya %s plan." % command,
            "command": list(_command_for(ctx, command, execute=True)),
            "why": "Planning and dry-run modes do not modify Maya's user profile.",
        }
    ]
    return report


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_sha256(path):
    digest = hashlib.sha256()
    for item in sorted((candidate for candidate in path.rglob("*") if candidate.is_file()), key=lambda p: p.as_posix()):
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(_sha256(item)))
    return digest.hexdigest()


def _read_receipt(path, required=False):
    if not path.is_file():
        if required:
            raise LifecycleError(
                INSTALL_EXIT_PREFLIGHT,
                "receipt",
                "receipt_missing",
                "No Maya install receipt exists at %s." % path,
            )
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "receipt",
            "receipt_invalid",
            "The Maya install receipt is unreadable: %s" % exc,
        ) from exc
    if not isinstance(value, dict) or value.get("receipt_version") != 1 or value.get("dcc_type") != DCC_TYPE:
        raise LifecycleError(
            INSTALL_EXIT_PREFLIGHT,
            "receipt",
            "receipt_invalid",
            "The Maya install receipt has an unsupported schema or owner.",
        )
    return value


def _artifact_digest(entry):
    path = Path(str(entry.get("path", ""))).expanduser().resolve()
    if entry.get("kind") == "tree":
        return _tree_sha256(path) if path.is_dir() else None
    return _sha256(path) if path.is_file() else None


def _inspect_state(receipt_path, module_root, descriptor_path, user_setup_path):
    if not receipt_path.is_file():
        if module_root.exists() or descriptor_path.exists():
            return "partial", "receipt", "unreceipted_install"
        if user_setup_path.is_file():
            try:
                user_setup = user_setup_path.read_text(encoding="utf-8")
            except OSError:
                user_setup = ""
            if USER_SETUP_BEGIN in user_setup or USER_SETUP_END in user_setup:
                return "partial", "receipt", "unreceipted_user_setup"
        return "fresh", "", ""
    try:
        receipt = _read_receipt(receipt_path, required=True)
    except LifecycleError:
        return "partial", "receipt", "receipt_invalid"
    artifacts = receipt.get("artifacts") if receipt else None
    if not isinstance(artifacts, list) or len(artifacts) != 3 or not all(isinstance(item, dict) for item in artifacts):
        return "partial", "receipt", "receipt_ownership_invalid"
    expected = {
        "tree": module_root.resolve(),
        "file": descriptor_path.resolve(),
        "user_setup": user_setup_path.resolve(),
    }
    for entry in artifacts:
        kind = entry.get("kind")
        if kind not in expected:
            return "partial", "receipt", "receipt_ownership_invalid"
        try:
            recorded = Path(str(entry.get("path", ""))).expanduser().resolve()
        except OSError:
            return "partial", "receipt", "receipt_ownership_invalid"
        if recorded != expected[kind]:
            return "partial", "receipt", "receipt_target_mismatch"
        if _artifact_digest(entry) != entry.get("sha256"):
            return "partial", "artifact", "%s_missing_or_modified" % kind
    return ("current" if receipt.get("adapter_version") == __version__ else "upgrade"), "", ""


def _replace_path(source, destination):
    os.replace(str(source), str(destination))


def _remove_path(path):
    if not path.exists():
        return
    if path.is_dir():
        result = safe_remove_tree(path)
        if not result.get("success"):
            raise OSError(str(result.get("message") or result.get("reason") or "tree removal failed"))
    else:
        path.unlink()


def _is_windows_lock(exc):
    return os.name == "nt" and (isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32, 33})


def _asset_path(relative):
    package_asset = Path(__file__).resolve().parent / "install_assets" / relative
    if package_asset.is_file():
        return package_asset
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / relative
    if not source.is_file():
        raise LifecycleError(
            INSTALL_EXIT_ACQUIRE,
            "acquire",
            "install_asset_missing",
            "Required Maya install asset is missing: %s" % relative,
        )
    return source


def _platform_token():
    if os.name == "nt":
        return "win64"
    return "macos" if sys.platform == "darwin" else "linux"


def _render_descriptor(module_root, has_python37=False):
    lines = []
    module_path = module_root.as_posix()
    for year in range(MIN_MAYA_VERSION, MAX_MAYA_VERSION + 1):
        lines.append(
            "+ MAYAVERSION:%s PLATFORM:%s dcc_mcp_maya %s %s" % (year, _platform_token(), __version__, module_path)
        )
        python_dir = "python37" if has_python37 and year <= 2022 else "python"
        lines.append("PYTHONPATH+:=%s" % python_dir)
        lines.append("PLUG_IN_PATH+:=plug-ins")
    return "\n".join(lines) + "\n"


def _managed_user_setup_block(bootstrap_error_dir):
    return "\n".join(
        [
            USER_SETUP_BEGIN,
            "try:",
            "    import os as _dcc_mcp_maya_os",
            "    _dcc_mcp_maya_os.environ.setdefault(",
            "        'DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR', %s," % json.dumps(str(bootstrap_error_dir)),
            "    )",
            "    from dcc_mcp_maya.install import bootstrap_user_setup as _dcc_mcp_maya_bootstrap",
            "    _dcc_mcp_maya_bootstrap()",
            "except Exception:",
            "    import logging as _dcc_mcp_maya_logging",
            "    _dcc_mcp_maya_logging.getLogger('dcc_mcp_maya.install').exception('Maya MCP bootstrap failed')",
            USER_SETUP_END,
        ]
    )


def _strip_managed_user_setup(content):
    pattern = re.compile(
        r"(?:\r?\n)?%s.*?%s(?:\r?\n)?" % (re.escape(USER_SETUP_BEGIN), re.escape(USER_SETUP_END)),
        re.DOTALL,
    )
    return pattern.sub("\n", content).strip("\n")


def _render_user_setup(current, bootstrap_error_dir):
    base = _strip_managed_user_setup(current)
    return ((base + "\n\n") if base else "") + _managed_user_setup_block(bootstrap_error_dir) + "\n"


def bootstrap_user_setup(defer=True):
    """Schedule the fixed plug-in load and capture any bootstrap exception."""
    from dcc_mcp_core import capture_bootstrap_errors

    from maya import cmds

    log_dir = os.environ.get("DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR") or str(
        DEFAULT_RECEIPT_PATH.parent / "bootstrap-errors"
    )

    def load_plugin():
        with capture_bootstrap_errors(
            DCC_TYPE,
            adapter_version=__version__,
            min_core_version=MIN_CORE_VERSION,
            phase="userSetup",
            log_dir=log_dir,
        ):
            if not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
                cmds.loadPlugin("dcc_mcp_maya_plugin", quiet=True)

    if defer:
        cmds.evalDeferred(load_plugin, lowestPriority=True)
    else:
        load_plugin()


def _validate_module_zip(payload):
    try:
        archive = zipfile.ZipFile(str(payload))
    except (OSError, zipfile.BadZipFile) as exc:
        raise LifecycleError(
            INSTALL_EXIT_ACQUIRE,
            "acquire",
            "invalid_module_zip",
            "The Maya module ZIP cannot be opened: %s" % exc,
        ) from exc
    with archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        if not files or len(files) > MAX_MODULE_ZIP_FILES:
            raise LifecycleError(
                INSTALL_EXIT_ACQUIRE,
                "acquire",
                "module_zip_bounds_exceeded",
                "The Maya module ZIP has an invalid or excessive file count.",
            )
        if sum(info.file_size for info in files) > MAX_MODULE_ZIP_BYTES:
            raise LifecycleError(
                INSTALL_EXIT_ACQUIRE,
                "acquire",
                "module_zip_bounds_exceeded",
                "The expanded Maya module ZIP exceeds the size limit.",
            )
        normalized = {}
        folded_files = set()
        folded_parents = set()
        for info in files:
            parts = Path(info.filename.replace("\\", "/")).parts
            mode = info.external_attr >> 16
            unsafe = (
                info.flag_bits & 0x1
                or not parts
                or Path(info.filename).is_absolute()
                or ".." in parts
                or ":" in parts[0]
                or (mode & 0o170000) == 0o120000
            )
            if unsafe:
                raise LifecycleError(
                    INSTALL_EXIT_ACQUIRE,
                    "acquire",
                    "unsafe_module_zip",
                    "The Maya module ZIP contains an unsafe path or entry.",
                )
            relative_parts = parts[1:] if parts[0] == "dcc-mcp-maya" else parts
            if not relative_parts:
                continue
            relative_path = "/".join(relative_parts)
            folded_path = relative_path.casefold()
            folded_ancestors = {
                "/".join(part.casefold() for part in relative_parts[:index]) for index in range(1, len(relative_parts))
            }
            collides = (
                folded_path in folded_files
                or folded_path in folded_parents
                or bool(folded_ancestors.intersection(folded_files))
            )
            if collides:
                raise LifecycleError(
                    INSTALL_EXIT_ACQUIRE,
                    "acquire",
                    "module_zip_path_collision",
                    "The Maya module ZIP maps multiple entries to the same destination.",
                )
            folded_files.add(folded_path)
            folded_parents.update(folded_ancestors)
            normalized[relative_path] = info.filename
    required = {
        "python/dcc_mcp_maya/__init__.py",
        "plug-ins/dcc_mcp_maya_plugin.py",
        "scripts/userSetup.py",
        "module-info.json",
    }
    if not required.issubset(normalized):
        raise LifecycleError(
            INSTALL_EXIT_ACQUIRE,
            "acquire",
            "module_zip_contract_missing",
            "The Maya module ZIP is missing its package, plug-in, or userSetup payload.",
        )
    with zipfile.ZipFile(str(payload)) as archive:
        try:
            module_info = json.loads(archive.read(normalized["module-info.json"]).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, ValueError) as exc:
            raise LifecycleError(
                INSTALL_EXIT_ACQUIRE,
                "acquire",
                "module_zip_metadata_invalid",
                "The Maya module ZIP has invalid module-info.json metadata.",
            ) from exc
    if not isinstance(module_info, dict) or module_info.get("name") != "dcc_mcp_maya":
        raise LifecycleError(
            INSTALL_EXIT_ACQUIRE,
            "acquire",
            "module_zip_metadata_invalid",
            "The module ZIP does not identify the dcc_mcp_maya adapter.",
        )
    if module_info.get("adapter_version") != __version__:
        raise LifecycleError(
            INSTALL_EXIT_ACQUIRE,
            "acquire",
            "module_zip_version_mismatch",
            "The module ZIP adapter version does not match the installed lifecycle command.",
        )
    return normalized


def _extract_module_zip(payload, stage):
    validated_entries = _validate_module_zip(payload)
    with zipfile.ZipFile(str(payload)) as archive:
        for relative_path, member_name in validated_entries.items():
            info = archive.getinfo(member_name)
            destination = stage.joinpath(*relative_path.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)


def _stage_module_tree(stage, ctx):
    if ctx.module_zip is not None:
        stage.mkdir()
        _extract_module_zip(ctx.module_zip, stage)
        return (stage / "python37").is_dir()
    (stage / "python").mkdir(parents=True)
    package_source = Path(__file__).resolve().parent
    shutil.copytree(
        str(package_source),
        str(stage / "python" / "dcc_mcp_maya"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    (stage / "plug-ins").mkdir()
    shutil.copy2(_asset_path(Path("maya") / "plugin" / "dcc_mcp_maya_plugin.py"), stage / "plug-ins")
    (stage / "scripts").mkdir()
    shutil.copy2(_asset_path(Path("maya") / "userSetup.py"), stage / "scripts" / "userSetup.py")
    (stage / "module-info.json").write_text(
        json.dumps(
            {
                "name": "dcc_mcp_maya",
                "adapter_version": __version__,
                "min_core_version": MIN_CORE_VERSION,
                "supported_maya_versions": list(range(MIN_MAYA_VERSION, MAX_MAYA_VERSION + 1)),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return False


def _previous_user_setup_payload(ctx, previous_receipt, prior_user_setup):
    baseline = prior_user_setup
    existed = ctx.user_setup_path.is_file()
    if previous_receipt is not None:
        previous = previous_receipt.get("previous_user_setup")
        if not isinstance(previous, dict):
            raise LifecycleError(
                INSTALL_EXIT_INSTALL,
                "receipt",
                "receipt_ownership_invalid",
                "Previous userSetup ownership is missing from the receipt.",
            )
        try:
            previous_baseline = base64.b64decode(str(previous.get("content_base64", "")).encode("ascii"), validate=True)
        except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
            raise LifecycleError(
                INSTALL_EXIT_INSTALL,
                "receipt",
                "receipt_ownership_invalid",
                "Previous userSetup ownership is invalid.",
            ) from exc
        if hashlib.sha256(previous_baseline).hexdigest() != previous.get("sha256"):
            raise LifecycleError(
                INSTALL_EXIT_INSTALL,
                "receipt",
                "receipt_ownership_invalid",
                "Previous userSetup ownership failed its digest check.",
            )
        current = prior_user_setup.decode("utf-8") if prior_user_setup else ""
        unmanaged = _strip_managed_user_setup(current).rstrip("\r\n")
        newline = "\r\n" if "\r\n" in current else "\n"
        current_baseline = (unmanaged + newline).encode("utf-8") if unmanaged else b""
        same_unmanaged_content = current_baseline.replace(b"\r\n", b"\n") == previous_baseline.replace(b"\r\n", b"\n")
        if same_unmanaged_content:
            baseline = previous_baseline
            existed = bool(previous.get("existed"))
        else:
            baseline = current_baseline
            existed = ctx.user_setup_path.is_file() and (bool(previous.get("existed")) or bool(baseline))
    return {
        "existed": existed,
        "content_base64": base64.b64encode(baseline).decode("ascii"),
        "sha256": hashlib.sha256(baseline).hexdigest(),
    }


def _receipt_payload(ctx, module_stage, descriptor_stage, user_setup_stage, previous_receipt, prior_user_setup):
    previous_user_setup = _previous_user_setup_payload(ctx, previous_receipt, prior_user_setup)
    installed_at = time.time()
    source = (
        {"kind": "module_zip", "path": str(ctx.module_zip), "sha256": _sha256(ctx.module_zip)}
        if ctx.module_zip is not None
        else {"kind": "installed_package", "path": str(Path(__file__).resolve().parent)}
    )
    return {
        "receipt_version": 1,
        "schema_version": INSTALL_SOP_SCHEMA_VERSION,
        "dcc_type": DCC_TYPE,
        "adapter_version": __version__,
        "core_version": ctx.core_version,
        "host": {"path": str(ctx.host_path), "version": ctx.host_version},
        "python": {"path": str(ctx.python_path), "version": ctx.python_version},
        "artifacts": [
            {"kind": "tree", "path": str(ctx.module_root), "sha256": _tree_sha256(module_stage)},
            {"kind": "file", "path": str(ctx.descriptor_path), "sha256": _sha256(descriptor_stage)},
            {"kind": "user_setup", "path": str(ctx.user_setup_path), "sha256": _sha256(user_setup_stage)},
        ],
        "previous_user_setup": previous_user_setup,
        "installed_at_epoch": installed_at,
        "installed_at": datetime.fromtimestamp(installed_at, timezone.utc).isoformat(),
        "bootstrap_error_dir": str(ctx.receipt_path.parent / "bootstrap-errors"),
        "source": source,
    }


def _rollback_path(current, backup, existed_before):
    if current.exists():
        _remove_path(current)
    if existed_before and backup.exists():
        _replace_path(backup, current)


def _install_transaction(ctx):
    previous_receipt = _read_receipt(ctx.receipt_path)
    token = uuid.uuid4().hex
    if ctx.module_zip is not None:
        _validate_module_zip(ctx.module_zip)
    for parent in (ctx.modules_dir, ctx.scripts_dir, ctx.receipt_path.parent):
        parent.mkdir(parents=True, exist_ok=True)
    paths = [ctx.module_root, ctx.descriptor_path, ctx.user_setup_path, ctx.receipt_path]
    stages = [path.with_name(".%s.stage-%s" % (path.name, token)) for path in paths]
    backups = [path.with_name(".%s.backup-%s" % (path.name, token)) for path in paths]
    existed = [path.exists() for path in paths]
    prior_user_setup = ctx.user_setup_path.read_bytes() if ctx.user_setup_path.is_file() else b""
    committed = [False, False, False, False]
    try:
        has_python37 = _stage_module_tree(stages[0], ctx)
        descriptor = _render_descriptor(ctx.module_root, has_python37=has_python37)
        (stages[0] / "dcc_mcp_maya.mod").write_text(descriptor, encoding="utf-8")
        stages[1].write_text(descriptor, encoding="utf-8")
        current_user_setup = prior_user_setup.decode("utf-8") if prior_user_setup else ""
        stages[2].write_text(
            _render_user_setup(current_user_setup, ctx.receipt_path.parent / "bootstrap-errors"),
            encoding="utf-8",
        )
        receipt = _receipt_payload(ctx, stages[0], stages[1], stages[2], previous_receipt, prior_user_setup)
        stages[3].write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        inspection = inspect_install_root(ctx.module_root)
        if inspection.get("requires_restart"):
            raise LifecycleError(
                INSTALL_EXIT_REQUIRES_RESTART,
                "install",
                "native_artifact_loaded",
                str(inspection.get("recommended_next_action") or "Maya must restart."),
            )
        for index, (current, stage, backup, had_current) in enumerate(zip(paths, stages, backups, existed)):
            if had_current:
                _replace_path(current, backup)
            _replace_path(stage, current)
            committed[index] = True
    except BaseException:
        try:
            for current, backup, had_current, was_committed in reversed(list(zip(paths, backups, existed, committed))):
                if was_committed or backup.exists():
                    _rollback_path(current, backup, had_current)
        finally:
            for stage in stages:
                if stage.exists():
                    _remove_path(stage)
        raise
    else:
        for backup in backups:
            if backup.exists():
                _remove_path(backup)


def _readiness_next_steps(ctx):
    return [
        {
            "id": "launch_maya",
            "description": "Launch the selected Maya installation and let userSetup finish.",
            "command": [str(ctx.host_path)],
            "why": "The typed host.ping probe requires a running Maya instance.",
        },
        {
            "id": "verify_install",
            "description": "Verify after Maya finishes starting.",
            "command": list(_command_for(ctx, "verify")),
            "why": "Direct usability is not proven until typed readiness succeeds.",
        },
    ]


def _verify(ctx, environ, timeout_secs):
    try:
        receipt = _read_receipt(ctx.receipt_path, required=True)
    except LifecycleError as exc:
        return {"directly_usable": False, "failure_stage": "receipt", "failure_reason": exc.reason}, []
    state, stage, reason = _inspect_state(
        ctx.receipt_path,
        ctx.module_root,
        ctx.descriptor_path,
        ctx.user_setup_path,
    )
    if state not in {"current", "upgrade"}:
        return {"directly_usable": False, "failure_stage": stage, "failure_reason": reason}, []
    assert receipt is not None
    try:
        target = _probe_target(ctx.python_path)
    except LifecycleError as exc:
        return {"directly_usable": False, "failure_stage": "import", "failure_reason": exc.reason}, []
    if target.get("adapter_version") != __version__:
        return {
            "directly_usable": False,
            "failure_stage": "import",
            "failure_reason": "adapter_version_mismatch",
        }, []
    bootstrap_dir = Path(str(receipt.get("bootstrap_error_dir", "")))
    installed_at = float(receipt.get("installed_at_epoch", 0.0))
    if bootstrap_dir.is_dir():
        errors = [
            path
            for path in bootstrap_dir.glob("dcc-mcp-maya.*.host-errors.log")
            if path.stat().st_mtime >= installed_at
        ]
        if errors:
            return {
                "directly_usable": False,
                "failure_stage": "bootstrap",
                "failure_reason": "bootstrap_error_captured",
                "diagnostic_path": str(errors[-1]),
            }, []
    readiness = wait_for_sidecar_ready(
        environ.get("DCC_MCP_REGISTRY_DIR"),
        dcc_type=DCC_TYPE,
        timeout_secs=max(0.0, float(timeout_secs)),
        probe_tool="host.ping",
        probe_timeout_secs=min(3.0, max(0.1, float(timeout_secs))),
    )
    if not readiness.get("success"):
        return {
            "directly_usable": False,
            "failure_stage": "readiness",
            "failure_reason": "sidecar_unavailable",
            "readiness_status": readiness.get("status"),
            "probe_tool": "host.ping",
        }, _readiness_next_steps(ctx)
    return {
        "directly_usable": True,
        "failure_stage": None,
        "failure_reason": None,
        "probe_tool": "host.ping",
        "instance_id": readiness.get("instance_id"),
    }, []


def _execute_install(ctx, environ, timeout_secs, command="install"):
    try:
        _install_transaction(ctx)
    except LifecycleError:
        raise
    except OSError as exc:
        exit_code = INSTALL_EXIT_REQUIRES_RESTART if _is_windows_lock(exc) else INSTALL_EXIT_INSTALL
        reason = "windows_file_lock" if exit_code == INSTALL_EXIT_REQUIRES_RESTART else "commit_failed"
        raise LifecycleError(exit_code, "install", reason, "Install transaction failed: %s" % exc) from exc
    verify, next_steps = _verify(ctx, environ, timeout_secs)
    usable = bool(verify["directly_usable"])
    report = _base_report(ctx, command, "ok" if usable else "partial")
    report["plan_type"] = "upgrade" if command == "upgrade" else ("repair" if ctx.state == "partial" else ctx.state)
    report["steps"] = [
        {"id": "preflight", "status": "ok"},
        {"id": "stage", "status": "ok"},
        {"id": "commit", "status": "ok"},
        {"id": "verify", "status": "ok" if usable else "failed"},
    ]
    report["next_steps"] = next_steps
    report["verify"] = verify
    return report, INSTALL_EXIT_OK if usable else INSTALL_EXIT_VERIFY


def _status(ctx):
    report = _base_report(ctx, "status", "partial" if ctx.state == "partial" else "ok")
    report["steps"] = [
        {"id": "receipt", "status": "present" if ctx.receipt_path.is_file() else "absent"},
        {"id": "module", "status": "present" if ctx.module_root.is_dir() else "absent"},
        {"id": "descriptor", "status": "present" if ctx.descriptor_path.is_file() else "absent"},
        {"id": "user_setup", "status": "present" if ctx.user_setup_path.is_file() else "absent"},
    ]
    if ctx.state == "partial":
        report["verify"] = {
            "directly_usable": False,
            "failure_stage": ctx.state_stage or "state",
            "failure_reason": ctx.state_reason or "partial_install",
        }
    return report, INSTALL_EXIT_PREFLIGHT if ctx.state == "partial" else INSTALL_EXIT_OK


def _receipt_artifacts(receipt, ctx):
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 3 or not all(isinstance(item, dict) for item in artifacts):
        raise LifecycleError(
            INSTALL_EXIT_INSTALL,
            "receipt",
            "receipt_ownership_invalid",
            "Receipt ownership is incomplete; refusing removal.",
        )
    expected = {
        "tree": ctx.module_root.resolve(),
        "file": ctx.descriptor_path.resolve(),
        "user_setup": ctx.user_setup_path.resolve(),
    }
    by_kind = {entry.get("kind"): entry for entry in artifacts}
    if set(by_kind) != set(expected):
        raise LifecycleError(
            INSTALL_EXIT_INSTALL, "receipt", "receipt_ownership_invalid", "Receipt artifacts are invalid."
        )
    for kind, path in expected.items():
        recorded = Path(str(by_kind[kind].get("path", ""))).expanduser().resolve()
        if recorded != path:
            raise LifecycleError(
                INSTALL_EXIT_INSTALL,
                "receipt",
                "receipt_target_mismatch",
                "Receipt target does not match the selected Maya profile.",
            )
    return by_kind


def _execute_uninstall(ctx):
    receipt = _read_receipt(ctx.receipt_path)
    if receipt is None:
        managed_user_setup = False
        if ctx.user_setup_path.is_file():
            try:
                content = ctx.user_setup_path.read_text(encoding="utf-8")
            except OSError:
                content = ""
            managed_user_setup = USER_SETUP_BEGIN in content or USER_SETUP_END in content
        if ctx.module_root.exists() or ctx.descriptor_path.exists() or managed_user_setup:
            raise LifecycleError(
                INSTALL_EXIT_PREFLIGHT,
                "receipt",
                "unreceipted_install",
                "Maya artifacts exist without a receipt; refusing ambiguous removal.",
            )
        report = _base_report(ctx, "uninstall", "ok")
        report["steps"] = [{"id": "uninstall", "status": "already_absent"}]
        return report, INSTALL_EXIT_OK
    artifacts = _receipt_artifacts(receipt, ctx)
    for kind in ("tree", "file"):
        current_digest = _artifact_digest(artifacts[kind])
        if current_digest is not None and current_digest != artifacts[kind].get("sha256"):
            raise LifecycleError(
                INSTALL_EXIT_INSTALL,
                "uninstall",
                "%s_modified" % kind,
                "A receipted Maya artifact was modified; preserving it.",
            )
    current_user_setup = ""
    user_setup_unchanged = False
    if ctx.user_setup_path.is_file():
        current_user_setup = ctx.user_setup_path.read_text(encoding="utf-8")
        if USER_SETUP_BEGIN not in current_user_setup or USER_SETUP_END not in current_user_setup:
            raise LifecycleError(
                INSTALL_EXIT_INSTALL,
                "uninstall",
                "user_setup_marker_missing",
                "The receipted userSetup.py no longer contains the managed block.",
            )
        user_setup_unchanged = _sha256(ctx.user_setup_path) == artifacts["user_setup"].get("sha256")
    inspection = inspect_install_root(ctx.module_root)
    if inspection.get("requires_restart"):
        raise LifecycleError(
            INSTALL_EXIT_REQUIRES_RESTART,
            "uninstall",
            "native_artifact_loaded",
            str(inspection.get("recommended_next_action") or "Maya must restart."),
        )
    previous = receipt.get("previous_user_setup")
    if not isinstance(previous, dict):
        raise LifecycleError(
            INSTALL_EXIT_INSTALL, "receipt", "receipt_ownership_invalid", "Previous userSetup state is missing."
        )
    token = uuid.uuid4().hex
    removal_paths = [ctx.module_root, ctx.descriptor_path, ctx.receipt_path]
    tombstones = [path.with_name(".%s.uninstall-%s" % (path.name, token)) for path in removal_paths]
    user_stage = ctx.user_setup_path.with_name(".%s.stage-%s" % (ctx.user_setup_path.name, token))
    user_backup = ctx.user_setup_path.with_name(".%s.backup-%s" % (ctx.user_setup_path.name, token))
    moved = [False, False, False]
    user_committed = False
    user_existed = ctx.user_setup_path.exists()
    try:
        if previous.get("existed") and user_setup_unchanged:
            restored = base64.b64decode(str(previous.get("content_base64", "")).encode("ascii"))
            if hashlib.sha256(restored).hexdigest() != previous.get("sha256"):
                raise LifecycleError(
                    INSTALL_EXIT_INSTALL,
                    "receipt",
                    "receipt_ownership_invalid",
                    "The receipt's prior userSetup content is invalid.",
                )
            user_stage.write_bytes(restored)
        elif ctx.user_setup_path.is_file():
            remaining = _strip_managed_user_setup(current_user_setup)
            if remaining:
                user_stage.write_text(remaining + "\n", encoding="utf-8")
        for index, (path, tombstone) in enumerate(zip(removal_paths, tombstones)):
            if path.exists():
                _replace_path(path, tombstone)
                moved[index] = True
        if user_existed:
            _replace_path(ctx.user_setup_path, user_backup)
        if user_stage.exists():
            _replace_path(user_stage, ctx.user_setup_path)
        user_committed = True
    except BaseException:
        if user_committed and ctx.user_setup_path.exists():
            _remove_path(ctx.user_setup_path)
        if user_backup.exists():
            _replace_path(user_backup, ctx.user_setup_path)
        for path, tombstone, was_moved in reversed(list(zip(removal_paths, tombstones, moved))):
            if was_moved and tombstone.exists():
                _replace_path(tombstone, path)
        if user_stage.exists():
            _remove_path(user_stage)
        raise
    for tombstone in tombstones:
        if tombstone.exists():
            _remove_path(tombstone)
    if user_backup.exists():
        _remove_path(user_backup)
    report = _base_report(ctx, "uninstall", "ok")
    report["install_state"] = "fresh"
    report["steps"] = [{"id": "receipt", "status": "consumed"}, {"id": "uninstall", "status": "ok"}]
    return report, INSTALL_EXIT_OK


def _failure_report(command, dcc_path, python_path, error):
    retry = [COMMAND, command, "--json", "--dry-run"]
    if dcc_path:
        retry.extend(["--dcc-path", str(dcc_path)])
    if python_path:
        retry.extend(["--python", str(python_path)])
    return {
        "schema_version": INSTALL_SOP_SCHEMA_VERSION,
        "status": "requires_restart" if error.exit_code == INSTALL_EXIT_REQUIRES_RESTART else "failed",
        "dcc_type": DCC_TYPE,
        "command": command,
        "adapter_version": __version__,
        "core_version": str(getattr(dcc_mcp_core, "__version__", "unknown")),
        "steps": [{"id": error.stage, "status": "failed", "message": str(error)}],
        "next_steps": [
            {
                "id": "retry_preflight",
                "description": "Repeat the non-mutating Maya lifecycle preflight.",
                "command": retry,
                "why": str(error),
            }
        ],
        "receipt_path": os.environ.get("DCC_MCP_MAYA_RECEIPT", str(DEFAULT_RECEIPT_PATH)),
        "verify": {"directly_usable": False, "failure_stage": error.stage, "failure_reason": error.reason},
        "host": {"path": dcc_path},
        "python": {"path": python_path},
        "failure_message": str(error),
    }


def _parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=LIFECYCLE_COMMANDS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dcc-path")
    parser.add_argument("--python")
    parser.add_argument("--module-zip", help="Optional immutable released Maya module ZIP payload.")
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        ctx = _resolve_context(args.dcc_path, args.python, os.environ, args.module_zip)
        if args.command == "install":
            if args.dry_run or not args.yes:
                report = _plan(ctx, args.command)
                exit_code = INSTALL_EXIT_OK
            else:
                report, exit_code = _execute_install(ctx, os.environ, args.timeout)
        elif args.command == "upgrade":
            if not ctx.receipt_path.is_file():
                raise LifecycleError(
                    INSTALL_EXIT_PREFLIGHT,
                    "receipt",
                    "receipt_missing",
                    "Upgrade requires an existing Maya install receipt.",
                )
            if args.dry_run or not args.yes:
                report = _plan(ctx, args.command)
                exit_code = INSTALL_EXIT_OK
            else:
                report, exit_code = _execute_install(ctx, os.environ, args.timeout, command="upgrade")
        elif args.command == "status":
            report, exit_code = _status(ctx)
        elif args.command == "verify":
            verify, next_steps = _verify(ctx, os.environ, args.timeout)
            usable = bool(verify["directly_usable"])
            report = _base_report(ctx, args.command, "ok" if usable else "failed")
            report["steps"] = [{"id": "verify", "status": "ok" if usable else "failed"}]
            report["next_steps"] = next_steps
            report["verify"] = verify
            exit_code = INSTALL_EXIT_OK if usable else INSTALL_EXIT_VERIFY
        elif args.command == "uninstall":
            if args.dry_run or not args.yes:
                report = _plan(ctx, args.command)
                exit_code = INSTALL_EXIT_OK
            else:
                report, exit_code = _execute_uninstall(ctx)
        else:
            raise LifecycleError(
                INSTALL_EXIT_PREFLIGHT,
                "command",
                "command_not_implemented",
                "The %s lifecycle path is not implemented." % args.command,
            )
    except LifecycleError as exc:
        report = _failure_report(args.command, args.dcc_path, args.python, exc)
        exit_code = exc.exit_code
    except OSError as exc:
        exit_code = INSTALL_EXIT_REQUIRES_RESTART if _is_windows_lock(exc) else INSTALL_EXIT_INSTALL
        failure = LifecycleError(
            exit_code,
            args.command,
            "windows_file_lock" if exit_code == INSTALL_EXIT_REQUIRES_RESTART else "lifecycle_failed",
            "Lifecycle operation failed: %s" % exc,
        )
        report = _failure_report(args.command, args.dcc_path, args.python, failure)
    except BaseException as exc:
        failure = LifecycleError(
            INSTALL_EXIT_INSTALL,
            args.command,
            "lifecycle_failed",
            "Lifecycle operation failed: %s" % exc,
        )
        report = _failure_report(args.command, args.dcc_path, args.python, failure)
        exit_code = failure.exit_code
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("%s: %s" % (args.command, report["status"]))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "INSTALL_EXIT_ACQUIRE",
    "INSTALL_EXIT_CODES",
    "INSTALL_EXIT_INSTALL",
    "INSTALL_EXIT_OK",
    "INSTALL_EXIT_PREFLIGHT",
    "INSTALL_EXIT_REQUIRES_RESTART",
    "INSTALL_EXIT_VERIFY",
    "INSTALL_SOP_SCHEMA_VERSION",
    "LIFECYCLE_COMMANDS",
    "load_install_sop_schema",
    "main",
]
