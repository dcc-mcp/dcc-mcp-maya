---
name: maya-audio
description: Maya audio node control — import, list, configure and remove sound nodes
dcc: maya
tags: [audio, sound, timeline, animation]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-audio

Maya audio skill. Provides actions for managing audio/sound nodes attached to
Maya's timeline for animation playback sync.

## Scripts

- `import_audio` — Import an audio file and create a sound node
- `list_audio_nodes` — List all sound nodes in the scene
- `set_audio_offset` — Set the frame offset for a sound node
- `set_active_audio` — Set a sound node as the active timeline audio
- `delete_audio_node` — Delete a sound node from the scene
