# -*- coding: utf-8 -*-
"""
optimize_plans_tool.py · 方案三标签深度优化工具
====================================================
让统帅调用此工具，自动完成：
  ① 读取10个方案文件
  ② 每个方案拆成3份
  ③ 分别发给三个标签（豆包/千问/智谱）做深度思考
  ④ 收集改进建议，汇总成最终优化版
  ⑤ 全程实时日志 + 用量记账

统帅只需要调用这个工具，不需要自己处理细节。
"""
import os
import sys
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from app.tool.base import BaseTool, ToolResult

BASE = r"D:\360Downloads\金庸\一念永恒"
SCRIPT = os.path.join(BASE, "一念永恒小说", "三个标签", "半个智能体代码库", "执行层", "optimize_plans_3tags.py")
PLANS_DIR = os.path.join(BASE, "一念永恒小说", "开源拉取", "OpenManus", "training_logs", "网友成熟方案收藏")
OUTPUT_DIR = os.path.join(PLANS_DIR, "三标签优化版")
LOG_DIR = os.path.join(PLANS_DIR, "logs")


class OptimizePlansTool(BaseTool):
    name: str = "optimize_plans"
    description: str = (
        "方案三标签深度优化工具。将10个OpenManus成熟方案分别拆成3份，"
        "分别发给豆包、千问国际版、智谱清言三个标签做深度思考，"
        "收集他们的改进建议（只做加法不做减法），汇总成最终优化版。"
        "参数：plan='all'优化全部10个方案，plan='1'只优化第1个，plan='1-3'优化第1-3个。"
        "返回：优化结果汇总，包括每个方案的输出文件路径和三个标签的调用情况。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "plan": {
                "type": "string",
                "description": "优化哪些方案：all（全部10个）/ 1（第1个）/ 1-3（第1到3个）",
                "default": "all"
            },
            "action": {
                "type": "string",
                "description": "操作类型：start（启动优化）/ status（查看进度）/ result（查看结果）",
                "default": "start"
            }
        },
        "required": []
    }

    async def execute(self, plan: str = "all", action: str = "start") -> ToolResult:
        """执行方案优化"""
        if action == "status":
            return self._get_status()
        elif action == "result":
            return self._get_result()
        else:
            return await self._start_optimize(plan)

    async def _start_optimize(self, plan: str) -> ToolResult:
        """启动优化任务（异步子进程，立即返回）"""
        # 检查脚本是否存在
        if not os.path.exists(SCRIPT):
            return self.error_response(f"优化脚本不存在: {SCRIPT}")

        # 创建日志文件
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, f"optimize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        # 启动子进程
        cmd = [
            sys.executable, "-u", SCRIPT,
            "--plan", plan
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=os.path.dirname(SCRIPT)
            )

            # 后台任务：实时读取输出并写入日志
            asyncio.create_task(self._monitor_output(proc, log_file))

            result = {
                "ok": True,
                "started": True,
                "pid": proc.pid,
                "plan": plan,
                "log_file": log_file,
                "output_dir": OUTPUT_DIR,
                "message": f"方案优化已启动，正在后台运行。计划优化{plan}个方案，每个方案拆成3份发给三个标签。"
            }
            return self.success_response(json.dumps(result, ensure_ascii=False, indent=2))

        except Exception as e:
            return self.error_response(f"启动优化失败: {str(e)}")

    async def _monitor_output(self, proc, log_file):
        """后台监控子进程输出，实时写入日志"""
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode("utf-8", errors="replace").strip()
                    f.write(f"[{time.strftime('%H:%M:%S')}] {line_str}\n")
                    f.flush()
                    print(f"[optimize_plans] {line_str}")
                await proc.wait()
                f.write(f"[{time.strftime('%H:%M:%S')}] 优化任务完成，退出码: {proc.returncode}\n")
        except Exception as e:
            print(f"[optimize_plans] 监控异常: {e}")

    def _get_status(self) -> ToolResult:
        """查看优化进度"""
        # 检查最新日志
        if not os.path.exists(LOG_DIR):
            return self.success_response("暂无优化记录")

        logs = sorted([f for f in os.listdir(LOG_DIR) if f.endswith('.log')], reverse=True)
        if not logs:
            return self.success_response("暂无优化记录")

        latest_log = os.path.join(LOG_DIR, logs[0])
        with open(latest_log, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 检查输出目录
        output_files = []
        if os.path.exists(OUTPUT_DIR):
            output_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.md')]

        status = {
            "latest_log": latest_log,
            "log_lines": len(lines),
            "recent_log": "\n".join(lines[-10:]) if lines else "空",
            "output_files_count": len(output_files),
            "output_files": output_files[:10]
        }
        return self.success_response(json.dumps(status, ensure_ascii=False, indent=2))

    def _get_result(self) -> ToolResult:
        """查看优化结果"""
        if not os.path.exists(OUTPUT_DIR):
            return self.error_response("输出目录不存在，可能还未完成优化")

        files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('_优化版.md')]
        if not files:
            return self.success_response("暂无优化完成的方案，请先用 action=start 启动优化")

        result = {
            "completed_count": len(files),
            "completed_files": sorted(files),
            "output_dir": OUTPUT_DIR
        }
        return self.success_response(json.dumps(result, ensure_ascii=False, indent=2))
