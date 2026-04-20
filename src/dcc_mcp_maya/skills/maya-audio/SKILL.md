---
name: maya-audio
description: Maya audio — import audio files, set timeline audio, list and remove audio nodes
dcc: maya
version: 1.0.0
tags:
- maya
- audio
- sound
- timeline
search-hint: audio, sound, import audio, timeline audio, sound node
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: import_audio
- name: list_audio
  read_only_hint: true
  idempotent_hint: true
- name: remove_audio
  destructive_hint: true
  idempotent_hint: true
- name: set_timeline_audio
  idempotent_hint: true
---
# maya-audio

Maya audio skill. Provides actions for importing audio files into Maya, attaching
them to the timeline, and managing sound nodes.

## Scripts

- `import_audio` — Import an audio file and create a sound node
- `list_audio` — List all sound nodes in the scene
- `set_timeline_audio` — Set the active timeline audio node
- `remove_audio` — Delete a sound node from the scene
