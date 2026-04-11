# MCP Tools Guide

This guide is for users who want to control Maya using natural language through an AI assistant (Claude, Cursor, etc.). No Python knowledge required.

## How It Works

Once the `dcc-mcp-maya` server is running inside Maya, your AI assistant gains access to **60+ Maya tools**. Just describe what you want in plain English.

## Scene Operations

### Create and Manage Scenes

```
"Create a new empty scene"
"Save the current scene to /projects/my_scene.ma"
"Open the file /projects/character.mb"
"What's the current frame rate? Change it to 30fps"
```

### Browse the Scene

```
"List all objects in the scene"
"Show me the scene hierarchy"
"How many objects are in the scene?"
"Select all mesh objects"
"What is selected right now?"
```

## Creating Objects

### Basic Geometry

```
"Create a sphere"
"Create a cube with width 2 and name it 'table'"
"Make a ground plane, scale it to 10x10"
"Create a cylinder at position (3, 0, 0)"
```

### Transforms

```
"Move pSphere1 to position (0, 5, 0)"
"Rotate the cube 45 degrees on the Y axis"
"Scale pPlane1 to 5 on X and Z"
"Freeze the transforms on all selected objects"
"Center the pivot on my_mesh"
```

### Object Management

```
"Rename pSphere1 to 'ball'"
"Duplicate the cube and move it 3 units to the right"
"Delete pCone1"
"Group sphere1, cube1, and cylinder1 into a group called 'objects'"
"Parent sphere1 under group1"
"Hide the camera_rig group"
"Lock the transform of ground_plane"
```

## Materials and Shading

```
"Create a red Lambert material called 'redMat'"
"Make a shiny gold material"
"Assign redMat to pSphere1"
"Create a transparent material and assign it to the glass object"
"List all materials in the scene"
"Change the color of material1 to blue"
```

## Animation

```
"Set a keyframe on pSphere1 at frame 1"
"Set the translate Y of ball to 0 at frame 1, then 5 at frame 24, then 0 at frame 48"
"Set the timeline from frame 1 to 120"
"Go to frame 50"
"What frame am I on?"
"Bake the simulation on pCloth1 from frame 1 to 100"
"Delete all keyframes on pSphere1 between frames 20 and 40"
"Export animation curves from character_ctrl to /exports/walk_cycle.anim"
```

## Lighting

```
"Add a directional light pointing down"
"Create a point light at position (5, 10, 5) with intensity 2"
"Make the directional light warmer (orange-ish)"
"List all lights in the scene"
"Turn off shadows on light1"
```

## Cameras

```
"Create a camera at position (10, 5, 10) looking at the origin"
"Set the focal length of camera1 to 85mm"
"Switch the viewport to the render camera"
"List all cameras in the scene"
```

## Render and Capture

```
"Take a screenshot of the current view"
"Capture the scene from the front camera"
"Set the render resolution to 1920x1080"
"Set the renderer to Arnold"
"What are the current render settings?"
```

## Advanced Workflows

### Full Asset Creation

```
"Create a table: a flat cube for the top (scale 4x0.2x2) at height 2,
 and 4 cylinder legs (scale 0.1x1x0.1) at each corner.
 Apply a brown wood material to everything."
```

### Animation Setup

```
"I need a bouncing ball animation:
 - Create a sphere called 'ball' at (0,0,0)
 - Set keyframes: Y=0 at frame 1, Y=5 at frame 12, Y=0 at frame 24
 - Set the timeline to 1-48
 - Take a screenshot of the result"
```

### Scene Inspection

```
"Give me a full report on the current scene:
 - How many objects are there?
 - What materials are used?
 - What are the render settings?
 - Show me a screenshot"
```

## Tips

1. **Be specific about object names** — use the exact name Maya shows (e.g. `pSphere1`, not just `sphere`)
2. **Chain operations** — you can describe multi-step workflows in one message
3. **Ask for confirmation** — "show me a screenshot" after operations to verify results
4. **Use natural units** — "1 unit" = 1 Maya unit (typically 1 cm or 1 m depending on your scene scale)
