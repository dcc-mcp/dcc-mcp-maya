# Snapshot API

Viewport capture via the `maya-render` skill.

## Tool: `maya_render__playblast`

Capture the active (or specified) Maya viewport as a base64-encoded PNG.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `width` | int | `960` | Output image width in pixels |
| `height` | int | `540` | Output image height in pixels |
| `camera` | str | _(active viewport camera)_ | Camera name, e.g. `"persp"`, `"front"`, `"top"` |
| `display_mode` | str | `"smoothShaded"` | Viewport display mode |

**display_mode values:**

| Value | Description |
|-------|-------------|
| `smoothShaded` | Smooth shaded with textures |
| `flatShaded` | Flat-shaded polygons |
| `wireframe` | Wireframe only |
| `boundingBox` | Bounding box display |

### Return Value

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "width": 960,
  "height": 540,
  "camera": "persp",
  "format": "png",
  "encoding": "base64"
}
```

### Decode the Image

```python
import base64

image_b64 = result["image"]
image_bytes = base64.b64decode(image_b64)

with open("snapshot.png", "wb") as f:
    f.write(image_bytes)
```

### Direct Script Usage

```python
# In Maya Script Editor (Python)
import importlib
import sys

# The script is importable from the skill's scripts directory
from dcc_mcp_maya.skills.maya_render.scripts import playblast

result = playblast.main(
    width=1920,
    height=1080,
    camera="persp",
    display_mode="smoothShaded",
)
print(f"Captured {result['width']}x{result['height']} image")
```

## Tool: `maya_render__get_render_settings`

Query the current render settings — useful for AI agents to understand the render pipeline state before issuing capture commands.

### Return Value

```json
{
  "renderer": "arnold",
  "width": 1920,
  "height": 1080,
  "start_frame": 1,
  "end_frame": 120,
  "image_format": "exr",
  "output_path": "/renders/my_scene"
}
```
