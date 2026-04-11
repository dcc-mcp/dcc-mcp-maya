# Action API Reference

Technical reference for all built-in actions. Each action is a Python module with a `main()` function.

## Naming Convention

```
{skill_name.replace("-", "_")}__{script_stem}
```

| Skill Package | MCP Tool Prefix |
|---------------|-----------------|
| `maya-scene` | `maya_scene__` |
| `maya-primitives` | `maya_primitives__` |
| `maya-animation` | `maya_animation__` |
| `maya-cameras` | `maya_cameras__` |
| `maya-lighting` | `maya_lighting__` |
| `maya-render` | `maya_render__` |
| `maya-materials` | `maya_materials__` |
| `maya-mesh-ops` | `maya_mesh_ops__` |
| `maya-uv-ops` | `maya_uv_ops__` |
| `maya-rigging` | `maya_rigging__` |

## Scene Actions

### `maya_scene__new_scene`

Create a new empty Maya scene.

**Parameters:** none

**Returns:**

```json
{ "success": true }
```

---

### `maya_scene__save_scene`

Save the current scene.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `file_path` | str | _(current)_ | Save path; if omitted, saves to current file |
| `file_type` | str | `"mayaAscii"` | `"mayaAscii"` or `"mayaBinary"` |

**Returns:**

```json
{ "success": true, "path": "/path/to/scene.ma" }
```

---

### `maya_scene__open_scene`

Open a Maya scene file.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `file_path` | str | Path to `.ma` or `.mb` file |

---

### `maya_scene__list_objects`

List scene objects.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `type_filter` | str | `""` | Maya node type filter (e.g. `"mesh"`, `"joint"`) |
| `long_names` | bool | `false` | Return full DAG paths |

**Returns:**

```json
{ "objects": ["pSphere1", "pCube1"], "count": 2 }
```

---

### `maya_scene__get_session_info`

Get Maya session information.

**Returns:**

```json
{
  "maya_version": "2024.1",
  "scene_path": "/path/scene.ma",
  "fps": 24.0,
  "start_frame": 1,
  "end_frame": 120,
  "object_count": 42
}
```

---

### `maya_scene__get_bounding_box`

Query the world-space bounding box of an object.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `object_name` | str | Maya object name |

**Returns:**

```json
{
  "min": [-1.0, -1.0, -1.0],
  "max": [1.0, 1.0, 1.0],
  "center": [0.0, 0.0, 0.0],
  "size": [2.0, 2.0, 2.0]
}
```

## Primitive Actions

### `maya_primitives__create_sphere`

Create a polygon sphere.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | str | `"pSphere1"` | Node name |
| `radius` | float | `1.0` | Sphere radius |
| `subdiv_x` | int | `20` | Subdivisions along X |
| `subdiv_y` | int | `20` | Subdivisions along Y |

**Returns:**

```json
{ "success": true, "name": "pSphere1", "shape": "pSphereShape1" }
```

---

### `maya_primitives__set_transform`

Set translate/rotate/scale on an object.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `object_name` | str | — | Target object |
| `translate` | list[float] | `null` | `[tx, ty, tz]` |
| `rotate` | list[float] | `null` | `[rx, ry, rz]` in degrees |
| `scale` | list[float] | `null` | `[sx, sy, sz]` |

## Animation Actions

### `maya_animation__set_keyframe`

Set a keyframe on an object at a given time.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `object_name` | str | — | Target object |
| `time` | float | — | Frame number |
| `attribute` | str | `null` | Attribute name (e.g. `"translateY"`); all if omitted |
| `value` | float | `null` | Value to set; current value if omitted |

---

### `maya_animation__bake_simulation`

Bake simulation or constraints to keyframes.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `objects` | list[str] | — | Objects to bake |
| `start_frame` | float | — | Bake start frame |
| `end_frame` | float | — | Bake end frame |
| `step` | float | `1.0` | Sample every N frames |
| `simulation` | bool | `true` | Include simulation evaluation |

## Render Actions

### `maya_render__playblast`

Capture the active viewport as a base64-encoded PNG.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `width` | int | `960` | Image width |
| `height` | int | `540` | Image height |
| `camera` | str | _(active)_ | Camera name |
| `display_mode` | str | `"smoothShaded"` | Display mode |

**Returns:**

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgA...",
  "width": 960,
  "height": 540,
  "format": "png",
  "encoding": "base64"
}
```

---

### `maya_render__set_render_settings`

Configure render settings.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `width` | int | `null` | Render width |
| `height` | int | `null` | Render height |
| `start_frame` | float | `null` | Start frame |
| `end_frame` | float | `null` | End frame |
| `renderer` | str | `null` | `"arnold"`, `"vray"`, `"redshift"`, `"mayaHardware2"` |
| `image_format` | str | `null` | `"png"`, `"exr"`, `"jpg"` |

## Lighting Actions

### `maya_lighting__create_light`

Create a Maya light.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `light_type` | str | `"directionalLight"` | `directionalLight`, `pointLight`, `spotLight`, `areaLight`, `ambientLight` |
| `name` | str | `null` | Node name |
| `intensity` | float | `1.0` | Light intensity |
| `color` | list[float] | `[1, 1, 1]` | RGB color (0–1) |
| `position` | list[float] | `[0, 0, 0]` | World position |
| `rotation` | list[float] | `[0, 0, 0]` | World rotation in degrees |
