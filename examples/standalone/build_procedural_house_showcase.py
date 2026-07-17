"""Build and save the Bifrost house showcase from mayapy.

Usage:
    mayapy examples/standalone/build_procedural_house_showcase.py --output house-showcase.ma --seed 20260718
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import maya.standalone


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Destination .ma scene path")
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--frames", type=int, default=72)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    maya.standalone.initialize(name="python")
    try:
        import maya.cmds as cmds

        from dcc_mcp_maya.bifrost import ensure_bifrost_plugins
        from dcc_mcp_maya.procedural_house_showcase import build_house_showcase, design_house_showcase

        runtime = ensure_bifrost_plugins(cmds)
        spec = design_house_showcase(seed=args.seed, frame_count=args.frames)
        showcase = build_house_showcase(cmds, spec)
        cmds.file(rename=str(output))
        cmds.file(save=True, type="mayaAscii", force=True)
        print(
            json.dumps(
                {
                    "scene": str(output),
                    "runtime": runtime,
                    "root": showcase["root"],
                    "camera": showcase["camera"],
                    "house_count": showcase["house_count"],
                    "frame_range": showcase["frame_range"],
                },
                indent=2,
            )
        )
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
