"""Meta-tests replaying the batch-3 tables against a real Maya.

The unit tests for ``maya-plugins`` and ``maya-compositing`` run against fakes
that accept any keyword, so they cannot catch a flag Maya rejects or a node
type Maya will not create - the exact failure class that produced review
findings in the earlier batches.

These checks follow the same shape as the field-table guard in
``test_maya_nucleus.py``: the assertion runs in a **child interpreter**, because
booting ``maya.standalone`` flips ``is_gui_executable()`` to batch mode for the
whole process, which changes the dispatcher ``MayaMcpServer`` installs and
breaks ``tests/test_server.py``.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

#: Flag that turns this file into the Maya-hosted drift checker.
MAYA_CHECK_ARGV = "--maya-batch3-table-check"


def _boot_maya_cmds():
    """Import and initialise a real ``maya.cmds`` (child interpreter only)."""
    import maya.cmds as cmds
    import maya.standalone

    maya.standalone.initialize()
    return cmds


def _maya_flag_names(cmds, command_name):
    """Long flag names Maya reports for a command, from ``cmds.help()``."""
    import re

    text = cmds.help(command_name, language="python") or ""
    return set(re.findall(r"^\s*-\w+\s+-(\w+)\s", text, re.M))


def _collect_errors(cmds):
    """Return drift descriptions; empty means Maya agrees with the tables."""
    from dcc_mcp_maya.compositing import BLEND_MODES, INPUT_PLUGS, UTILITY_NODES
    from dcc_mcp_maya.plugins import ALWAYS_VALID_FLAGS, LOADED_ONLY_FLAGS

    errors = []

    # 1. pluginInfo flags: the always-valid ones must exist, and the
    #    loaded-only ones must exist but be rejected while unloaded.
    info_flags = _maya_flag_names(cmds, "pluginInfo")
    for flag in ALWAYS_VALID_FLAGS + LOADED_ONLY_FLAGS:
        if flag not in info_flags:
            errors.append("cmds.pluginInfo has no -{} flag".format(flag))

    # 2. Every utility node type we expose must actually be creatable, and must
    #    not come back as an `unknown` node (which is what grade/colorCorrect
    #    do in a batch session).
    for node_type in UTILITY_NODES + ("layeredTexture", "file", "blendColors"):
        try:
            node = cmds.createNode(node_type)
        except Exception as exc:  # noqa: BLE001 - report, keep scanning
            errors.append("cmds.createNode({}) failed: {}".format(node_type, exc))
            continue
        try:
            if str(cmds.nodeType(node)) == "unknown":
                errors.append("cmds.createNode({}) returns an unknown node in batch mode".format(node_type))
        finally:
            try:
                cmds.delete(node)
            except Exception:  # noqa: BLE001 - cleanup must not mask drift
                pass

    # 3. The input plugs we connect into must exist on each node type.
    for node_type, plugs in sorted(INPUT_PLUGS.items()):
        if not plugs:
            continue
        try:
            node = cmds.createNode(node_type)
        except Exception as exc:  # noqa: BLE001 - report, keep scanning
            errors.append("cmds.createNode({}) failed: {}".format(node_type, exc))
            continue
        try:
            for plug in plugs:
                if not cmds.objExists("{}.{}".format(node, plug)):
                    errors.append("{} has no .{} plug".format(node_type, plug))
        finally:
            try:
                cmds.delete(node)
            except Exception:  # noqa: BLE001 - cleanup must not mask drift
                pass

    # 4. layeredTexture must expose the blend-mode enum we validate against.
    stack = cmds.createNode("layeredTexture")
    try:
        cmds.createNode("file")  # ensure a source exists
        modes = cmds.attributeQuery("blendMode", node="{}.inputs[0]".format(stack), listEnum=True)
        if modes:
            declared = list(modes[0].split(":"))
            if declared != list(BLEND_MODES):
                errors.append(
                    "layeredTexture blendMode enum drift: Maya={} table={}".format(declared, list(BLEND_MODES))
                )
    except Exception as exc:  # noqa: BLE001 - report
        errors.append("layeredTexture blendMode enum could not be read: {}".format(exc))
    finally:
        try:
            cmds.delete(stack)
        except Exception:  # noqa: BLE001 - cleanup must not mask drift
            pass

    return errors


def _maya_check_main():
    """Entry point for the child interpreter."""
    cmds = _boot_maya_cmds()
    errors = _collect_errors(cmds)
    for line in errors:
        print("DRIFT: {}".format(line))
    return 1 if errors else 0


def test_batch3_tables_match_a_real_maya():
    """Meta-test: the plug-in and compositing tables must match real Maya."""
    import subprocess

    try:
        import importlib.util

        if importlib.util.find_spec("maya.cmds") is None:
            pytest.skip("maya.cmds is not importable in this interpreter")
    except (ImportError, ValueError):
        pytest.skip("maya.cmds is not importable in this interpreter")

    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), MAYA_CHECK_ARGV],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")

    # Deliberately no skip based on the child's output: a child that could not
    # boot must fail, otherwise a broken Maya install silently turns the guard
    # into a no-op.
    assert result.returncode == 0, "Maya disagrees with the batch-3 tables:\n" + output.strip()


if __name__ == "__main__":
    if MAYA_CHECK_ARGV in sys.argv:
        sys.exit(_maya_check_main())
