# MCP Tools for AI Agents

This guide is for **AI Agent users** (non-developers) who want to use natural language to control Maya via Claude Desktop, Cursor, or any MCP-compatible host.

## How It Works

Once `dcc-mcp-maya` is running inside Maya and your AI host is configured, you can describe tasks in plain English. The AI model translates your request into one or more MCP tool calls.

You don't need to know the action names — just describe what you want.

## Example Conversations

### Creating Objects

> **You:** Create a polygon sphere named "planet" with 40 subdivisions, radius 3, at position (0, 0, 0)

The AI calls `maya_primitives__create_sphere` with the appropriate parameters.

---

> **You:** Make a grid of 5x5 cubes, each 1 unit apart

The AI calls `maya_primitives__create_cube` in a loop (via `maya_expressions__execute_python`).

### Materials and Shading

> **You:** Create a gold metallic material and apply it to all selected objects

The AI calls:
1. `maya_materials__create_material` (aiStandardSurface)
2. `maya_materials__set_material_attribute` (metalness=1, base_color=warm gold)
3. `maya_materials__assign_material` (to selected objects)

---

> **You:** Make the hero_ball object red and shiny

### Animation

> **You:** Animate the "camera1" to orbit around the origin over 120 frames

> **You:** Bake all constraints on the character rig to keyframes

> **You:** Export the animation for "char_root" as an .anim file to C:/exports/

### Scene Management

> **You:** Take a screenshot of the current viewport

The AI calls `maya_render__capture_viewport` and returns the image.

---

> **You:** Save the scene to "C:/projects/hero_shot/v003.ma"

> **You:** What objects are in the scene? List them by type.

### Rigging

> **You:** Bind "hero_mesh" to the skeleton starting from "root_jnt"

> **You:** Copy skin weights from "hero_mesh_v1" to "hero_mesh_v2"

### Rendering

> **You:** Set the render resolution to 1920x1080 and frame range to 1-240

> **You:** Add a Z-depth AOV to the Arnold render settings

## Prompt Tips

### Be Specific About Names

Instead of:
> Move the ball up

Say:
> Move "hero_ball" up by 5 units (translate Y += 5)

### Reference Object Types

> Select all polygon meshes in the scene

> Create an aiStandardSurface material (not Lambert)

### Combine Operations

> Import the file "C:/assets/tree.fbx", rename it "bg_tree_01", place it at (10, 0, 5), and assign the "bark_mat" material to it

The AI decomposes this into 4 sequential tool calls.

### Ask for Information First

> What's in the current scene? Then create a group called "environment" and put all static meshes in it.

## Supported AI Hosts

| Host | Status | Notes |
|------|--------|-------|
| [Claude Desktop](https://claude.ai/download) | ✅ Recommended | Best multi-tool reasoning |
| [Cursor](https://cursor.com) | ✅ | Good for scripting workflows |
| [OpenClaw](https://github.com/loonghao/openclaw) | ✅ | Lightweight CLI host |
| Any OpenAI-compatible host | ⚠️ | Must support MCP Streamable HTTP |

## Limitations

- Actions run on **Maya's main thread** — very long operations may briefly pause the UI
- `capture_viewport` returns a **base64-encoded PNG** — not all hosts render images inline
- MEL/Python execution (`execute_mel`, `execute_python`) gives the AI full Maya access — use in trusted environments only
- Undo is available in Maya but not tracked by the MCP server
