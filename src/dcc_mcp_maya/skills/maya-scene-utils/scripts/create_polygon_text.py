"""Create a 3D polygon text object in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_polygon_text(
    text: str,
    name: Optional[str] = None,
    font: str = "Arial",
    depth: float = 0.5,
    extrude: bool = True,
) -> dict:
    """Create a 3D polygon text object in the scene.

    Uses ``cmds.textCurves`` to generate text curves and then extrudes them
    with ``cmds.extrude`` to produce a solid polygon mesh.

    Args:
        text: The text string to create.
        name: Optional name for the resulting group/transform node.
        font: Font name recognised by Maya (e.g. ``"Arial"``, ``"Courier"``).
            Default: ``"Arial"``.
        depth: Extrusion depth for the 3D effect.  Default: 0.5.
        extrude: If True, extrude text curves into a 3D polygon mesh.
            If False, the raw NURBS text curves are returned.

    Returns:
        ActionResultModel dict with ``context.objects`` (list of created
        transform names) and ``context.text``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not text:
            return skill_error("Empty text", "text parameter must not be empty")

        kwargs = {"font": font, "text": text}
        if name:
            kwargs["name"] = name

        # Create text curves
        curves = cmds.textCurves(**kwargs) or []

        objects = list(curves)

        if extrude and curves:
            # Extrude each NURBS curve sub-component to polygon
            extruded = []
            for crv in curves:
                try:
                    ex = cmds.extrude(crv, extrudeType=0, length=depth, constructionHistory=False)
                    extruded.extend(ex or [])
                except Exception:
                    extruded.append(crv)
            objects = extruded

        return skill_success(
            "Created polygon text: '{}'".format(text),
            text=text,
            font=font,
            depth=depth if extrude else None,
            extruded=extrude,
            objects=objects,
            count=len(objects),
            prompt="Check the result with list_scene_utils or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create polygon text '{}'".format(text))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_polygon_text`."""
    return create_polygon_text(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
