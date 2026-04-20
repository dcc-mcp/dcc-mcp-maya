---
name: maya-rigging
description: Maya rigging — joints, IK, skin clusters, deformers, blend shapes and constraints
dcc: maya
version: 1.0.0
tags:
- maya
- rigging
- skeleton
- deformer
- animation
search-hint: rig, joint, bind, skin, IK, FK, control
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: assign_deformer
  idempotent_hint: true
- name: blend_shape_add_target
- name: create_blend_shape
- name: create_curve
- name: create_ik_handle
- name: create_joint
- name: mirror_joints
- name: set_driven_key
  idempotent_hint: true
- name: set_ik_fk_blend
  idempotent_hint: true
- name: set_joint_limit
  idempotent_hint: true
- name: set_joint_orient
  idempotent_hint: true
- name: skin_cluster_bind
groups:
- name: rigging
  description: Rigging, deformation, and skinning tools
  default_active: false
  tools:
  - assign_deformer
  - blend_shape_add_target
  - create_blend_shape
  - create_curve
  - create_ik_handle
  - create_joint
  - mirror_joints
  - set_driven_key
  - set_ik_fk_blend
  - set_joint_limit
  - set_joint_orient
  - skin_cluster_bind
---
