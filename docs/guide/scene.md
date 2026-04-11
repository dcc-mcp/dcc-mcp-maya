# Scene Information

Query Maya scene state — hierarchy, session info, object properties.

## Session Info

Get a high-level overview of the current Maya session:

**Tool:** `maya_scene__get_session_info`

```json
{
  "maya_version": "2024.1",
  "scene_path": "/path/to/my_scene.ma",
  "fps": 24.0,
  "start_frame": 1,
  "end_frame": 120,
  "object_count": 42,
  "selection_count": 0
}
```

Natural language: `"What version of Maya am I running? How many objects are in the scene?"`

## Scene Hierarchy

Get the full DAG hierarchy as a nested structure:

**Tool:** `maya_scene__get_scene_info`

```json
{
  "name": "root",
  "children": [
    {
      "name": "pSphere1",
      "type": "transform",
      "children": [
        { "name": "pSphereShape1", "type": "mesh" }
      ]
    },
    {
      "name": "directionalLight1",
      "type": "transform",
      "children": [
        { "name": "directionalLightShape1", "type": "directionalLight" }
      ]
    }
  ]
}
```

## List Objects

Filter objects by type:

**Tool:** `maya_scene__list_objects`

| Parameter | Type | Description |
|-----------|------|-------------|
| `type_filter` | str | Maya node type (e.g. `"mesh"`, `"camera"`, `"joint"`) |
| `long_names` | bool | Return full DAG paths |

```
"List all mesh objects in the scene"
"Show me all cameras"
"List all joints in the rig"
```

## Selection

### Get Selection

**Tool:** `maya_scene__get_selection`

```json
{
  "selection": ["pSphere1", "pCube1"],
  "count": 2
}
```

### Set Selection

**Tool:** `maya_scene__set_selection`

| Parameter | Type | Description |
|-----------|------|-------------|
| `objects` | list[str] | List of object names to select |

```
"Select pSphere1 and pCube1"
"Select all mesh objects"  ← uses select_by_type first
```

## Bounding Box

Query the world-space bounding box of any object:

**Tool:** `maya_scene__get_bounding_box`

```json
{
  "object": "pSphere1",
  "min": [-1.0, -1.0, -1.0],
  "max": [1.0, 1.0, 1.0],
  "center": [0.0, 0.0, 0.0],
  "size": [2.0, 2.0, 2.0]
}
```

## Transform Queries

Get and set translate/rotate/scale via `maya-primitives`:

**Tool:** `maya_primitives__get_transform`

```json
{
  "object": "pSphere1",
  "translate": [0.0, 1.0, 0.0],
  "rotate": [0.0, 0.0, 0.0],
  "scale": [1.0, 1.0, 1.0]
}
```

## Practical Queries

```
"What objects are in my scene?"
"Where is pSphere1 located?"
"What is the bounding box of my character mesh?"
"Is the scene saved? What's the current file path?"
"How many polygons are in the scene?"
```
