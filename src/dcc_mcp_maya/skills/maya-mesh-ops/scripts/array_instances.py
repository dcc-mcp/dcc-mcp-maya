"""Create a bounded linear array of Maya DAG instances."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._mutation import MayaUndoChunk, node_uuid, shape_uuids, uuid_inventory

_MAX_INSTANCES = 128
_TOLERANCE = 1e-5


def _vector3(value, name):
    # type: (...) -> tuple
    if not isinstance(value, list) or len(value) != 3:
        return None, skill_error("Invalid array vector", "{} must contain exactly three numbers".format(name))
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        return None, skill_error("Invalid array vector", "{} values must be numeric".format(name))
    return [float(item) for item in value], None


def _matches(actual, expected):
    # type: (...) -> bool
    return bool(
        isinstance(actual, (list, tuple))
        and len(actual) == 3
        and all(abs(float(actual[index]) - expected[index]) <= _TOLERANCE for index in range(3))
    )


def array_instances(
    object_name,  # type: str
    count,  # type: int
    translate_step=None,  # type: Optional[List[float]]
    rotate_step=None,  # type: Optional[List[float]]
    name_prefix=None,  # type: Optional[str]
):
    # type: (...) -> dict
    """Create ``count - 1`` instances plus the existing source object."""
    if not isinstance(object_name, str) or not object_name:
        return skill_error("Invalid array source", "object_name must be a non-empty string")
    if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= _MAX_INSTANCES:
        return skill_error(
            "Invalid array count",
            "count must be an integer from 2 through {}".format(_MAX_INSTANCES),
            count=count,
        )
    translate, error = _vector3(translate_step or [0.0, 0.0, 0.0], "translate_step")
    if error:
        return error
    rotate, error = _vector3(rotate_step or [0.0, 0.0, 0.0], "rotate_step")
    if error:
        return error
    if name_prefix is not None and (not isinstance(name_prefix, str) or not name_prefix):
        return skill_error("Invalid array name", "name_prefix must be a non-empty string when provided")

    transaction = None
    before_uuids = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Array source not found", "'{}' does not exist".format(object_name))

        before_uuids = uuid_inventory(cmds)
        source_uuid = node_uuid(cmds, object_name)
        source_shape_uuids = shape_uuids(cmds, object_name)
        if not source_shape_uuids:
            return skill_error(
                "Array source has no instanceable shape",
                "object_name must resolve to a transform with at least one non-intermediate shape",
            )

        source_translation = [
            float(value) for value in cmds.xform(object_name, query=True, objectSpace=True, translation=True)
        ]
        source_rotation = [
            float(value) for value in cmds.xform(object_name, query=True, objectSpace=True, rotation=True)
        ]
        objects = [object_name]
        object_uuids = [source_uuid]
        prefix = name_prefix or "{}_instance".format(object_name.rsplit("|", 1)[-1])
        transaction = MayaUndoChunk(cmds, "dcc_mcp_array_instances")
        transaction.begin()

        for index in range(1, count):
            result = cmds.instance(object_name, name="{}_{:02d}".format(prefix, index))
            if not result:
                receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
                return skill_error(
                    "Array instance creation failed",
                    "maya.cmds.instance returned no node",
                    failed_index=index,
                    **receipt,
                )
            instance_name = str(result[0])
            instance_uuid = node_uuid(cmds, instance_name)
            instance_shape_uuids = shape_uuids(cmds, instance_name)
            if (
                instance_uuid in before_uuids
                or instance_uuid in object_uuids
                or instance_shape_uuids != source_shape_uuids
            ):
                receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
                return skill_error(
                    "Array instance provenance verification failed",
                    "Each result must be a new unique transform sharing the source shape UUID",
                    failed_index=index,
                    object_name=instance_name,
                    **receipt,
                )
            expected_translation = [source_translation[axis] + translate[axis] * index for axis in range(3)]
            expected_rotation = [source_rotation[axis] + rotate[axis] * index for axis in range(3)]
            cmds.xform(instance_name, objectSpace=True, translation=expected_translation)
            cmds.xform(instance_name, objectSpace=True, rotation=expected_rotation)

            actual_translation = cmds.xform(instance_name, query=True, objectSpace=True, translation=True)
            actual_rotation = cmds.xform(instance_name, query=True, objectSpace=True, rotation=True)
            if (
                not cmds.objExists(instance_name)
                or not _matches(actual_translation, expected_translation)
                or not _matches(actual_rotation, expected_rotation)
            ):
                receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
                return skill_error(
                    "Array instance verification failed",
                    "Instance {} did not preserve the requested transform".format(index),
                    failed_index=index,
                    object_name=instance_name,
                    **receipt,
                )
            objects.append(instance_name)
            object_uuids.append(instance_uuid)

        transaction.commit()
        return skill_success(
            "Created and verified {}-object instance array".format(count),
            source=object_name,
            source_uuid=source_uuid,
            objects=objects,
            object_uuids=object_uuids,
            verified_count=len(objects),
            translate_step=translate,
            rotate_step=rotate,
            prompt="Use set_pivot or mirror_mesh to continue the modeling workflow.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        receipt = {}
        if transaction is not None and before_uuids is not None:
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
        return skill_exception(exc, message="Failed to create Maya instance array", **receipt)


@skill_entry
def main(**kwargs):
    # type: (...) -> dict
    """Entry point; delegates to :func:`array_instances`."""
    return array_instances(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
