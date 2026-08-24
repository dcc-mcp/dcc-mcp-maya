"""Request bounded Maya file-node reloads with disk and native readback evidence."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._texture_paths import texture_disk_evidence

_MAX_TEXTURE_NODES = 64


def reload_textures(texture_nodes) -> dict:
    """Reissue paths for explicit file nodes and return bounded disk evidence."""

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if (
            not isinstance(texture_nodes, list)
            or not 1 <= len(texture_nodes) <= _MAX_TEXTURE_NODES
            or any(not isinstance(node, str) or not node or len(node) > 512 for node in texture_nodes)
            or len(set(texture_nodes)) != len(texture_nodes)
        ):
            return skill_error(
                "Invalid texture nodes",
                "texture_nodes must contain 1 through {} unique Maya node names".format(_MAX_TEXTURE_NODES),
            )

        textures = []
        for node in texture_nodes:
            if not cmds.objExists(node) or str(cmds.nodeType(node)) != "file":
                return skill_error(
                    "Texture node was not found",
                    "Every texture_nodes entry must resolve to a Maya file node.",
                    node=node,
                )
            path_value = cmds.getAttr("{}.fileTextureName".format(node))
            tiling_value = cmds.getAttr("{}.uvTilingMode".format(node))
            if tiling_value not in {0, 3}:
                return skill_error(
                    "Unsupported texture tiling mode",
                    "Only ordinary and UDIM file nodes can be reloaded by this typed tool.",
                    node=node,
                    uv_tiling_mode=tiling_value,
                )
            udim_mode = "udim" if tiling_value == 3 else "off"
            try:
                path, disk_evidence = texture_disk_evidence(path_value, udim_mode)
            except ValueError as exc:
                return skill_error(
                    "Texture source is unavailable",
                    str(exc),
                    node=node,
                    texture_path=path_value,
                )
            textures.append(
                {
                    "node": node,
                    "texture_path": str(path),
                    "udim_mode": udim_mode,
                    "tile_count": disk_evidence["tile_count"],
                    "bytes": disk_evidence["bytes"],
                    "mtime_ns": disk_evidence["mtime_ns"],
                }
            )

        for texture in textures:
            node = texture["node"]
            path = texture["texture_path"]
            cmds.setAttr("{}.fileTextureName".format(node), path, type="string")
            cmds.dgdirty(node)
            if str(cmds.getAttr("{}.fileTextureName".format(node))) != path:
                return skill_error(
                    "Texture reload did not round-trip",
                    "Native Maya fileTextureName readback changed after the reload request.",
                    node=node,
                    requested_path=path,
                )

        return skill_success(
            "Reload requested for {} texture node(s)".format(len(textures)),
            textures=textures,
            reloaded_count=len(textures),
            verified=True,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to reload textures")


@skill_entry
def main(**kwargs) -> dict:
    return reload_textures(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
