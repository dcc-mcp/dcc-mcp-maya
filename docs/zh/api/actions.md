# Action API 参考（中文）

参阅英文版 [Actions API Reference](/api/actions) 获取完整文档。

本页提供中文说明补充。

## Action 脚本规范

每个 `scripts/` 下的 `.py` 文件必须定义一个**与文件名相同的顶层函数**。

### 最小示例

```python
# scripts/create_sphere.py
"""在 Maya 场景中创建多边形球体。"""


def create_sphere(
    name: str = "pSphere1",
    radius: float = 1.0,
    subdivisions_x: int = 20,
    subdivisions_y: int = 20,
    translate: list = None,
) -> dict:
    """创建多边形球体。

    Args:
        name: 新球体的名称。
        radius: 球体半径（场景单位）。
        subdivisions_x: 经度细分数。
        subdivisions_y: 纬度细分数。
        translate: [x, y, z] 位置，默认 [0, 0, 0]。

    Returns:
        dict: ``{"name": str, "success": bool, "message": str}``
    """
    import maya.cmds as cmds

    if translate is None:
        translate = [0.0, 0.0, 0.0]

    sphere, _ = cmds.polySphere(
        name=name,
        radius=radius,
        subdivisionsX=subdivisions_x,
        subdivisionsY=subdivisions_y,
    )
    cmds.move(*translate, sphere)

    return {
        "name": sphere,
        "success": True,
        "message": f"在 {translate} 创建了球体 '{sphere}'",
    }
```

## 关键规则

1. **延迟导入** — 在函数内部导入 `maya.cmds`，不在模块级别导入
2. **返回可序列化的 dict** — 包含 `success` 和 `message` 字段
3. **用异常表示错误** — `dcc-mcp-core` 会捕获并返回 MCP 错误响应
4. **模块文档字符串** — 第一行成为 MCP 工具描述

详细规范见英文 [Actions API Reference](/api/actions)。
