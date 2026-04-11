# Action 完整列表

`dcc-mcp-maya` 内置 **200+ Action**，组织为 39 个技能包。每个 Action 都成为 AI Agent 可直接调用的 MCP 工具。

## 命名规则

Action 命名格式：`{技能名_下划线}__{脚本名}`

示例：
- `maya_scene__new_scene`
- `maya_primitives__create_sphere`
- `maya_animation__set_keyframe`

## 技能包列表

### maya-scene（21 个）

场景生命周期、对象管理、层级和基本查询。

| Action | 说明 |
|--------|------|
| `maya_scene__new_scene` | 创建新的空 Maya 场景 |
| `maya_scene__open_scene` | 打开 Maya 场景文件 |
| `maya_scene__save_scene` | 保存当前场景 |
| `maya_scene__export_scene` | 导出场景为 FBX/OBJ/Alembic/Maya 格式 |
| `maya_scene__list_objects` | 列出 DAG 对象（可按类型过滤）|
| `maya_scene__get_selection` | 获取当前选择 |
| `maya_scene__set_selection` | 设置活动选择 |
| `maya_scene__select_by_type` | 按 Maya 节点类型选择所有对象 |
| `maya_scene__get_session_info` | Maya 版本、场景路径、FPS、对象数量 |
| `maya_scene__get_scene_info` | 场景的 DAG 层级描述 |
| `maya_scene__group_objects` | 将对象组合到新组节点下 |
| `maya_scene__parent_object` | 设置或清除对象的父级 |
| `maya_scene__duplicate_object` | 复制对象 |
| `maya_scene__freeze_transforms` | 冻结对象的变换 |
| `maya_scene__center_pivot` | 将轴心点居中到边界框 |
| `maya_scene__get_bounding_box` | 查询世界空间边界框 |
| `maya_scene__set_visibility` | 显示或隐藏对象 |
| `maya_scene__lock_object` | 锁定/解锁变换属性 |
| `maya_scene__set_frame_rate` | 更改场景播放帧率 |
| `maya_scene__list_cameras` | 列出场景中所有摄影机 |
| `maya_scene__create_locator` | 创建 Maya 定位器节点 |

### maya-primitives（8 个）

多边形基本体创建与变换管理。

| Action | 说明 |
|--------|------|
| `maya_primitives__create_sphere` | 创建多边形球体 |
| `maya_primitives__create_cube` | 创建多边形立方体 |
| `maya_primitives__create_cylinder` | 创建多边形圆柱体 |
| `maya_primitives__create_plane` | 创建多边形平面 |
| `maya_primitives__delete_objects` | 从场景中删除对象 |
| `maya_primitives__set_transform` | 设置平移/旋转/缩放 |
| `maya_primitives__get_transform` | 获取平移/旋转/缩放 |
| `maya_primitives__rename_object` | 重命名对象 |

### maya-animation（13 个）

关键帧、时间轴、曲线、模拟烘焙和动画 I/O。

| Action | 说明 |
|--------|------|
| `maya_animation__set_keyframe` | 在指定时间设置属性关键帧 |
| `maya_animation__get_keyframes` | 获取对象/属性的所有关键帧时间 |
| `maya_animation__delete_keyframes` | 删除指定帧范围内的关键帧 |
| `maya_animation__set_timeline` | 设置播放和动画时间轴范围 |
| `maya_animation__get_current_time` | 获取当前帧号 |
| `maya_animation__set_current_time` | 设置当前帧号 |
| `maya_animation__query_scene_time_info` | 查询场景时间和播放设置 |
| `maya_animation__bake_simulation` | 将模拟/约束烘焙为关键帧 |
| `maya_animation__bake_constraints` | 将约束驱动的动画烘焙为关键帧 |
| `maya_animation__list_animation_curves` | 列出驱动对象的 animCurve 节点 |
| `maya_animation__set_animation_curve_tangent` | 设置关键帧切线类型 |
| `maya_animation__export_animation_curves` | 导出动画曲线到 `.anim` 文件 |
| `maya_animation__import_animation_curves` | 从文件导入动画曲线 |

### maya-materials（8 个）

着色器创建、指定和属性编辑。

| Action | 说明 |
|--------|------|
| `maya_materials__create_material` | 创建 Lambert/Blinn/Phong/aiStandardSurface 材质 |
| `maya_materials__assign_material` | 将材质指定给对象 |
| `maya_materials__set_material_attribute` | 设置颜色、粗糙度、金属度等 |
| `maya_materials__list_materials` | 列出所有场景材质 |
| `maya_materials__list_shading_groups` | 列出所有着色组 |
| `maya_materials__get_material_connections` | 获取材质上的纹理/节点连接 |
| `maya_materials__get_shader_assignment` | 获取对象上指定的材质 |
| `maya_materials__reset_to_default_material` | 将对象重置为默认 Lambert 材质 |

### maya-rigging（12 个）

骨骼、IK、混合形状、蒙皮绑定。

