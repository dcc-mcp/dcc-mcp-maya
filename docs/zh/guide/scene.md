# 场景信息查询

查询 Maya 场景状态 — 层次结构、会话信息、对象属性。

## 会话信息

获取当前 Maya 会话的高层概览：

**工具：** `maya_scene__get_session_info`

```json
{
  "maya_version": "2024.1",
  "scene_path": "/path/to/my_scene.ma",
  "fps": 24.0,
  "start_frame": 1,
  "end_frame": 120,
  "object_count": 42,
  "selection_count": 0
}
```

自然语言：`"我用的是什么版本的 Maya？场景里有多少对象？"`

## 场景层次结构

以嵌套结构获取完整 DAG 层次：

**工具：** `maya_scene__get_scene_info`

```json
{
  "name": "root",
  "children": [
    {
      "name": "pSphere1",
      "type": "transform",
      "children": [
        { "name": "pSphereShape1", "type": "mesh" }
      ]
    }
  ]
}
```

## 列出对象

按类型过滤对象：

**工具：** `maya_scene__list_objects`

```
"列出场景中的所有网格对象"
"显示所有摄像机"
"列出绑定中的所有关节"
```

## 选择操作

### 获取选择

**工具：** `maya_scene__get_selection`

```json
{
  "selection": ["pSphere1", "pCube1"],
  "count": 2
}
```

### 设置选择

**工具：** `maya_scene__set_selection`

```
"选择 pSphere1 和 pCube1"
"选择所有网格对象"
```

## 包围盒

查询任意对象的世界空间包围盒：

**工具：** `maya_scene__get_bounding_box`

```json
{
  "object": "pSphere1",
  "min": [-1.0, -1.0, -1.0],
  "max": [1.0, 1.0, 1.0],
  "center": [0.0, 0.0, 0.0],
  "size": [2.0, 2.0, 2.0]
}
```

## 实用查询

```
"场景里有哪些对象？"
"pSphere1 在什么位置？"
"角色网格的包围盒是多少？"
"场景有没有保存？当前文件路径是什么？"
"场景里有多少多边形？"
```
