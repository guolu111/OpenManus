# -*- coding: utf-8 -*-
"""
Dreaming 异步复盘模块
参考网友成熟方案：Agent自进化飞轮中的 Dreaming 异步复盘机制

功能：
1. 空闲时批量扫描历史任务轨迹
2. 自动挖掘三类隐性问题：
   - 反复出现的零散失败模式
   - 流程冗余的低效执行链路
   - 长期依赖外部查询的知识缺口
3. 输出结构化优化建议
4. 经人工审核后纳入正式迭代流水线

用法：
    python -m app.dreaming.dreaming --scan
    python -m app.dreaming.dreaming --report
    python -m app.dreaming.dreaming --daemon  # 后台守护进程模式
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger


class DreamingAnalyzer:
    """Dreaming 异步复盘分析器"""

    def __init__(self, logs_dir: str = "logs", output_dir: str = "logs/dreaming"):
        self.logs_dir = logs_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def scan_history_tasks(self, days: int = 7) -> List[Dict[str, Any]]:
        """扫描历史任务日志"""
        tasks = []
        cutoff_date = datetime.now() - timedelta(days=days)

        # 扫描任务报告文件
        report_pattern = re.compile(r'task_report_(\d{8})_(\d{6})\.txt')
        if os.path.exists(self.logs_dir):
            for filename in os.listdir(self.logs_dir):
                match = report_pattern.match(filename)
                if match:
                    date_str = match.group(1)
                    try:
                        file_date = datetime.strptime(date_str, "%Y%m%d")
                        if file_date >= cutoff_date:
                            filepath = os.path.join(self.logs_dir, filename)
                            task_info = self._parse_task_report(filepath)
                            if task_info:
                                tasks.append(task_info)
                    except ValueError:
                        continue

        # 扫描状态历史
        status_file = os.path.join(self.logs_dir, "status_history.jsonl")
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            tasks.append({
                                "type": "status",
                                "timestamp": record.get("timestamp", ""),
                                "task_id": record.get("task_id", ""),
                                "status": record.get("status", ""),
                                "error": record.get("error", ""),
                            })
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"读取状态历史失败: {e}")

        logger.info(f"🌙 Dreaming: 扫描到 {len(tasks)} 条历史任务记录")
        return tasks

    def _parse_task_report(self, filepath: str) -> Optional[Dict[str, Any]]:
        """解析任务报告文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单解析：提取关键信息
            task_info = {
                "type": "task_report",
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "content_length": len(content),
                "has_error": "错误" in content or "失败" in content or "error" in content.lower(),
                "has_timeout": "超时" in content or "timeout" in content.lower(),
                "has_api_error": "429" in content or "500" in content or "API" in content,
            }
            return task_info
        except Exception as e:
            logger.warning(f"解析任务报告失败 {filepath}: {e}")
            return None

    def detect_failure_patterns(self, tasks: List[Dict]) -> List[Dict[str, Any]]:
        """检测反复出现的失败模式"""
        patterns = []

        # 统计错误类型
        error_counts = {}
        timeout_count = 0
        api_error_count = 0

        for task in tasks:
            if task.get("has_error"):
                error_type = "general_error"
                if task.get("has_timeout"):
                    error_type = "timeout"
                    timeout_count += 1
                elif task.get("has_api_error"):
                    error_type = "api_error"
                    api_error_count += 1

                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # 识别反复出现的失败（出现3次以上）
        for error_type, count in error_counts.items():
            if count >= 3:
                patterns.append({
                    "type": "repeated_failure",
                    "error_type": error_type,
                    "occurrences": count,
                    "severity": "high" if count >= 5 else "medium",
                    "suggestion": self._get_failure_suggestion(error_type, count),
                })

        logger.info(f"🌙 Dreaming: 检测到 {len(patterns)} 个反复失败模式")
        return patterns

    def _get_failure_suggestion(self, error_type: str, count: int) -> str:
        """获取失败模式的修复建议"""
        suggestions = {
            "timeout": "增加超时时间或优化执行效率，检查是否有死循环",
            "api_error": "检查API密钥和额度，添加自动重试和降级机制",
            "general_error": "分析错误日志，定位根因，添加错误处理",
        }
        return suggestions.get(error_type, "分析错误日志，定位根因")

    def detect_redundant_workflows(self, tasks: List[Dict]) -> List[Dict[str, Any]]:
        """检测流程冗余的低效执行链路"""
        # 简化实现：检测重复执行相同类型任务的情况
        workflows = []

        # 统计相似任务的执行频率
        task_types = {}
        for task in tasks:
            task_type = task.get("type", "unknown")
            task_types[task_type] = task_types.get(task_type, 0) + 1

        # 识别高频重复任务（可能可以批量处理或缓存）
        for task_type, count in task_types.items():
            if count >= 5:
                workflows.append({
                    "type": "redundant_workflow",
                    "task_type": task_type,
                    "occurrences": count,
                    "suggestion": "考虑批量处理或缓存结果，减少重复执行",
                })

        logger.info(f"🌙 Dreaming: 检测到 {len(workflows)} 个冗余工作流")
        return workflows

    def detect_knowledge_gaps(self, tasks: List[Dict]) -> List[Dict[str, Any]]:
        """检测长期依赖外部查询的知识缺口"""
        # 简化实现：检测频繁调用搜索工具的情况
        gaps = []

        # 这里可以分析工具调用日志，检测频繁搜索的主题
        # 简化版本：检测任务报告中频繁出现"搜索"关键词
        search_count = 0
        for task in tasks:
            if task.get("type") == "task_report":
                try:
                    with open(task.get("filepath", ""), 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "搜索" in content or "search" in content.lower():
                            search_count += 1
                except Exception:
                    pass

        if search_count >= 3:
            gaps.append({
                "type": "knowledge_gap",
                "description": "频繁依赖外部搜索，考虑将常用知识存入记忆库",
                "occurrences": search_count,
                "suggestion": "将高频查询的知识存入 memory/skills.json，减少外部依赖",
            })

        logger.info(f"🌙 Dreaming: 检测到 {len(gaps)} 个知识缺口")
        return gaps

    async def run_dreaming_cycle(self, days: int = 7) -> Dict[str, Any]:
        """运行一次完整的 Dreaming 复盘周期"""
        logger.info("🌙 开始 Dreaming 异步复盘周期...")
        start_time = time.time()

        # 1. 扫描历史任务
        tasks = self.scan_history_tasks(days=days)

        # 2. 检测三类隐性问题
        failure_patterns = self.detect_failure_patterns(tasks)
        redundant_workflows = self.detect_redundant_workflows(tasks)
        knowledge_gaps = self.detect_knowledge_gaps(tasks)

        # 3. 生成优化建议
        suggestions = []
        for pattern in failure_patterns:
            suggestions.append({
                "category": "failure_pattern",
                "priority": pattern["severity"],
                "title": f"反复失败: {pattern['error_type']} ({pattern['occurrences']}次)",
                "suggestion": pattern["suggestion"],
            })

        for workflow in redundant_workflows:
            suggestions.append({
                "category": "redundant_workflow",
                "priority": "medium",
                "title": f"冗余工作流: {workflow['task_type']} ({workflow['occurrences']}次)",
                "suggestion": workflow["suggestion"],
            })

        for gap in knowledge_gaps:
            suggestions.append({
                "category": "knowledge_gap",
                "priority": "low",
                "title": gap["description"],
                "suggestion": gap["suggestion"],
            })

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))

        # 4. 生成报告
        report = {
            "dreaming_time": datetime.now().isoformat(),
            "scan_days": days,
            "tasks_scanned": len(tasks),
            "findings": {
                "failure_patterns": len(failure_patterns),
                "redundant_workflows": len(redundant_workflows),
                "knowledge_gaps": len(knowledge_gaps),
            },
            "suggestions": suggestions,
            "duration_seconds": round(time.time() - start_time, 2),
            "status": "pending_review",  # 待人工审核
        }

        # 5. 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"dreaming_report_{timestamp}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"🌙 Dreaming 复盘完成: {len(suggestions)} 条建议，保存到 {report_file}")
        return report

    def print_report(self, report: Dict):
        """打印 Dreaming 报告"""
        print("\n" + "🌙" * 30)
        print("Dreaming 异步复盘报告")
        print("🌙" * 30)
        print(f"复盘时间: {report['dreaming_time']}")
        print(f"扫描天数: {report['scan_days']}天")
        print(f"扫描任务数: {report['tasks_scanned']}")
        print(f"耗时: {report['duration_seconds']}秒")
        print("-" * 60)
        print("🔍 发现:")
        print(f"  反复失败模式: {report['findings']['failure_patterns']} 个")
        print(f"  冗余工作流: {report['findings']['redundant_workflows']} 个")
        print(f"  知识缺口: {report['findings']['knowledge_gaps']} 个")
        print("-" * 60)
        print("💡 优化建议（按优先级排序）:")
        for i, suggestion in enumerate(report['suggestions'], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(suggestion['priority'], "⚪")
            print(f"  {i}. {priority_icon} [{suggestion['priority']}] {suggestion['title']}")
            print(f"     建议: {suggestion['suggestion']}")
        print("🌙" * 30 + "\n")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dreaming 异步复盘模块")
    parser.add_argument("--scan", action="store_true", help="运行一次复盘扫描")
    parser.add_argument("--report", action="store_true", help="查看最近的复盘报告")
    parser.add_argument("--days", type=int, default=7, help="扫描天数（默认7天）")
    parser.add_argument("--daemon", action="store_true", help="后台守护进程模式（每24小时运行一次）")
    args = parser.parse_args()

    analyzer = DreamingAnalyzer()

    if args.scan:
        report = await analyzer.run_dreaming_cycle(days=args.days)
        analyzer.print_report(report)
    elif args.report:
        # 查看最近的报告
        reports = sorted([f for f in os.listdir(analyzer.output_dir) if f.startswith("dreaming_report_")])
        if reports:
            latest = os.path.join(analyzer.output_dir, reports[-1])
            with open(latest, 'r', encoding='utf-8') as f:
                report = json.load(f)
            analyzer.print_report(report)
        else:
            print("暂无复盘报告，请先运行 --scan")
    elif args.daemon:
        logger.info("🌙 Dreaming 守护进程启动（每24小时运行一次）")
        while True:
            try:
                report = await analyzer.run_dreaming_cycle(days=7)
                analyzer.print_report(report)
            except Exception as e:
                logger.error(f"Dreaming 复盘异常: {e}")
            await asyncio.sleep(86400)  # 24小时
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
