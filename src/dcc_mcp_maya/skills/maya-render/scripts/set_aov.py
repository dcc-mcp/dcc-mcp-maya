"""Manage bounded Arnold AOV state with native post-condition readback."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_AOV_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_DATA_TYPES = frozenset({"rgba", "rgb", "float", "int", "bool", "vector", "point", "point2"})
_MAX_AOVS = 64


def _ensure_mtoa(cmds) -> bool:
    try:
        if not cmds.pluginInfo("mtoa", q=True, loaded=True):
            cmds.loadPlugin("mtoa", quiet=True)
        return bool(cmds.pluginInfo("mtoa", q=True, loaded=True))
    except Exception:
        return False


def _read_aovs(cmds, interface, type_names: Optional[Dict[object, str]] = None) -> List[Dict[str, object]]:
    pairs = list(interface.getAOVNodes(names=True) or [])
    if len(pairs) > _MAX_AOVS:
        raise ValueError("Arnold scene has more than {} active AOVs".format(_MAX_AOVS))

    result = []
    seen = set()
    for raw_name, raw_node in pairs:
        name = str(raw_name)
        node = str(raw_node)
        if name in seen:
            raise ValueError("Arnold returned duplicate AOV name: {}".format(name))
        seen.add(name)
        raw_data_type = cmds.getAttr("{}.type".format(node))
        data_type = (type_names or {}).get(raw_data_type)
        if data_type is None and isinstance(raw_data_type, str):
            data_type = raw_data_type.lower()
        if data_type not in _DATA_TYPES:
            raise ValueError("Arnold returned unsupported AOV type for {}: {}".format(name, raw_data_type))
        enabled = cmds.getAttr("{}.enabled".format(node))
        result.append(
            {
                "name": name,
                "node": node,
                "data_type": data_type,
                "enabled": bool(enabled),
            }
        )
    return sorted(result, key=lambda item: item["name"])


def set_aov(action: str, name: Optional[str] = None, data_type: str = "rgba") -> dict:
    """Add one Arnold AOV and return the exact active native AOV list."""

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if action not in {"add", "list", "remove"}:
            return skill_error("Unsupported AOV action", "action must be 'add', 'list', or 'remove'")
        if action != "list" and (not isinstance(name, str) or not _AOV_NAME_RE.fullmatch(name)):
            return skill_error(
                "Invalid AOV name",
                "name must start with a letter and contain at most 64 ASCII letters, digits, or underscores",
            )
        if data_type not in _DATA_TYPES:
            return skill_error(
                "Unsupported AOV data type",
                "data_type must be one of: {}".format(", ".join(sorted(_DATA_TYPES))),
            )
        if not _ensure_mtoa(cmds):
            return skill_error("Arnold is unavailable", "The mtoa plug-in could not be loaded")

        from mtoa import aovs as mtoa_aovs  # noqa: PLC0415

        interface = mtoa_aovs.AOVInterface()
        type_names = {code: str(type_name).lower() for type_name, code in getattr(mtoa_aovs, "TYPES", ())}
        before = _read_aovs(cmds, interface, type_names)
        if action == "list":
            return skill_success(
                "Read {} active Arnold AOV(s)".format(len(before)),
                action=action,
                changed=False,
                aovs=before,
                count=len(before),
            )
        if action == "remove":
            matches = [item for item in before if item["name"] == name]
            if len(matches) != 1:
                return skill_error(
                    "AOV was not found",
                    "Removal requires exactly one active AOV with the requested name.",
                    name=name,
                    aovs=before,
                )
            interface.removeAOV(name)
            after = _read_aovs(cmds, interface, type_names)
            if any(item["name"] == name for item in after):
                return skill_error(
                    "Arnold AOV removal did not round-trip",
                    "Native AOV readback still contains the requested AOV.",
                    name=name,
                    aovs=after,
                )
            return skill_success(
                "Removed Arnold AOV '{}'".format(name),
                action=action,
                changed=True,
                removed=matches[0],
                aovs=after,
                count=len(after),
            )
        if any(item["name"] == name for item in before):
            return skill_error(
                "AOV already exists",
                "Remove the existing AOV before adding it with different settings.",
                name=name,
                aovs=before,
            )
        if len(before) >= _MAX_AOVS:
            return skill_error(
                "AOV limit reached",
                "Remove an AOV before adding another one.",
                max_aovs=_MAX_AOVS,
                aovs=before,
            )

        def _rollback_added_aov() -> bool:
            try:
                interface.removeAOV(name)
                rollback_state = _read_aovs(cmds, interface, type_names)
                return not any(item["name"] == name for item in rollback_state)
            except Exception:
                return False

        interface.addAOV(name, aovType=data_type)
        try:
            after = _read_aovs(cmds, interface, type_names)
        except Exception:
            if not _rollback_added_aov():
                raise RuntimeError("Arnold AOV add failed and rollback could not be verified")
            raise
        matches = [item for item in after if item["name"] == name]
        if len(matches) != 1:
            rolled_back = _rollback_added_aov()
            return skill_error(
                "Arnold AOV add did not round-trip",
                "Native AOV readback did not contain exactly one requested AOV.",
                name=name,
                rollback_succeeded=rolled_back,
                aovs=after,
            )
        if matches[0]["data_type"] != data_type or not matches[0]["enabled"]:
            rolled_back = _rollback_added_aov()
            return skill_error(
                "Arnold AOV state did not match the request",
                "Native AOV readback reported a different type or disabled state.",
                name=name,
                requested_data_type=data_type,
                actual=matches[0],
                rollback_succeeded=rolled_back,
                aovs=after,
            )

        return skill_success(
            "Added Arnold AOV '{}'".format(name),
            action=action,
            changed=True,
            aov=matches[0],
            aovs=after,
            count=len(after),
        )
    except ImportError:
        return skill_error("Arnold is unavailable", "Maya or the mtoa AOV API could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to manage Arnold AOVs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point for bounded Arnold AOV management."""

    return set_aov(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
