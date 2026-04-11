# Scene API Reference

Scene inspection and management tools from the `maya-scene` skill.

## `maya_scene__get_session_info`

Return high-level Maya session information.

### Return Value

```typescript
{
  maya_version: string      // e.g. "2024.1"
  scene_path: string        // current file path, or "" if unsaved
  fps: number               // playback frame rate
  start_frame: number       // animation start frame
  end_frame: number         // animation end frame
  object_count: number      // total DAG node count
  selection_count: number   // currently selected objects
}
```

---

## `maya_scene__get_scene_info`

Return a hierarchical DAG description of the scene.

### Return Value

```typescript
{
  name: string
  children: Array<{
    name: string
    type: string        // Maya node type
    children: Array<...>
  }>
}
```

---

## `maya_scene__list_objects`

List objects in the scene with optional type filtering.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `type_filter` | str | `""` | Maya node type (e.g. `"mesh"`, `"camera"`, `"joint"`) |
| `long_names` | bool | `false` | Return full DAG paths |

### Return Value

```json
{
  "objects": ["pSphere1", "pCube1"],
  "count": 2,
  "type_filter": "mesh"
}
```

---

## `maya_scene__get_bounding_box`

Query the world-space bounding box of an object.

### Parameters

| Name | Type | Description |
|------|------|-------------|
| `object_name` | str | Maya object name |

### Return Value

```json
{
  "object": "pSphere1",
  "min": [-1.0, -1.0, -1.0],
  "max": [1.0, 1.0, 1.0],
  "center": [0.0, 0.0, 0.0],
  "size": [2.0, 2.0, 2.0]
}
```

---

## `maya_scene__get_selection`

Return the current selection.

### Return Value

```json
{
  "selection": ["pSphere1", "pCube2"],
  "count": 2
}
```

---

## `maya_scene__set_selection`

Set the active selection.

### Parameters

| Name | Type | Description |
|------|------|-------------|
| `objects` | list[str] | Object names to select |

---

## `maya_scene__group_objects`

Group objects under a new group node.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `objects` | list[str] | — | Objects to group |
| `group_name` | str | `"group1"` | Name for the new group |
| `world` | bool | `false` | Create the group at world level |

### Return Value

```json
{ "success": true, "group": "group1" }
```

---

## `maya_scene__set_visibility`

Show or hide an object.

### Parameters

| Name | Type | Description |
|------|------|-------------|
| `object_name` | str | Target object |
| `visible` | bool | `true` to show, `false` to hide |

---

## `maya_scene__freeze_transforms`

Freeze the transforms of an object (reset to identity while preserving visual position).

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `object_name` | str | — | Target object |
| `translate` | bool | `true` | Freeze translation |
| `rotate` | bool | `true` | Freeze rotation |
| `scale` | bool | `true` | Freeze scale |

---

## `maya_scene__duplicate_object`

Duplicate an object.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `object_name` | str | — | Object to duplicate |
| `new_name` | str | `null` | Name for the duplicate |
| `upstream_nodes` | bool | `false` | Duplicate upstream nodes |

### Return Value

```json
{ "success": true, "duplicate": "pSphere2" }
```

---

## `maya_scene__export_scene`

Export the entire scene to a file.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `file_path` | str | — | Output file path |
| `file_type` | str | `"mayaAscii"` | `"mayaAscii"`, `"mayaBinary"`, `"fbx"`, `"obj"` |
| `selection_only` | bool | `false` | Export only selected objects |
