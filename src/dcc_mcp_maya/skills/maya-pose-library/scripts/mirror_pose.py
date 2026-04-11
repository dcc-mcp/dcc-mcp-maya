"""Mirror pose by swapping left/right control attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_NEGATE_ATTRS = {"tx", "ry", "rz"}


# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success  # noqa: E402


def mirror_pose(
    file_path: str,
    output_path: Optional[str] = None,
    left_prefix: str = "L_",
    right_prefix: str = "R_",
) -> dict:
    """Mirror pose by swapping left/right control values.

    Reads a pose JSON, swaps values between controls prefixed with
    ``left_prefix`` and ``right_prefix``, and negates translation X, rotation
    Y, and rotation Z to account for symmetry across the YZ plane.

    Args:
        file_path: Path to the source ``.json`` pose file.
        output_path: Destination ``.json`` path for the mirrored pose.
            If None, the mirrored pose is applied directly to the scene
            via ``maya.cmds.setAttr``.
        left_prefix: Prefix identifying left-side controls.  Default: ``L_``.
        right_prefix: Prefix identifying right-side controls.
            Default: ``R_``.

    Returns:
        ActionResultModel dict with ``context.mirrored_pairs`` and
        ``context.output_path``.
    """

    try:
        if not os.path.isfile(file_path):
            return skill_error(
                "Pose file not found: {}".format(file_path),
                "'{}'  does not exist on disk".format(file_path),
            )

        with open(file_path, "r") as fh:
            pose_data = json.load(fh)

        mirrored_data = {}  # type: dict

        processed_pairs = []

        for node, attrs in pose_data.items():
            if node.startswith(left_prefix):
                counterpart = right_prefix + node[len(left_prefix) :]
            elif node.startswith(right_prefix):
                counterpart = left_prefix + node[len(right_prefix) :]
            else:
                mirrored_data[node] = attrs
                continue

            mirror_attrs = {}
            for attr, value in attrs.items():
                if attr in _NEGATE_ATTRS and isinstance(value, (int, float)):
                    mirror_attrs[attr] = -value
                else:
                    mirror_attrs[attr] = value

            counterpart_orig = pose_data.get(counterpart, {})
            mirrored_data[node] = {
                k: (
                    counterpart_orig.get(k, v)
                    if k not in _NEGATE_ATTRS
                    else -counterpart_orig.get(k, v)
                    if isinstance(counterpart_orig.get(k, v), (int, float))
                    else v
                )
                for k, v in attrs.items()
            }
            mirrored_data[counterpart] = mirror_attrs
            processed_pairs.append([node, counterpart])

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w") as fh:
                json.dump(mirrored_data, fh, indent=2)
            msg = "Mirrored pose saved to '{}'".format(output_path)
        else:
            import maya.cmds as cmds  # noqa: PLC0415

            for node, attrs in mirrored_data.items():
                if not cmds.objExists(node):
                    continue
                for attr, value in attrs.items():
                    full = "{}.{}".format(node, attr)
                    try:
                        if cmds.attributeQuery(attr, node=node, exists=True):
                            if not cmds.getAttr(full, lock=True):
                                cmds.setAttr(full, value)
                    except Exception as exc:
                        logger.warning("Could not set %s: %s", full, exc)
            msg = "Mirrored pose applied to scene"

        return skill_success(
            "{} ({} pair(s) swapped)".format(msg, len(processed_pairs)),
            prompt="Use save_pose to persist the mirrored pose for reuse.",
            mirrored_pairs=processed_pairs,
            output_path=output_path,
            control_count=len(mirrored_data),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to mirror pose from '{}'".format(file_path))


@skill_entry
def main(**kwargs):
    return mirror_pose(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
