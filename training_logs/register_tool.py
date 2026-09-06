# -*- coding: utf-8 -*-
"""注册optimize_plans工具到manus.py"""

with open('app/agent/manus.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加import
old_import = "from app.tool.status_monitor_tool import StatusMonitor"
new_import = """from app.tool.status_monitor_tool import StatusMonitor
from app.tool.optimize_plans_tool import OptimizePlansTool"""

if old_import in content and "optimize_plans_tool" not in content:
    content = content.replace(old_import, new_import)
    print("已添加import")
else:
    print("import已存在或未找到")

# 2. 在available_tools中添加工具
old_tool = "            StatusMonitor(),  # 实时状态监控：更新/查询当前任务状态，关键节点自动记录"
new_tool = """            StatusMonitor(),  # 实时状态监控：更新/查询当前任务状态，关键节点自动记录
            OptimizePlansTool(),  # 方案三标签深度优化：拆分方案→发给三个标签→汇总改进建议"""

if old_tool in content and "OptimizePlansTool()" not in content:
    content = content.replace(old_tool, new_tool)
    print("已添加工具到available_tools")
else:
    print("工具已存在或未找到")

with open('app/agent/manus.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修改完成")
