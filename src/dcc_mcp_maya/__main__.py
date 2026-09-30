"""Run an owning-thread Maya MCP service with ``mayapy -m dcc_mcp_maya``."""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Optional, Sequence


def _port(value: str) -> int:
    number = int(value)
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return number


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Initialize standalone Maya and serve until interrupted."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=_port, default=None)
    parser.add_argument("--gateway-port", type=_port, default=None)
    parser.add_argument("--registry-dir")
    parser.add_argument("--skill-path", action="append", default=[])
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    import maya.standalone  # noqa: PLC0415

    from dcc_mcp_maya.__version__ import __version__  # noqa: PLC0415
    from dcc_mcp_maya.headless import serve_headless  # noqa: PLC0415

    def announce(server):
        record = {
            "dcc_type": "maya",
            "host_pid": os.getpid(),
            "instance_type": "standalone",
            "adapter_version": __version__,
            "mcp_url": server.mcp_url,
        }
        print(json.dumps(record) if args.as_json else "Maya MCP server started: " + server.mcp_url, flush=True)

    maya.standalone.initialize(name="python")
    try:
        serve_headless(
            port=args.port,
            gateway_port=args.gateway_port,
            registry_dir=args.registry_dir,
            extra_skill_paths=args.skill_path,
            on_started=announce,
        )
    except KeyboardInterrupt:
        pass
    finally:
        maya.standalone.uninitialize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
