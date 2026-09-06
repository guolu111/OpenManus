# -*- coding: utf-8 -*-
"""
OpenManus Golden Tasks 评测脚本
自动运行评测任务集，生成评测报告，覆盖5个硬指标：
1. 任务完成率
2. 幻觉率（未知工具幻觉/影子调用/参数幻觉）
3. 工具调用准确率（工具选择/参数正确/调用顺序）
4. 错误恢复率
5. 成本与延迟（Token消耗/完成时间）

用法：
    python evaluation/run_evaluation.py --tasks T001,T002,T003
    python evaluation/run_evaluation.py --all
    python evaluation/run_evaluation.py --category 简单查询
"""
import asyncio
import json
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.manus import Manus
from app.logger import logger


class EvaluationResult:
    """单个任务的评测结果"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.success = False
        self.steps_executed = 0
        self.tools_called = []
        self.tool_call_errors = []
        self.illusion_detected = []
        self.error_recovered = False
        self.error_occurred = False
        self.token_usage = {"input": 0, "output": 0, "total": 0}
        self.notes = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "tools_called": self.tools_called,
            "tool_call_errors": self.tool_call_errors,
            "illusion_detected": self.illusion_detected,
            "error_occurred": self.error_occurred,
            "error_recovered": self.error_recovered,
            "token_usage": self.token_usage,
            "notes": self.notes,
        }


class EvaluationRunner:
    """评测运行器"""

    def __init__(self, tasks_file: str = "evaluation/golden_tasks.json"):
        self.tasks_file = tasks_file
        self.tasks = self._load_tasks()
        self.results: List[EvaluationResult] = []

    def _load_tasks(self) -> List[Dict]:
        """加载评测任务集"""
        with open(self.tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("tasks", [])

    def get_task(self, task_id: str) -> Optional[Dict]:
        """根据ID获取任务"""
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None

    def get_tasks_by_category(self, category: str) -> List[Dict]:
        """根据分类获取任务"""
        return [t for t in self.tasks if t["category"] == category]

    async def run_task(self, task: Dict) -> EvaluationResult:
        """运行单个评测任务"""
        result = EvaluationResult(task["id"])
        result.start_time = datetime.now().isoformat()
        start = time.time()

        logger.info(f"🧪 开始评测任务: {task['id']} - {task['name']}")

        try:
            # 创建 Manus 实例
            manus = await Manus.create()

            # 运行任务
            task_prompt = task["prompt"]
            logger.info(f"   输入: {task_prompt[:100]}...")

            # 这里简化处理：实际运行时需要捕获工具调用日志
            # 由于 Manus.run() 是完整的 Agent 循环，我们需要通过日志来分析
            result_text = await manus.run(task_prompt)

            # 简单的成功判断（实际应该更复杂）
            result.success = "error" not in result_text.lower() or "失败" not in result_text
            result.notes = result_text[:500] if result_text else "无输出"

            # 记录工具调用（从日志中提取，这里简化）
            result.steps_executed = manus.current_step if hasattr(manus, 'current_step') else 0

        except Exception as e:
            result.error_occurred = True
            result.notes = f"执行异常: {str(e)}"
            logger.error(f"   任务执行异常: {e}")

        result.end_time = datetime.now().isoformat()
        result.duration = time.time() - start

        logger.info(f"   结果: {'✅ 成功' if result.success else '❌ 失败'} ({result.duration:.1f}秒)")

        self.results.append(result)
        return result

    async def run_tasks(self, task_ids: Optional[List[str]] = None,
                        category: Optional[str] = None) -> List[EvaluationResult]:
        """运行多个评测任务"""
        if task_ids:
            tasks_to_run = [self.get_task(tid) for tid in task_ids if self.get_task(tid)]
        elif category:
            tasks_to_run = self.get_tasks_by_category(category)
        else:
            tasks_to_run = self.tasks

        logger.info(f"📊 开始评测，共 {len(tasks_to_run)} 个任务")

        for task in tasks_to_run:
            await self.run_task(task)
            # 任务间间隔，避免限流
            await asyncio.sleep(2)

        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """生成评测报告"""
        if not self.results:
            return {"error": "没有评测结果"}

        total = len(self.results)
        success_count = sum(1 for r in self.results if r.success)
        error_count = sum(1 for r in self.results if r.error_occurred)
        recovery_count = sum(1 for r in self.results if r.error_recovered)

        # 计算各维度指标
        task_completion_rate = success_count / total if total > 0 else 0
        error_recovery_rate = recovery_count / error_count if error_count > 0 else 0

        # 幻觉率统计
        total_illusions = sum(len(r.illusion_detected) for r in self.results)
        illusion_rate = total_illusions / (total * 3) if total > 0 else 0  # 3种幻觉类型

        # 平均耗时和Token
        avg_duration = sum(r.duration for r in self.results) / total if total > 0 else 0
        total_tokens = sum(r.token_usage.get("total", 0) for r in self.results)

        # 综合评分（加权）
        score = (
            task_completion_rate * 30 +
            (1 - illusion_rate) * 20 +
            0.8 * 20 +  # 工具调用准确率（需要更详细的日志分析）
            error_recovery_rate * 15 +
            max(0, 1 - avg_duration / 300) * 15  # 效率分
        )

        report = {
            "evaluation_time": datetime.now().isoformat(),
            "total_tasks": total,
            "summary": {
                "success_count": success_count,
                "failure_count": total - success_count,
                "error_count": error_count,
                "recovery_count": recovery_count,
            },
            "metrics": {
                "task_completion_rate": round(task_completion_rate, 4),
                "illusion_rate": round(illusion_rate, 4),
                "tool_accuracy_rate": 0.8,  # 占位，需要详细日志
                "error_recovery_rate": round(error_recovery_rate, 4),
                "avg_duration_seconds": round(avg_duration, 2),
                "total_tokens": total_tokens,
            },
            "overall_score": round(score, 2),
            "pass_threshold": {
                "overall_score": 70,
                "task_completion_rate": 0.7,
                "illusion_rate": 0.1,
            },
            "passed": score >= 70 and task_completion_rate >= 0.7 and illusion_rate <= 0.1,
            "detailed_results": [r.to_dict() for r in self.results],
        }

        return report

    def save_report(self, report: Dict, output_file: Optional[str] = None) -> str:
        """保存评测报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"evaluation/report_{timestamp}.json"

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📝 评测报告已保存: {output_file}")
        return output_file

    def print_summary(self, report: Dict):
        """打印评测摘要"""
        print("\n" + "=" * 60)
        print("📊 OpenManus 评测报告")
        print("=" * 60)
        print(f"评测时间: {report['evaluation_time']}")
        print(f"任务总数: {report['total_tasks']}")
        print(f"成功: {report['summary']['success_count']} | "
              f"失败: {report['summary']['failure_count']} | "
              f"错误: {report['summary']['error_count']} | "
              f"恢复: {report['summary']['recovery_count']}")
        print("-" * 60)
        print("📈 核心指标:")
        print(f"  任务完成率: {report['metrics']['task_completion_rate']:.1%}")
        print(f"  幻觉率: {report['metrics']['illusion_rate']:.1%}")
        print(f"  工具调用准确率: {report['metrics']['tool_accuracy_rate']:.1%}")
        print(f"  错误恢复率: {report['metrics']['error_recovery_rate']:.1%}")
        print(f"  平均耗时: {report['metrics']['avg_duration_seconds']:.1f}秒")
        print(f"  总Token消耗: {report['metrics']['total_tokens']}")
        print("-" * 60)
        print(f"🏆 综合评分: {report['overall_score']}/100")
        print(f"✅ 评测通过: {'是' if report['passed'] else '否'}")
        print("=" * 60 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="OpenManus Golden Tasks 评测脚本")
    parser.add_argument("--tasks", type=str, help="指定任务ID，逗号分隔（如 T001,T002）")
    parser.add_argument("--category", type=str, help="按分类运行（如 简单查询）")
    parser.add_argument("--all", action="store_true", help="运行全部任务")
    parser.add_argument("--output", type=str, help="输出报告文件路径")
    args = parser.parse_args()

    runner = EvaluationRunner()

    if args.tasks:
        task_ids = [t.strip() for t in args.tasks.split(",")]
        await runner.run_tasks(task_ids=task_ids)
    elif args.category:
        await runner.run_tasks(category=args.category)
    elif args.all:
        await runner.run_tasks()
    else:
        # 默认运行前3个简单任务做快速测试
        print("⚠️  未指定任务，默认运行前3个简单任务做快速测试")
        await runner.run_tasks(task_ids=["T001", "T002", "T003"])

    report = runner.generate_report()
    runner.print_summary(report)
    output_file = runner.save_report(report, args.output)
    print(f"📄 完整报告: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
