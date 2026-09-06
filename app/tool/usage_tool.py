"""
usage_tool.py — OpenManus 自定义用量监控工具：查询各API今日用量。

功能：
1. 查询 gcli（谷歌中转）今日调用次数 / 上限950
2. 查询 智谱free（glm-4-flash）今日调用次数
3. 查询 智谱air（glm-4.5-air）今日token消耗 / 1200万额度
4. 查询 硅基（GLM-4-9B）今日调用次数
5. 查询 3标签（豆包/千问/智谱）今日调用次数
6. 查询 bridge_health 自愈触发次数

数据来源：usage/*.jsonl 日志文件（每次API调用都追加一条）。
"""

import json
import os
from datetime import datetime
from typing import ClassVar, Dict, Optional

from app.tool.base import BaseTool, ToolResult

PROJECT_ROOT = r"D:\360Downloads\金庸\一念永恒"
USAGE_DIR = os.path.join(PROJECT_ROOT, "一念永恒小说", "三个标签", "usage")

# 各API的用量上限
LIMITS = {
    "gcli": 950,           # 谷歌中转，1000/天留50缓冲
    "zhipu_free": 999999,  # 免费无上限
    "zhipu_air_tokens": 12_000_000,  # 智谱4.5-air，用户1200万额度
    "siliconflow": 999999, # 免费无上限
    "ask_tag": 999999,     # 3标签网页版
    "bridge_health": 999,  # 自愈次数
}


