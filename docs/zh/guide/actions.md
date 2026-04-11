# Action 完整列表

所有内置 Action 按 Skill 包组织，命名规则为：

```
{skill_name.replace("-", "_")}__{script_stem}
```

## 场景管理（`maya-scene`）

管理 Maya 场景生命周期、对象层次结构和场景状态。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 新建场景 | `maya_scene__new_scene` | 创建新的空 Maya 场景 |
| 保存场景 | `maya_scene__save_scene` | 将当前场景保存到磁盘 |
| 打开场景 | `maya_scene__open_scene` | 打开 Maya 场景文件（.ma/.mb） |
| 导出场景 | `maya_scene__export_scene` | 将整个场景导出到文件 |
| 列出对象 | `maya_scene__list_objects` | 列出 DAG 对象（支持类型过滤） |
| 获取选择 | `maya_scene__get_selection` | 返回当前选择列表 |
| 设置选择 | `maya_scene__set_selection` | 设置当前活动选择 |
| 按类型选择 | `maya_scene__select_by_type` | 选择指定 Maya 类型的所有对象 |
| 会话信息 | `maya_scene__get_session_info` | Maya 版本、场景路径、FPS、对象数量 |
| 场景信息 | `maya_scene__get_scene_info` | 场景的层次 DAG 描述 |
| 编组对象 | `maya_scene__group_objects` | 将对象编到新组节点下 |
| 设置父子关系 | `maya_scene__parent_object` | 设置或清除对象的父级 |
| 复制对象 | `maya_scene__duplicate_object` | 复制场景中的对象 |
| 冻结变换 | `maya_scene__freeze_transforms` | 冻结对象的变换 |
| 居中轴心 | `maya_scene__center_pivot` | 将轴心居中到包围盒中心 |
| 包围盒 | `maya_scene__get_bounding_box` | 查询世界空间包围盒 |
| 设置可见性 | `maya_scene__set_visibility` | 显示或隐藏对象 |
| 锁定对象 | `maya_scene__lock_object` | 锁定/解锁变换属性 |
| 设置帧率 | `maya_scene__set_frame_rate` | 更改场景播放帧率 |
| 列出摄像机 | `maya_scene__list_cameras` | 列出场景中的所有摄像机 |
| 创建定位器 | `maya_scene__create_locator` | 创建 Maya 定位器节点 |

## 几何体与基础体（`maya-primitives`）

创建多边形基础体并管理对象变换。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 创建球体 | `maya_primitives__create_sphere` | 创建多边形球体 |
| 创建立方体 | `maya_primitives__create_cube` | 创建多边形立方体 |
| 创建圆柱体 | `maya_primitives__create_cylinder` | 创建多边形圆柱体 |
| 创建平面 | `maya_primitives__create_plane` | 创建多边形平面 |
| 删除对象 | `maya_primitives__delete_objects` | 从场景中删除对象 |
| 设置变换 | `maya_primitives__set_transform` | 设置对象的位移/旋转/缩放 |
| 获取变换 | `maya_primitives__get_transform` | 获取对象的位移/旋转/缩放 |
| 重命名对象 | `maya_primitives__rename_object` | 重命名场景中的对象 |

## 动画（`maya-animation`）

完整动画流水线：关键帧、曲线、时间轴、模拟烘焙。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 打关键帧 | `maya_animation__set_keyframe` | 在指定时间给对象属性打关键帧 |
| 获取关键帧 | `maya_animation__get_keyframes` | 获取对象/属性的所有关键帧时间 |
| 设置时间轴 | `maya_animation__set_timeline` | 设置播放和动画范围 |
| 获取当前时间 | `maya_animation__get_current_time` | 获取当前帧号 |
| 设置当前时间 | `maya_animation__set_current_time` | 设置当前帧号 |
| 删除关键帧 | `maya_animation__delete_keyframes` | 删除可选帧范围内的关键帧 |
| 烘焙模拟 | `maya_animation__bake_simulation` | 将模拟/约束烘焙为关键帧 |
| 烘焙约束 | `maya_animation__bake_constraints` | 将约束驱动的动画烘焙为关键帧 |
| 列出动画曲线 | `maya_animation__list_animation_curves` | 列出驱动对象的所有 animCurve 节点 |
| 设置曲线切线 | `maya_animation__set_animation_curve_tangent` | 设置关键帧的切线类型 |
| 导出动画曲线 | `maya_animation__export_animation_curves` | 将动画曲线导出为 .anim 文件 |
| 导入动画曲线 | `maya_animation__import_animation_curves` | 从文件导入动画曲线 |
| 查询时间信息 | `maya_animation__query_scene_time_info` | 查询当前场景时间和播放设置 |

## 摄像机（`maya-cameras`）

创建和配置 Maya 摄像机。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 创建摄像机 | `maya_cameras__create_camera` | 创建带位置、旋转、焦距的摄像机 |
| 设置摄像机属性 | `maya_cameras__set_camera_attribute` | 设置 focalLength、nearClipPlane 等 |
| 获取摄像机信息 | `maya_cameras__get_camera_info` | 焦距、裁剪、光圈和变换信息 |
| 设置活动摄像机 | `maya_cameras__set_active_camera` | 设置视口中的活动摄像机 |

