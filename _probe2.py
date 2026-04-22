"""Isolated probe: discover the maya-scripting skill dir and check groups."""
from dcc_mcp_core import ToolRegistry, ToolDispatcher, SkillCatalog
from pathlib import Path

skills_root = Path("src/dcc_mcp_maya/skills").resolve()
print("skills_root:", skills_root)

reg = ToolRegistry()
disp = ToolDispatcher(reg)
cat = SkillCatalog(reg)
n = cat.discover([str(skills_root)])
print("discovered:", n)
cat.load_skill("maya-scripting")

actions = reg.list_actions()
scripting = [a for a in actions if 'maya_scripting' in a.get('name', '')]
print("scripting total:", len(scripting))
print("groups set:", set(a.get('group', '(unset)') for a in scripting))
print("enabled:", sum(1 for a in scripting if a.get('enabled')))
print("registry groups:", reg.list_groups())

info = cat.get_skill_info("maya-scripting")
print("tool groups from info:", [(t.name, t.group) for t in info.tools[:6]])
