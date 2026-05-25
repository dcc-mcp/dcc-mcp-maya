"""Detect optional Maya rigging frameworks without importing their runtime APIs."""

from __future__ import annotations

import importlib.util
import os
from typing import Any, Dict, Iterable, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_FRAMEWORKS: Dict[str, Dict[str, Any]] = {
    "mgear": {
        "label": "mGear",
        "kind": "procedural_rig",
        "python_modules": ["mgear", "mgear.shifter"],
        "notes": "Use for guide-driven procedural character rigs when the package is installed.",
    },
    "advanced_skeleton": {
        "label": "AdvancedSkeleton",
        "kind": "procedural_rig",
        "mel_commands": ["AdvancedSkeleton", "AdvancedSkeleton5"],
        "notes": "Use for template-based character setup when the script package is loaded.",
    },
    "mgtools": {
        "label": "MGTools",
        "kind": "animation_rig_tools",
        "env_vars": ["MAYA_MGTOOLS_ROOT"],
        "mel_commands": ["MGToolsAutoLoader"],
        "notes": "Use for animator-facing rig controls and animation utilities.",
    },
    "go_skinning": {
        "label": "Go Skinning",
        "kind": "skinning",
        "python_modules": ["maya_go_skinning", "go_skinning"],
        "notes": "Use for assisted skin binding or skin-weight generation when available.",
    },
    "skin_magic": {
        "label": "Skin Magic",
        "kind": "skinning",
        "notes": "Use for specialized skin-weight processing when the tool is installed.",
    },
    "si_weight_editor": {
        "label": "SI Weight Editor",
        "kind": "skinning",
        "python_modules": ["siweighteditor"],
        "notes": "Use for detailed skin-weight editing workflows when available.",
    },
    "metahuman": {
        "label": "MetaHuman for Maya",
        "kind": "character_pipeline",
        "python_modules": ["dna_viewer", "metahuman"],
        "notes": "Use for DNA or MetaHuman-style character pipeline tasks when available.",
    },
}


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:  # noqa: BLE001
        return False


def _mel_command_available(mel: Any, command: str) -> bool:
    if mel is None:
        return False
    try:
        result = mel.eval('whatIs "{}"'.format(command))
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(result, str):
        return False
    lowered = result.lower()
    return bool(result and "unknown" not in lowered and "not found" not in lowered)


def _env_available(env_vars: Iterable[str]) -> List[str]:
    return [name for name in env_vars if os.environ.get(name)]


def _framework_record(key: str, spec: Dict[str, Any], mel: Any) -> Dict[str, Any]:
    modules = [name for name in spec.get("python_modules", []) if _module_available(name)]
    env_vars = _env_available(spec.get("env_vars", []))
    mel_commands = [name for name in spec.get("mel_commands", []) if _mel_command_available(mel, name)]
    signals = {
        "python_modules": modules,
        "env_vars": env_vars,
        "mel_commands": mel_commands,
    }
    available = any(signals.values())
    return {
        "name": key,
        "label": spec["label"],
        "kind": spec["kind"],
        "available": available,
        "signals": signals,
        "notes": spec.get("notes", ""),
    }


def detect_rig_frameworks(
    frameworks: Optional[List[str]] = None,
    include_unavailable: bool = False,
) -> dict:
    """Detect optional rigging frameworks and return capability-oriented records."""
    try:
        try:
            import maya.mel as mel  # noqa: PLC0415
        except ImportError:
            mel = None

        requested = frameworks or list(_FRAMEWORKS.keys())
        unknown = [name for name in requested if name not in _FRAMEWORKS]
        if unknown:
            return maya_error(
                "Unknown rig framework",
                "Unknown framework(s): {}".format(", ".join(unknown)),
                known_frameworks=sorted(_FRAMEWORKS),
            )

        records = []
        for name in requested:
            record = _framework_record(name, _FRAMEWORKS[name], mel)
            if include_unavailable or record["available"]:
                records.append(record)

        return maya_success(
            "Detected {} available rig framework(s)".format(sum(1 for item in records if item["available"])),
            frameworks=records,
            known_frameworks=sorted(_FRAMEWORKS),
            prompt="Use built-in rigging tools first; use optional frameworks only when a record reports available=true.",
        )
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to detect rig frameworks")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`detect_rig_frameworks`."""
    return detect_rig_frameworks(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