class UsageMonitor(BaseTool):
    """API用量监控工具：查询各通道今日调用次数和剩余额度。

    当用户问"API用了多少""还剩多少额度""gcli超了没""各模型消耗统计"时使用。
    返回各通道今日用量、上限、剩余量和使用率。
    """

    name: str = "usage_monitor"
    description: str = (
        "API用量监控工具。查询今日各通道调用次数和剩余额度："
        "gcli谷歌中转(上限950/天)、智谱free(glm-4-flash免费)、"
        "智谱air(glm-4.5-air收费,1200万token额度)、硅基(GLM-4-9B免费)、"
        "3标签网页版(豆包/千问/智谱)、bridge自愈次数。"
        "无参数，直接返回全部通道用量汇总。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "只查某个通道：gcli/zhipu_free/zhipu_air/siliconflow/ask_tag/bridge_health/all，默认all",
                "default": "all",
            },
        },
        "required": [],
    }

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _count_jsonl(self, filepath: str, date_field: str = "timestamp") -> Dict:
        """统计jsonl文件今日记录数和总token。"""
        if not os.path.exists(filepath):
            return {"count": 0, "tokens": 0}
        today = self._today_str()
        count = 0
        tokens = 0
        try:
            for line in open(filepath, encoding="utf-8"):
                try:
                    j = json.loads(line)
                    ts = j.get(date_field, j.get("time", ""))
                    if today in str(ts):
                        count += 1
                        tokens += int(j.get("tokens", j.get("total_tokens", 0)) or 0)
                except Exception:
                    pass
        except Exception:
            pass
        return {"count": count, "tokens": tokens}

    def _get_all_usage(self) -> Dict:
        """汇总所有通道今日用量。"""
        today = self._today_str()
        result = {"date": today, "channels": {}}

        # gcli
        gcli = self._count_jsonl(os.path.join(USAGE_DIR, "gcli_usage.jsonl"))
        result["channels"]["gcli"] = {
            "used": gcli["count"], "limit": LIMITS["gcli"],
            "remaining": LIMITS["gcli"] - gcli["count"],
            "usage_rate": f"{gcli['count']/LIMITS['gcli']*100:.1f}%",
        }

        # 智谱free
        zf = self._count_jsonl(os.path.join(USAGE_DIR, "zhipu_helper_usage.jsonl"))
        # 区分free和air：free的model字段是glm-4-flash
        free_count = 0
        air_tokens = 0
        air_count = 0
        try:
            for line in open(os.path.join(USAGE_DIR, "zhipu_helper_usage.jsonl"), encoding="utf-8"):
                try:
                    j = json.loads(line)
                    if today in str(j.get("timestamp", "")):
                        model = j.get("model", "")
                        if "flash" in model.lower():
                            free_count += 1
                        elif "air" in model.lower():
                            air_count += 1
                            air_tokens += int(j.get("tokens", 0) or 0)
                except Exception:
                    pass
        except Exception:
            pass
        result["channels"]["zhipu_free"] = {"used": free_count, "limit": "免费无上限"}
        result["channels"]["zhipu_air"] = {
            "used_calls": air_count, "used_tokens": air_tokens,
            "limit_tokens": LIMITS["zhipu_air_tokens"],
            "remaining_tokens": LIMITS["zhipu_air_tokens"] - air_tokens,
            "usage_rate": f"{air_tokens/LIMITS['zhipu_air_tokens']*100:.4f}%",
        }

        # 硅基
        sf = self._count_jsonl(os.path.join(USAGE_DIR, "siliconflow_helper_usage.jsonl"))
        result["channels"]["siliconflow"] = {"used": sf["count"], "limit": "免费无上限"}

        # 3标签
        at = self._count_jsonl(os.path.join(USAGE_DIR, "ask_tag_usage.jsonl"))
        result["channels"]["ask_tag_3labels"] = {"used": at["count"], "limit": "网页版无明确上限"}

        # bridge自愈
        bh = self._count_jsonl(os.path.join(USAGE_DIR, "bridge_health.jsonl"))
        result["channels"]["bridge_heal"] = {"used": bh["count"], "note": "今日自愈触发次数"}

        return result

    async def execute(self, channel: str = "all") -> ToolResult:
        """查询用量。"""
        data = self._get_all_usage()

        if channel != "all" and channel in data["channels"]:
            ch = data["channels"][channel]
            lines = [f"=== {channel} 今日用量 ==="]
            for k, v in ch.items():
                lines.append(f"  {k}: {v}")
            return self.success_response("\n".join(lines))

        # 全部通道汇总
        lines = [f"=== API用量汇总 ({data['date']}) ==="]
        c = data["channels"]

        lines.append("\n【收费/有限额通道】")
        lines.append(f"  gcli谷歌中转: {c['gcli']['used']}/{c['gcli']['limit']} "
                     f"(剩{c['gcli']['remaining']}, {c['gcli']['usage_rate']})")
        lines.append(f"  智谱4.5-air: {c['zhipu_air']['used_calls']}次 / "
                     f"{c['zhipu_air']['used_tokens']:,}token / "
                     f"额度{c['zhipu_air']['limit_tokens']:,} "
                     f"({c['zhipu_air']['usage_rate']})")

        lines.append("\n【免费通道】")
        lines.append(f"  智谱free(glm-4-flash): {c['zhipu_free']['used']}次")
        lines.append(f"  硅基(GLM-4-9B): {c['siliconflow']['used']}次")
        lines.append(f"  3标签网页版: {c['ask_tag_3labels']['used']}次")

        lines.append("\n【系统】")
        lines.append(f"  bridge自愈触发: {c['bridge_heal']['used']}次")

        # 告警
        warnings = []
        if c["gcli"]["used"] > 800:
            warnings.append(f"⚠️ gcli已用{c['gcli']['used']}次，接近上限950！")
        if c["zhipu_air"]["used_tokens"] > 10_000_000:
            warnings.append(f"⚠️ air已用{c['zhipu_air']['used_tokens']:,}token，接近1200万额度！")
        if warnings:
            lines.append("\n【告警】")
            for w in warnings:
                lines.append(f"  {w}")

        return self.success_response("\n".join(lines))


if __name__ == "__main__":
    import asyncio
    async def _main():
        tool = UsageMonitor()
        r = await tool.execute()
        print(str(r))
    asyncio.run(_main())