## 灯光（`maya-lighting`）

创建和管理 Maya 灯光。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 创建灯光 | `maya_lighting__create_light` | 创建平行光/点光/聚光/面光/环境光 |
| 设置灯光属性 | `maya_lighting__set_light_attribute` | 设置强度、颜色、阴影属性 |
| 列出灯光 | `maya_lighting__list_lights` | 列出所有灯光及类型和强度 |

## 渲染（`maya-render`）

渲染设置和视口截图。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 设置渲染设置 | `maya_render__set_render_settings` | 设置分辨率、帧范围、渲染器 |
| 获取渲染设置 | `maya_render__get_render_settings` | 查询当前渲染设置 |
| 视口截图 | `maya_render__playblast` | 将视口捕获为 base64 编码的 PNG |

## 材质（`maya-materials`）

创建和管理着色材质。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 创建材质 | `maya_materials__create_material` | 创建 Lambert/Blinn/Phong/Arnold 材质 |
| 赋予材质 | `maya_materials__assign_material` | 将材质赋予对象 |
| 设置材质属性 | `maya_materials__set_material_attribute` | 设置材质颜色、粗糙度等 |
| 列出材质 | `maya_materials__list_materials` | 列出所有场景材质 |

## 网格操作（`maya-mesh-ops`）

多边形网格操作：细分、布尔、清理等。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 细分 | `maya_mesh_ops__subdivide` | 细分多边形网格 |
| 布尔运算 | `maya_mesh_ops__boolean_operation` | 布尔并集/差集/交集 |
| 清理网格 | `maya_mesh_ops__cleanup_mesh` | 运行多边形清理 |
| 提取面 | `maya_mesh_ops__extract_face` | 将选中面提取为新网格 |
| 合并网格 | `maya_mesh_ops__combine_meshes` | 将多个网格合并为一个 |
| 分离网格 | `maya_mesh_ops__separate_meshes` | 分离合并的网格 |
| 填补洞 | `maya_mesh_ops__fill_hole` | 填补网格上的开放洞口 |
| 镜像 | `maya_mesh_ops__mirror_mesh` | 沿轴镜像网格 |
| 三角化 | `maya_mesh_ops__triangulate` | 将所有面转为三角形 |
| 四边化 | `maya_mesh_ops__quadrangulate` | 将三角形尽量转为四边形 |
| 平滑 | `maya_mesh_ops__smooth_mesh` | 应用平滑网格预览 |
| 多边形信息 | `maya_mesh_ops__get_poly_info` | 查询顶点/边/面数量 |

## UV 操作（`maya-uv-ops`）

UV 布局创建与编辑。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 平面投影 | `maya_uv_ops__planar_projection` | 应用平面 UV 投影 |
| 柱形投影 | `maya_uv_ops__cylindrical_projection` | 应用柱形 UV 投影 |
| 球形投影 | `maya_uv_ops__spherical_projection` | 应用球形 UV 投影 |
| 自动展开 | `maya_uv_ops__auto_unwrap` | 自动 UV 展开 |
| 规范化 UV | `maya_uv_ops__normalize_uvs` | 将 UV 规范化到 0–1 空间 |
| 翻转 UV | `maya_uv_ops__flip_uvs` | 水平或垂直翻转 UV |
| 旋转 UV | `maya_uv_ops__rotate_uvs` | 按指定角度旋转 UV |
| 布局 UV | `maya_uv_ops__layout_uvs` | 将 UV 壳打包到 0–1 区域 |

## 绑定（`maya-rigging`）

骨骼、IK、蒙皮集群和约束。

| Action | 工具名称 | 说明 |
|--------|----------|------|
| 创建关节 | `maya_rigging__create_joint` | 在指定位置创建关节 |
| 关节父子关系 | `maya_rigging__parent_joint` | 将一个关节放到另一个下面 |
| 创建 IK 手柄 | `maya_rigging__create_ik_handle` | 在关节之间创建 IK 手柄 |
| 绑定蒙皮 | `maya_rigging__bind_skin` | 将网格绑定到骨骼 |
| 解绑蒙皮 | `maya_rigging__unbind_skin` | 分离蒙皮集群 |
| 设置蒙皮权重 | `maya_rigging__set_skin_weights` | 设置顶点的蒙皮权重 |
| 获取蒙皮权重 | `maya_rigging__get_skin_weights` | 查询顶点的蒙皮权重 |
| 创建约束 | `maya_rigging__create_constraint` | 创建父级/点/朝向/缩放约束 |
| 删除约束 | `maya_rigging__remove_constraint` | 删除对象上的约束 |
| 创建混合变形 | `maya_rigging__create_blend_shape` | 创建混合变形变形器 |
| 设置混合变形权重 | `maya_rigging__set_blend_shape_weight` | 设置混合变形目标权重 |
