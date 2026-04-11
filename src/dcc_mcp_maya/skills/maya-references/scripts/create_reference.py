"""Reference an external Maya file into the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_reference(
    file_path: str,
    namespace: Optional[str] = None,
    group_reference: bool = False,
) -> dict:
    """Reference an external Maya file into the current scene.

    Args:
        file_path: Absolute path to the Maya file to reference (.ma, .mb).
        namespace: Namespace string to use.  When omitted Maya derives one from
            the filename.  Use ``":"`` for the root namespace (not recommended).
        group_reference: If True, place the referenced nodes inside a new
            transform group node.  Default: False.

    Returns:
        ActionResultModel dict with ``context.reference_node``,
        ``context.namespace``, and ``context.file_path``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not file_path or not file_path.strip():
            return skill_error("Invalid file path", "file_path must not be empty")

        kwargs = {
            "reference": True,
            "groupReference": group_reference,
            "mergeNamespacesOnClash": False,
            "returnNewNodes": False,
        }
        if namespace is not None:
            kwargs["namespace"] = namespace
        else:
            kwargs["defaultNamespace"] = False

        # cmds.file returns the reference node name
        ref_node = cmds.file(file_path, **kwargs)

        # Resolve actual namespace used
        try:
            resolved_ns = cmds.referenceQuery(ref_node, namespace=True, shortName=True)
        except Exception:
            resolved_ns = namespace or ""

        return skill_success(
            "Referenced '{}' as '{}'".format(file_path, resolved_ns),
            reference_node=ref_node,
            namespace=resolved_ns,
            file_path=file_path,
            prompt="Use list_references to verify or reload_reference if the file changes.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to reference file '{}'".format(file_path))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_reference`."""
    return create_reference(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
