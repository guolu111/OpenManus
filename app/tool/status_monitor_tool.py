"""
status_monitor_tool.py — OpenManus 自定义实时状态监控工具。

功能：
1. 更新当前任务状态（pending/running/completed/error）
2. 查询当前状态
3. 记录历史状态到日志文件
4. 计算任务已用时间

当统帅执行任务时，在关键节点调用本工具更新状态，
方便用户实时监控任务进度。

参数: action=操作类型(update/get/history); status=状态; task=任务名; step=当前步骤
"""

import json
import os
from datetime import datetime
from typing import ClassVar, Dict, Optional

from app.tool.base import BaseTool, ToolResult

# 状态文件路径
STATUS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
STATUS_FILE = os.path.join(STATUS_DIR, "current_status.json")
HISTORY_FILE = os.path.join(STATUS_DIR, "status_history.jsonl")


class StatusMonitor(BaseTool):
    """实时状态监控工具：更新和查询统帅当前任务状态。

    当统帅执行任务时，在关键节点（开始/完成/出错）调用本工具更新状态。
    用户可以通过查询状态了解任务进度。
    参数: action=操作类型(update/get/history); status=状态(pending/running/completed/error);
    task=任务名称; step=当前步骤; detail=详细信息。
    """

    name: str = "status_monitor"
    description: str = (
        "实时状态监控工具。更新和查询统帅当前任务状态，用于实时监控任务进度。"
        "在任务开始、完成、出错时调用update更新状态；用get查询当前状态；"
        "用history查询历史状态。"
        "参数: action=操作类型(update/get/history,默认get); "
        "status=状态(pending/running/completed/error,仅update用); "
        "task=任务名称(仅update用); step=当前步骤(仅update用); "
        "detail=详细信息(仅update用)。"
    )
    parameters: ClassVar[Dict] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型: update=更新状态, get=查询当前状态, history=查询历史状态",
                "enum": ["update", "get", "history"],
                "default": "get",
            },
            "status": {
                "type": "string",
                "description": "任务状态: pending=等待, running=运行中, completed=完成, error=错误",
                "enum": ["pending", "running", "completed", "error"],
            },
            "task": {
                "type": "string",
                "description": "任务名称",
            },
            "step": {
                "type": "string",
                "description": "当前步骤",
            },
            "detail": {
                "type": "string",
                "description": "详细信息",
            },
        },
        "required": ["action"],
    }

    def _ensure_dir(self):
        """确保日志目录存在。"""
        os.makedirs(STATUS_DIR, exist_ok=True)

    def _load_status(self) -> Dict:
        """加载当前状态。"""
        self._ensure_dir()
        if not os.path.exists(STATUS_FILE):
            return {
                "status": "pending",
                "task": "none",
                "step": "none",
                "detail": "",
                "start_time": None,
                "last_update": None,
            }
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "status": "pending",
                "task": "none",
                "step": "none",
                "detail": "",
                "start_time": None,
                "last_update": None,
            }

    def _save_status(self, status_data: Dict):
        """保存当前状态。"""
        self._ensure_dir()
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=4, ensure_ascii=False)

    def _append_history(self, status_data: Dict):
        """追加历史状态。"""
        self._ensure_dir()
        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(status_data, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _calc_elapsed(self, start_time: str) -> str:
        """计算已用时间。"""
        if not start_time:
            return "N/A"
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            elapsed = datetime.now() - start
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            seconds = elapsed.seconds % 60
            if hours > 0:
                return f"{hours}小时{minutes}分{seconds}秒"
            elif minutes > 0:
                return f"{minutes}分{seconds}秒"
            else:
                return f"{seconds}秒"
        except Exception:
            return "N/A"

    async def execute(self, action: str = "get",
                      status: Optional[str] = None,
                      task: Optional[str] = None,
                      step: Optional[str] = None,
                      detail: Optional[str] = None,
                      **kwargs) -> ToolResult:
        """执行状态监控操作。"""
        try:
            if action == "update":
                # 更新状态
                current = self._load_status()

                if status:
                    current["status"] = status
                if task:
                    current["task"] = task
                if step:
                    current["step"] = step
                if detail:
                    current["detail"] = detail

                # 如果状态变为running且没有开始时间，设置开始时间
                if status == "running" and not current.get("start_time"):
                    current["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 如果状态变为completed或error，计算结束时间
                if status in ["completed", "error"]:
                    current["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    current["elapsed"] = self._calc_elapsed(current.get("start_time", ""))

                current["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 保存状态
                self._save_status(current)

                # 追加历史
                self._append_history(current)

                # 构建返回信息
                status_emoji = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "error": "❌",
                }.get(current.get("status", ""), "❓")

                result = (
                    f"{status_emoji} 状态已更新\n"
                    f"  状态: {current.get('status')}\n"
                    f"  任务: {current.get('task')}\n"
                    f"  步骤: {current.get('step')}\n"
                    f"  详情: {current.get('detail', '')}\n"
                    f"  最后更新: {current.get('last_update')}"
                )
                if current.get("elapsed"):
                    result += f"\n  已用时间: {current.get('elapsed')}"

                return ToolResult(output=result, success=True, message=result)

            elif action == "get":
                # 查询当前状态
                current = self._load_status()

                status_emoji = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "error": "❌",
                }.get(current.get("status", ""), "❓")

                elapsed = self._calc_elapsed(current.get("start_time", ""))

                result = (
                    f"{status_emoji} 当前状态\n"
                    f"  状态: {current.get('status')}\n"
                    f"  任务: {current.get('task')}\n"
                    f"  步骤: {current.get('step')}\n"
                    f"  详情: {current.get('detail', '')}\n"
                    f"  开始时间: {current.get('start_time', 'N/A')}\n"
                    f"  已用时间: {elapsed}\n"
                    f"  最后更新: {current.get('last_update', 'N/A')}"
                )

                return ToolResult(output=result, success=True, message=result)

            elif action == "history":
                # 查询历史状态
                self._ensure_dir()
                if not os.path.exists(HISTORY_FILE):
                    return ToolResult(output="暂无历史状态记录", success=True)

                try:
                    history = []
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    history.append(json.loads(line))
                                except Exception:
                                    pass

                    if not history:
                        return ToolResult(output="暂无历史状态记录", success=True)

                    # 只返回最近10条
                    recent = history[-10:]
                    result_lines = ["📊 历史状态记录（最近10条）:"]
                    for i, h in enumerate(recent, 1):
                        status_emoji = {
                            "pending": "⏳",
                            "running": "🔄",
                            "completed": "✅",
                            "error": "❌",
                        }.get(h.get("status", ""), "❓")
                        result_lines.append(
                            f"  {i}. {status_emoji} {h.get('status')} | "
                            f"{h.get('task', 'N/A')} | "
                            f"{h.get('step', 'N/A')} | "
                            f"{h.get('last_update', 'N/A')}"
                        )

                    return ToolResult(output="\n".join(result_lines), success=True)

                except Exception as e:
                    return ToolResult(output=f"❌ 读取历史状态失败: {str(e)}", success=False)

            else:
                return ToolResult(output=f"❌ 未知操作类型: {action}", success=False)

        except Exception as e:
            return ToolResult(output=f"❌ 状态监控工具执行失败: {str(e)}", success=False, error=str(e))


if __name__ == "__main__":
    import asyncio

    async def _main():
        tool = StatusMonitor()

        # 测试更新状态
        print("=== 测试更新状态 ===")
        r = await tool.execute(action="update", status="running", task="测试任务", step="第1步", detail="测试详情")
        print(str(r))

        # 测试查询状态
        print("\n=== 测试查询状态 ===")
        r = await tool.execute(action="get")
        print(str(r))

        # 测试完成状态
        print("\n=== 测试完成状态 ===")
        r = await tool.execute(action="update", status="completed", task="测试任务", step="完成", detail="测试完成")
        print(str(r))

        # 测试历史状态
        print("\n=== 测试历史状态 ===")
        r = await tool.execute(action="history")
        print(str(r))

    asyncio.run(_main())
