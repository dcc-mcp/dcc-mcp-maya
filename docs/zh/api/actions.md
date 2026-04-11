# Action API 参考

详见英文文档 [Action API Reference](/api/actions)，下方为中文摘要说明。

## 命名规则

```
{skill_name.replace("-", "_")}__{script_stem}
```

| Skill 包 | MCP 工具前缀 |
|----------|-------------|
| `maya-scene` | `maya_scene__` |
| `maya-primitives` | `maya_primitives__` |
| `maya-animation` | `maya_animation__` |
| `maya-cameras` | `maya_cameras__` |
| `maya-lighting` | `maya_lighting__` |
| `maya-render` | `maya_render__` |
| `maya-materials` | `maya_materials__` |
| `maya-mesh-ops` | `maya_mesh_ops__` |
| `maya-uv-ops` | `maya_uv_ops__` |
| `maya-rigging` | `maya_rigging__` |

## 关键 Action 速览

### `maya_scene__new_scene`

创建新的空 Maya 场景。

**参数：** 无

**返回值：**

```json
{ "success": true }
```

---

### `maya_primitives__create_sphere`

创建多边形球体。

**参数：**

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | `"pSphere1"` | 节点名称 |
| `radius` | float | `1.0` | 球体半径 |
| `subdiv_x` | int | `20` | X 方向细分数 |
| `subdiv_y` | int | `20` | Y 方向细分数 |

---

### `maya_animation__set_keyframe`

在指定时间给对象属性打关键帧。

**参数：**

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `object_name` | str | — | 目标对象 |
| `time` | float | — | 帧号 |
| `attribute` | str | `null` | 属性名（如 `"translateY"`）；省略则打所有属性 |
| `value` | float | `null` | 要设置的值；省略则使用当前值 |

---

### `maya_render__playblast`

将活动视口捕获为 base64 编码的 PNG。

**参数：**

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | int | `960` | 图像宽度 |
| `height` | int | `540` | 图像高度 |
| `camera` | str | _(活动摄像机)_ | 摄像机名称 |
| `display_mode` | str | `"smoothShaded"` | 显示模式 |

**返回值：**

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgA...",
  "width": 960,
  "height": 540,
  "format": "png",
  "encoding": "base64"
}
```

---

### `maya_lighting__create_light`

创建 Maya 灯光。

**参数：**

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `light_type` | str | `"directionalLight"` | 灯光类型 |
| `name` | str | `null` | 节点名称 |
| `intensity` | float | `1.0` | 灯光强度 |
| `color` | list[float] | `[1, 1, 1]` | RGB 颜色（0–1） |
| `position` | list[float] | `[0, 0, 0]` | 世界空间位置 |
| `rotation` | list[float] | `[0, 0, 0]` | 世界空间旋转（度） |
