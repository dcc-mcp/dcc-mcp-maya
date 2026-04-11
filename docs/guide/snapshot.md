# Viewport Snapshot

Capture Maya viewport images for AI visual feedback, review workflows, or automation pipelines.

## MCP Tool

The `maya_render__playblast` tool captures the active viewport as a **base64-encoded PNG**.

```python
# Called by an MCP host internally — no Python code needed
# Just ask your AI: "Take a screenshot of the current viewport"
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | int | `960` | Image width in pixels |
| `height` | int | `540` | Image height in pixels |
| `camera` | str | _(active)_ | Camera to render from (e.g. `"persp"`, `"top"`) |
| `display_mode` | str | `"smoothShaded"` | Display mode: `smoothShaded`, `wireframe`, `flatShaded` |

## Usage Examples

### Via MCP Host (Natural Language)

> **"Take a screenshot of the scene"**
>
> **"Capture the front view at 1920×1080"**
>
> **"Show me what the scene looks like from the persp camera"**

### Direct Python (Maya Script Editor)

```python
import dcc_mcp_maya
handle = dcc_mcp_maya.start_server()

# The capture happens via MCP tool call — AI agent calls it automatically
# To test manually from Python:
from dcc_mcp_maya.skills.maya_render.scripts import playblast

result = playblast.main(width=1280, height=720, camera="persp")
print(result["image"])   # base64-encoded PNG string
```

## Return Value

The tool returns a JSON object:

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgA...",
  "width": 960,
  "height": 540,
  "camera": "persp",
  "format": "png",
  "encoding": "base64"
}
```

## Playblast vs Full Render

| Feature | `maya_render__playblast` | `maya_render__set_render_settings` + render |
|---------|--------------------------|---------------------------------------------|
| Speed | Instant (viewport grab) | Slow (full render) |
| Quality | Hardware viewport | Production quality |
| Requires Arnold/etc. | No | Depends on renderer |
| Use case | AI feedback, previews | Final output |

## Multi-Viewport Capture

To capture a specific panel, set the active camera first:

```
"Set the active viewport camera to 'front', then take a screenshot"
```

This will call:
1. `maya_cameras__set_active_camera` with `camera="front"`
2. `maya_render__playblast`

## Practical AI Workflow

```
You: "Create a red sphere, place it at (0, 1, 0), then show me what it looks like"

Claude:
  1. calls maya_primitives__create_sphere
  2. calls maya_primitives__set_transform (translate to 0,1,0)
  3. calls maya_materials__create_material (red Lambert)
  4. calls maya_materials__assign_material
  5. calls maya_render__playblast
  → shows you the resulting image
```
