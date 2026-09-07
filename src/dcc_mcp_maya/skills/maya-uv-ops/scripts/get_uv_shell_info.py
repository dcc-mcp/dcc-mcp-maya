"""Get UV shell information for a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def get_uv_shell_info(object_name: str, uv_set: Optional[str] = None) -> dict:
    """Get UV shell information for a polygon mesh.

    Reports the number of UV shells and the bounding box of each shell in
    UV space (u_min, v_min, u_max, v_max).

    Args:
        object_name: Transform or mesh shape name.
        uv_set: UV set to query.  If None, uses the current active UV set.

    Returns:
        ToolResult dict with ``context.shell_count``,
        ``context.shells`` (list of dicts with ``u_min``, ``v_min``,
        ``u_max``, ``v_max``, ``uv_count``).
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        # Resolve UV set
        if uv_set:
            existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
            if uv_set not in existing:
                return skill_error(
                    "UV set '{}' not found on '{}'".format(uv_set, object_name),
                    "Available UV sets: {}".format(existing),
                )
        active_set = uv_set or cmds.polyUVSet(object_name, query=True, currentUVSet=True)
        if isinstance(active_set, list):
            active_set = active_set[0] if active_set else None
        if not active_set:
            return skill_success(
                "Mesh has no active UV set", object_name=object_name, uv_set=None, shell_count=0, shells=[]
            )

        # The commands layer treats uvSetName as a boolean when polyEditUV
        # is queried. OpenMaya reads a named set without changing the active
        # set and preserves UV-index correspondence across both arrays.
        from maya.api import OpenMaya as om

        selection = om.MSelectionList()
        selection.add(object_name)
        dag_path = selection.getDagPath(0)
        if dag_path.node().hasFn(om.MFn.kTransform):
            dag_path.extendToShape()
        mesh = om.MFnMesh(dag_path)
        _shell_count, shell_ids = mesh.getUvShellsIds(active_set)
        u_vals, v_vals = mesh.getUVs(active_set)

        # Build shell groups: shell_id -> list of UV component indices
        shell_map = {}
        for i, sid in enumerate(shell_ids):
            shell_map.setdefault(int(sid), []).append(i)

        if len(u_vals) != len(shell_ids) or len(v_vals) != len(shell_ids):
            return skill_error(
                "Inconsistent UV readback",
                "UV coordinates and shell ids have different lengths",
                object_name=object_name,
                uv_set=active_set,
                u_count=len(u_vals),
                v_count=len(v_vals),
                shell_id_count=len(shell_ids),
            )

        shells = []
        for sid in sorted(shell_map.keys()):
            indices = shell_map[sid]
            us = [u_vals[i] for i in indices if i < len(u_vals)]
            vs = [v_vals[i] for i in indices if i < len(v_vals)]
            if us and vs:
                shells.append(
                    {
                        "shell_id": sid,
                        "uv_count": len(indices),
                        "u_min": min(us),
                        "u_max": max(us),
                        "v_min": min(vs),
                        "v_max": max(vs),
                    }
                )
            else:
                shells.append({"shell_id": sid, "uv_count": len(indices)})

        return skill_success(
            "UV shell info for '{}' (UV set: {})".format(object_name, active_set),
            object_name=object_name,
            uv_set=active_set,
            shell_count=len(shells),
            shells=shells,
            prompt="Check the result with list_uv_ops or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get UV shell info")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_uv_shell_info`."""
    return get_uv_shell_info(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
