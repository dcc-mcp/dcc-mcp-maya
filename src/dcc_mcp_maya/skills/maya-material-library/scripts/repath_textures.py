"""Transactionally repath bounded Maya file nodes between explicit roots."""

from __future__ import annotations

from pathlib import Path

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._texture_paths import MAX_TEXTURE_PATH_LENGTH, resolve_texture_path

_MAX_TEXTURE_NODES = 64


def _validated_root(value: str, label: str):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXTURE_PATH_LENGTH:
        raise ValueError("{} must be a non-empty bounded directory path".format(label))
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("{} is not an existing directory".format(label))
    return path


def repath_textures(texture_nodes, old_root: str, new_root: str) -> dict:
    """Move explicit file-node paths between roots while preserving relative paths."""

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
        try:
            source_root = _validated_root(old_root, "old_root")
            destination_root = _validated_root(new_root, "new_root")
        except ValueError as exc:
            return skill_error("Invalid texture roots", str(exc))

        changes = []
        for node in texture_nodes:
            if not cmds.objExists(node) or str(cmds.nodeType(node)) != "file":
                return skill_error(
                    "Texture node was not found",
                    "Every texture_nodes entry must resolve to a Maya file node.",
                    node=node,
                )
            previous_value = cmds.getAttr("{}.fileTextureName".format(node))
            tiling_value = cmds.getAttr("{}.uvTilingMode".format(node))
            if tiling_value not in {0, 3}:
                return skill_error(
                    "Unsupported texture tiling mode",
                    "Only ordinary and UDIM file nodes can be repathed by this typed tool.",
                    node=node,
                    uv_tiling_mode=tiling_value,
                )
            previous_path = Path(str(previous_value)).expanduser().resolve()
            try:
                relative = previous_path.relative_to(source_root)
            except ValueError:
                return skill_error(
                    "Texture path is outside old_root",
                    "Every selected texture must be contained by old_root before any path is changed.",
                    node=node,
                    texture_path=str(previous_path),
                    old_root=str(source_root),
                )
            texture_path = (destination_root / relative).resolve()
            try:
                texture_path.relative_to(destination_root)
            except ValueError:
                return skill_error(
                    "Repathed texture escaped new_root",
                    "The preserved relative path must stay inside new_root.",
                    node=node,
                )
            udim_mode = "udim" if tiling_value == 3 else "off"
            try:
                verified_path, tile_count = resolve_texture_path(str(texture_path), udim_mode)
            except ValueError as exc:
                return skill_error(
                    "Repathed texture is unavailable",
                    str(exc),
                    node=node,
                    texture_path=str(texture_path),
                )
            changes.append(
                {
                    "node": node,
                    "previous_path": str(previous_path),
                    "texture_path": str(verified_path),
                    "udim_mode": udim_mode,
                    "tile_count": tile_count,
                }
            )

        written = []
        try:
            for change in changes:
                attr = "{}.fileTextureName".format(change["node"])
                cmds.setAttr(attr, change["texture_path"], type="string")
                written.append(change)
                cmds.dgdirty(change["node"])
                if str(cmds.getAttr(attr)) != change["texture_path"]:
                    raise RuntimeError("{} did not return the requested path".format(change["node"]))
        except Exception as exc:
            rollback_errors = []
            for change in reversed(written):
                attr = "{}.fileTextureName".format(change["node"])
                try:
                    cmds.setAttr(attr, change["previous_path"], type="string")
                    cmds.dgdirty(change["node"])
                    if str(cmds.getAttr(attr)) != change["previous_path"]:
                        rollback_errors.append(change["node"])
                except Exception:
                    rollback_errors.append(change["node"])
            return skill_error(
                "Texture repath failed",
                str(exc),
                rollback_succeeded=not rollback_errors,
                rollback_errors=rollback_errors,
            )

        return skill_success(
            "Repathed {} texture node(s)".format(len(changes)),
            old_root=str(source_root),
            new_root=str(destination_root),
            changes=changes,
            changed_count=len(changes),
            verified=True,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to repath textures")


@skill_entry
def main(**kwargs) -> dict:
    return repath_textures(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
