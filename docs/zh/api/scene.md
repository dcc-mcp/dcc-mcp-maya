# 场景 API 参考

来自 `maya-scene` Skill 的场景检查与管理工具。

## `maya_scene__get_session_info`

返回高层次的 Maya 会话信息。

### 返回值

```typescript
{
  maya_version: string      // 如 "2024.1"
  scene_path: string        // 当前文件路径，未保存时为 ""
  fps: number               // 播放帧率
  start_frame: number       // 动画开始帧
  end_frame: number         // 动画结束帧
  object_count: number      // DAG 节点总数
  selection_count: number   // 当前选中对象数
}
```

---

## `maya_scene__get_scene_info`

返回场景的层次 DAG 描述。

### 返回值

```typescript
{
  name: string
  children: Array<{
    name: string
    type: string        // Maya 节点类型
    children: Array<...>
  }>
}
```

---

## `maya_scene__list_objects`

按可选类型过滤列出场景对象。

### 参数

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type_filter` | str | `""` | Maya 节点类型（如 `"mesh"`、`"camera"`、`"joint"`） |
| `long_names` | bool | `false` | 返回完整 DAG 路径 |

### 返回值

```json
{
  "objects": ["pSphere1", "pCube1"],
  "count": 2,
  "type_filter": "mesh"
}
```

---

## `maya_scene__get_bounding_box`

查询对象的世界空间包围盒。

### 参数

| 名称 | 类型 | 说明 |
|------|------|------|
| `object_name` | str | Maya 对象名称 |

### 返回值

```json
{
  "object": "pSphere1",
  "min": [-1.0, -1.0, -1.0],
  "max": [1.0, 1.0, 1.0],
  "center": [0.0, 0.0, 0.0],
  "size": [2.0, 2.0, 2.0]
}
```

---

## `maya_scene__group_objects`

将对象编组到新的组节点下。

### 参数

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `objects` | list[str] | — | 要编组的对象 |
| `group_name` | str | `"group1"` | 新组的名称 |
| `world` | bool | `false` | 在世界级别创建组 |

### 返回值

```json
{ "success": true, "group": "group1" }
```

---

## `maya_scene__export_scene`

将整个场景导出为文件。

### 参数

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | str | — | 输出文件路径 |
| `file_type` | str | `"mayaAscii"` | `"mayaAscii"`、`"mayaBinary"`、`"fbx"`、`"obj"` |
| `selection_only` | bool | `false` | 仅导出选中的对象 |
