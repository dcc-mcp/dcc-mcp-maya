# 视口截图

捕获 Maya 视口图像，用于 AI 视觉反馈、审阅工作流或自动化流水线。

## MCP 工具

`maya_render__playblast` 工具将活动视口捕获为 **base64 编码的 PNG**。

```python
# 由 MCP 宿主内部调用 — 无需 Python 代码
# 只需告诉 AI："截取当前视口截图"
```

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | int | `960` | 图像宽度（像素） |
| `height` | int | `540` | 图像高度（像素） |
| `camera` | str | _(活动摄像机)_ | 渲染摄像机（如 `"persp"`、`"top"`） |
| `display_mode` | str | `"smoothShaded"` | 显示模式：`smoothShaded`、`wireframe`、`flatShaded` |

## 使用示例

### 通过 MCP 宿主（自然语言）

> **"截取场景截图"**
>
> **"以 1920×1080 分辨率截取正视图"**
>
> **"用 persp 摄像机展示当前场景效果"**

## 返回值

工具返回 JSON 对象：

```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgA...",
  "width": 960,
  "height": 540,
  "camera": "persp",
  "format": "png",
  "encoding": "base64"
}
```

## 硬件截图 vs 完整渲染

| 特性 | `maya_render__playblast` | 完整渲染 |
|------|--------------------------|---------|
| 速度 | 即时（视口截图） | 慢（完整渲染） |
| 质量 | 硬件视口效果 | 生产级质量 |
| 需要 Arnold 等 | 否 | 取决于渲染器 |
| 适用场景 | AI 反馈、预览 | 最终输出 |

## 实用 AI 工作流

```
你：创建一个红色球体，放到 (0, 1, 0)，然后给我看看效果

Claude：
  1. 调用 maya_primitives__create_sphere
  2. 调用 maya_primitives__set_transform（位移到 0,1,0）
  3. 调用 maya_materials__create_material（红色 Lambert）
  4. 调用 maya_materials__assign_material
  5. 调用 maya_render__playblast
  → 显示结果图像
```
