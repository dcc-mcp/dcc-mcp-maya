"""Lock and/or hide specified attributes on a Maya node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_ATTRS = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"]


def lock_hide_attributes(
    node: str,
    attributes: Optional[List[str]] = None,
    lock: bool = True,
    hide: bool = True,
) -> dict:
    """Lock and/or hide specified attributes on a Maya node.

    Args:
        node: Name of the Maya node (typically a control transform).
        attributes: List of attribute names to process.  Defaults to all
            standard transform + visibility channels
            (``tx``, ``ty``, ``tz``, ``rx``, ``ry``, ``rz``,
            ``sx``, ``sy``, ``sz``, ``v``).
        lock: Whether to lock the attributes.  Default: True.
        hide: Whether to hide the attributes from the channel box.
            Default: True.

    Returns:
        ActionResultModel dict with ``context.processed_attributes``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return maya_error(
                "Node not found: {}".format(node),
                "'{}' does not exist in the scene".format(node),
            )

        attrs = attributes if attributes is not None else _DEFAULT_ATTRS
        processed = []

        for attr in attrs:
            full = "{}.{}".format(node, attr)
            if not cmds.attributeQuery(attr, node=node, exists=True):
                logger.warning("Attribute does not exist, skipping: %s", full)
                continue
            if lock:
                cmds.setAttr(full, lock=True)
            if hide:
                cmds.setAttr(full, keyable=False, channelBox=False)
            processed.append(attr)

        return maya_success(
            "{} attribute(s) on '{}' (lock={}, hide={})".format(
                "Locked/hidden" if lock and hide else ("Locked" if lock else "Hidden"),
                node,
                lock,
                hide,
            ),
            prompt="Use connect_attributes if you need to drive these attrs via connections.",
            node=node,
            processed_attributes=processed,
            lock=lock,
            hide=hide,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to lock/hide attributes on '{}'".format(node))


def main(**kwargs):
    return lock_hide_attributes(**kwargs)


if __name__ == "__main__":
    import json

    result = lock_hide_attributes("ctrl_root", attributes=["sx", "sy", "sz", "v"])
    print(json.dumps(result))
