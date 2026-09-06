"""
notify_feishu_tool.py — OpenManus 自定义飞书推送工具。

功能：向飞书群推送消息（跑批完成/出错/监控通知等）。
当任务完成、出错、或需要通知用户时使用本工具。
参数: text=消息内容(必填); type=消息类型(text/run/error,可选); chapter=章节号(可选)。
"""

import sys
import os
from typing import ClassVar, Dict, Optional
from datetime import datetime

from app.tool.base import BaseTool, ToolResult

# 导入飞书推送脚本
FEISHU_DIR = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\脚本仓库\中转API"
if FEISHU_DIR not in sys.path:
    sys.path.insert(0, FEISHU_DIR)

try:
    from notify_feishu import send_feishu, format_run_notification, format_error_notification
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False


class NotifyFeishu(BaseTool):
    """飞书推送工具：向飞书群推送消息通知。

    当跑批任务完成、出现错误、或需要向用户发送监控通知时使用本工具。
    消息会自动加上【监控】关键词以通过飞书机器人安全校验。
    参数: text=消息内容(必填); type=消息类型(text/run/error); chapter=章节号(run类型用)。
    """

    name: str = "notify_feishu"
    description: str = (
        "飞书推送工具。向飞书群发送消息通知，用于跑批完成、错误告警、监控通知等场景。"
        "消息自动包含【监控】关键词通过安全校验。"
        "参数: text=消息内容(必填); type=消息类型(text普通/run跑批/error错误,默认text); "
        "chapter=章节号(type=run时用); days_done=已完成天数; days_total=总天数。"
    )
    parameters: ClassVar[Dict] = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "消息内容",
            },
            "type": {
                "type": "string",
                "description": "消息类型: text=普通, run=跑批通知, error=错误告警",
                "enum": ["text", "run", "error"],
                "default": "text",
            },
            "chapter": {
                "type": "integer",
                "description": "章节号（type=run时使用）",
            },
            "days_done": {
                "type": "integer",
                "description": "已完成天数（type=run时使用）",
            },
            "days_total": {
                "type": "integer",
                "description": "总天数（type=run时使用）",
            },
        },
        "required": ["text"],
    }

    async def execute(self, text: str, type: str = "text", 
                      chapter: Optional[int] = None,
                      days_done: Optional[int] = None,
                      days_total: Optional[int] = None,
                      **kwargs) -> ToolResult:
        """执行飞书推送。"""
        if not FEISHU_AVAILABLE:
            return ToolResult(output="❌ 飞书推送模块不可用（notify_feishu.py导入失败）", success=False)

        # 根据类型格式化消息
        if type == "run" and chapter is not None:
            msg = format_run_notification(
                chapter=chapter,
                days_done=days_done or 0,
                days_total=days_total or 6,
                status="完成" if (days_done and days_total and days_done >= days_total) else "进行中"
            )
        elif type == "error":
            msg = format_error_notification(error_msg=text)
        else:
            msg = text

        # 发送（使用asyncio.to_thread避免阻塞事件循环）
        import asyncio
        result = await asyncio.to_thread(send_feishu, msg)
        
        if result["success"]:
            return ToolResult(
                output=f"✅ 飞书推送成功\n消息: {msg[:100]}...",
                success=True,
                message=msg
            )
        else:
            return ToolResult(
                output=f"❌ 飞书推送失败: {result['error'] or result['response']}",
                success=False,
                error=result["error"]
            )