| Action | 说明 |
|--------|------|
| `maya_rigging__create_joint` | 创建关节 |
| `maya_rigging__skin_cluster_bind` | 将网格平滑绑定到骨骼 |
| `maya_rigging__create_blend_shape` | 创建混合形状变形器 |
| `maya_rigging__blend_shape_add_target` | 向已有混合形状添加目标 |
| `maya_rigging__assign_deformer` | 为网格指定变形器 |
| `maya_rigging__create_ik_handle` | 创建 IK 手柄 |
| `maya_rigging__set_ik_fk_blend` | 设置 IK/FK 混合属性 |
| `maya_rigging__mirror_joints` | 跨轴镜像关节 |
| `maya_rigging__set_joint_orient` | 设置关节方向 |
| `maya_rigging__set_joint_limit` | 设置关节旋转限制 |
| `maya_rigging__set_driven_key` | 创建 Set Driven Key 连接 |
| `maya_rigging__create_curve` | 创建 NURBS 曲线 |

### maya-mesh-ops（12 个）

网格编辑、布尔运算和几何实用程序。

| Action | 说明 |
|--------|------|
| `maya_mesh_ops__combine_meshes` | 合并多个网格 |
| `maya_mesh_ops__separate_mesh` | 将网格分离为多个 shell |
| `maya_mesh_ops__extract_faces` | 将选中面提取为新网格 |
| `maya_mesh_ops__mirror_mesh` | 跨轴镜像网格 |
| `maya_mesh_ops__triangulate` | 三角化多边形网格 |
| `maya_mesh_ops__apply_subdivision` | 对网格应用细分 |
| `maya_mesh_ops__cleanup_mesh` | 清理网格几何体（删除无效面等）|
| `maya_mesh_ops__merge_vertices` | 合并距离阈值内的顶点 |
| `maya_mesh_ops__get_poly_count` | 获取多边形/顶点/边数量 |
| `maya_mesh_ops__get_mesh_edge_info` | 获取边连接性和长度 |
| `maya_mesh_ops__select_by_material` | 选择指定材质的面 |
| `maya_mesh_ops__create_proxy_mesh` | 创建低精度代理网格 |

### 更多技能包

| 技能包 | 数量 | 功能 |
|--------|------|------|
| `maya-uv-ops` | 8 | UV 投影、展开、规格化、UV 集管理 |
| `maya-render` | 8 | 渲染设置、视口捕捉、文件 I/O、playblast |
| `maya-node-graph` | 9 | 属性连接、历史、平滑、属性传递 |
| `maya-cameras` | 5 | 摄影机创建、属性、切换视角 |
| `maya-lighting` | 4 | 灯光创建、属性和列表 |
| `maya-deformers` | 5 | 簇、晶格、线框、雕刻变形器 |
| `maya-constraints` | 4 | 父约束、点约束、方向约束、加权约束 |
| `maya-dynamics` | 10 | nCloth、nRigid、核子、动力学场 |
| `maya-attributes` | 5 | 自定义属性管理 |
| `maya-references` | 6 | Maya 参考文件管理、命名空间 |
| `maya-scene-utils` | 7 | 对齐、注释、颜色、轴心、着色模式 |
| `maya-selection` | 5 | 选择转换、扩展、收缩、反转 |
| `maya-sets` | 4 | Maya 对象集 |
| `maya-display` | 4 | 显示层管理 |
| `maya-render-layers` | 5 | 渲染层管理 |
| `maya-mash` | 5 | MASH 程序效果网络 |
| `maya-bifrost` | 5 | Bifrost 图表和模拟 |
| `maya-xgen` | 5 | XGen 描述和属性管理 |
| `maya-arnold-aov` | 5 | Arnold AOV 管理 |
| `maya-namespaces` | 3 | 命名空间操作 |
| `maya-scripting` | 2 | MEL 和 Python 脚本执行 |
| `maya-expressions` | 3 | Maya 表达式节点 |
| `maya-vertex-color` | 4 | 顶点颜色操作 |
| `maya-texture-bake` | 3 | 纹理烘焙、颜色管理配置 |
| `maya-utility` | 2 | 实用节点创建、场景统计 |
| `maya-audio` | 5 | 音频节点导入、时间轴同步 |
| `maya-cache` | 5 | nCache 和 Alembic 缓存管理 |
| `maya-fluid` | 5 | Maya Fluid Effects 流体模拟 |
| `maya-grooming` | 5 | XGen 互动梳理毛发管理 |
| `maya-muscle` | 5 | Maya Muscle 变形系统 |
| `maya-nparticles` | 5 | nParticle 粒子模拟系统 |
| `maya-ocean` | 5 | Maya Ocean 海洋模拟 |
| `maya-paint-effects` | 5 | Paint Effects 笔触和笔刷管理 |
| `maya-toon` | 5 | 卡通着色器与轮廓线管理 |

完整 Action 参数和示例请参阅 [API 参考](/zh/api/actions)。

