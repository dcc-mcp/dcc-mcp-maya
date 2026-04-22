---
name: maya-audio
description: Maya audio management — import audio files, set timeline audio, list and remove sound nodes. Use when synchronizing audio to animation timelines. Not for animation keyframing or video editing — use maya-animation or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - audio
    - sound
    - timeline
    search-hint: sync audio, timeline sound, import audio, sound node
    depends: []
    tools: tools.yaml
---
# maya-audio

Maya audio skill. Provides actions for importing audio files into Maya, attaching
them to the timeline, and managing sound nodes.

## Scripts

- `import_audio` — Import an audio file and create a sound node
- `list_audio` — List all sound nodes in the scene
- `set_timeline_audio` — Set the active timeline audio node
- `remove_audio` — Delete a sound node from the scene
