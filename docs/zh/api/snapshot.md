# 截图 API

通过 `maya-render` Skill 进行视口截图。

## 工具：`maya_render__playblast`

将活动（或指定）Maya 视口捕获为 base64 编码的 PNG。

### 参数

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | int | `960` | 输出图像宽度（像素） |
| `height` | int | `540` | 输出图像高度（像素） |
| `camera` | str | _(活动视口摄像机)_ | 摄像机名称，如 `"persp"`、`"front"`、`"top"` |
| `display_mode` | str | `"smoothShaded"` | 视口显示模式 |

**display_mode 可选值：**

| 值 | 说明 |
|----|------|
| `smoothShaded` | 平滑着色（带贴图） |
| `flatShaded` | 平面着色多边形 |
| `wireframe` | 仅线框 |
| `boundingBox` | 包围盒显示 |

### 返回值

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "width": 960,
  "height": 540,
  "camera": "persp",
  "format": "png",
  "encoding": "base64"
}
```

### 解码图像

```python
import base64

image_b64 = result["image"]
image_bytes = base64.b64decode(image_b64)

with open("snapshot.png", "wb") as f:
    f.write(image_bytes)
```

## 工具：`maya_render__get_render_settings`

查询当前渲染设置。

### 返回值

```json
{
  "renderer": "arnold",
  "width": 1920,
  "height": 1080,
  "start_frame": 1,
  "end_frame": 120,
  "image_format": "exr",
  "output_path": "/renders/my_scene"
}
```
