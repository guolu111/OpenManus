"""
MultiRoleOrchestrator - 多角色协同调度器

支持：
1. 串行调度（A卡→B卡→C卡流水线）
2. 并行调度（多卡同时执行独立子任务）
3. 中层指挥官（内容创作军/数据分析军/系统运维军）
4. 世界书动态更新（通气公告/决议台账）

使用方式：
    from app.role_cards import MultiRoleOrchestrator

    orchestrator = MultiRoleOrchestrator(role_cards_dir)

    # 串行调度
    result = await orchestrator.run_serial(
        task="分析这段文本并生成摘要",
        roles=["分析", "生成"],
        pass_output=True  # 前一个角色的输出作为后一个的输入
    )

    # 并行调度
    results = await orchestrator.run_parallel(
        subtasks=[
            {"role": "分析", "task": "分析文本结构"},
            {"role": "匹配", "task": "计算相似度"},
        ]
    )

    # 指挥官调度
    result = await orchestrator.run_with_commander(
        commander="数据分析军",
        task="分析客户数据并生成报告"
    )
"""

import asyncio
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.logger import logger
from app.role_cards.role_orchestrator import RoleOrchestrator
from app.role_cards.role_card import RoleCard


@dataclass
class SubTask:
    """子任务"""
    role: str              # 角色卡名称
    task: str              # 任务描述
    depends_on: List[int] = field(default_factory=list)  # 依赖的子任务索引
    timeout: int = 300     # 超时时间（秒）


@dataclass
class SubTaskResult:
    """子任务结果"""
    subtask_index: int     # 子任务索引
    role: str              # 角色卡名称
    task: str              # 任务描述
    result: str = ""       # 执行结果
    success: bool = False  # 是否成功
    error: str = ""        # 错误信息
    duration: float = 0.0  # 执行时长（秒）
    started_at: Optional[datetime] = None  # 开始时间
    finished_at: Optional[datetime] = None  # 结束时间


@dataclass
class Commander:
    """中层指挥官"""
    name: str                    # 指挥官名称
    display_name: str            # 显示名称
    description: str             # 描述
    roles: List[str]             # 管辖的角色卡列表
    preferred_workflow: str = "serial"  # 偏好的工作流（serial/parallel/hybrid）


# 预定义的指挥官配置
COMMANDERS: Dict[str, Commander] = {
    "内容创作军": Commander(
        name="内容创作军",
        display_name="内容创作指挥官",
        description="负责内容生成、风格模仿、教学讲解等创作类任务",
        roles=["生成", "老师", "学生"],
        preferred_workflow="serial"
    ),
    "数据分析军": Commander(
        name="数据分析军",
        display_name="数据分析指挥官",
        description="负责文本分析、相似度匹配、数据处理等分析类任务",
        roles=["分析", "匹配"],
        preferred_workflow="parallel"
    ),
    "系统运维军": Commander(
        name="系统运维军",
        display_name="系统运维指挥官",
        description="负责脚本管理、API调用、跑批任务、文件夹管理等运维类任务",
        roles=["脚本", "小助手", "每天更新", "文件夹管理员"],
        preferred_workflow="hybrid"
    ),
}


class MultiRoleOrchestrator:
    """
    多角色协同调度器

    支持串行调度、并行调度、指挥官调度。
    """

    def __init__(self, role_cards_dir: str):
        """
        初始化多角色协同调度器

        Args:
            role_cards_dir: 角色卡目录路径
        """
        self.role_orchestrator = RoleOrchestrator(role_cards_dir)
        self.commanders = COMMANDERS.copy()
        self.world_book: Dict[str, Any] = {
            "通气公告": [],
            "决议台账": [],
            "通用规则": [],
            "执行历史": [],
        }
        logger.info("多角色协同调度器初始化完成")

    def list_commanders(self) -> List[Dict]:
        """列出所有指挥官"""
        return [
            {
                "name": c.name,
                "display_name": c.display_name,
                "description": c.description,
                "roles": c.roles,
                "preferred_workflow": c.preferred_workflow,
            }
            for c in self.commanders.values()
        ]

    def get_commander(self, name: str) -> Optional[Commander]:
        """获取指定指挥官"""
        return self.commanders.get(name)

    async def run_serial(
        self,
        task: str,
        roles: List[str],
        pass_output: bool = True,
        agent: Any = None,
    ) -> Dict[str, Any]:
        """
        串行调度（A卡→B卡→C卡流水线）

        Args:
            task: 总任务描述
            roles: 角色卡列表（按执行顺序）
            pass_output: 是否将前一个角色的输出作为后一个的输入
            agent: Agent对象（用于实际执行，None时只做模拟）

        Returns:
            调度结果，包含每个角色的执行结果和最终汇总
        """
        logger.info(f"串行调度开始: {task[:50]}...，角色序列: {' → '.join(roles)}")

        results: List[SubTaskResult] = []
        current_input = task
        overall_start = datetime.now()

        for i, role_name in enumerate(roles):
            subtask = SubTask(
                role=role_name,
                task=current_input if pass_output else task,
            )
            result = await self._execute_subtask(subtask, i, agent)
            results.append(result)

            if pass_output and result.success:
                current_input = f"【前置任务{role_name}的输出】\n{result.result}\n\n【当前任务】\n{task}"

            if not result.success:
                logger.warning(f"串行调度中断: 角色 {role_name} 执行失败")
                break

        overall_duration = (datetime.now() - overall_start).total_seconds()
        all_success = all(r.success for r in results)
        final_result = results[-1].result if results and results[-1].success else ""

        # 记录到世界书
        self._record_to_world_book("串行调度", task, roles, results, all_success)

        return {
            "mode": "serial",
            "task": task,
            "roles": roles,
            "results": [self._result_to_dict(r) for r in results],
            "all_success": all_success,
            "final_result": final_result,
            "total_duration": overall_duration,
        }

    async def run_parallel(
        self,
        subtasks: List[Dict[str, Any]],
        agent: Any = None,
    ) -> Dict[str, Any]:
        """
        并行调度（多卡同时执行独立子任务）

        Args:
            subtasks: 子任务列表，每个包含 role 和 task
            agent: Agent对象（用于实际执行，None时只做模拟）

        Returns:
            调度结果，包含每个子任务的执行结果
        """
        logger.info(f"并行调度开始: {len(subtasks)}个子任务")

        overall_start = datetime.now()

        # 创建子任务对象
        task_objects = []
        for i, st in enumerate(subtasks):
            task_objects.append(SubTask(
                role=st.get("role", "生成"),
                task=st.get("task", ""),
                depends_on=st.get("depends_on", []),
                timeout=st.get("timeout", 300),
            ))

        # 并行执行（注意：实际执行需要agent支持异步，这里用asyncio.gather模拟）
        results = await asyncio.gather(*[
            self._execute_subtask(st, i, agent)
            for i, st in enumerate(task_objects)
        ])

        overall_duration = (datetime.now() - overall_start).total_seconds()
        all_success = all(r.success for r in results)

        # 记录到世界书
        roles = [st.role for st in task_objects]
        self._record_to_world_book("并行调度", f"{len(subtasks)}个子任务", roles, results, all_success)

        return {
            "mode": "parallel",
            "subtasks_count": len(subtasks),
            "results": [self._result_to_dict(r) for r in results],
            "all_success": all_success,
            "total_duration": overall_duration,
        }

    async def run_with_commander(
        self,
        commander_name: str,
        task: str,
        agent: Any = None,
    ) -> Dict[str, Any]:
        """
        指挥官调度（由中层指挥官分解任务并调度下属角色）

        Args:
            commander_name: 指挥官名称
            task: 任务描述
            agent: Agent对象

        Returns:
            调度结果
        """
        commander = self.get_commander(commander_name)
        if not commander:
            return {
                "error": f"指挥官 {commander_name} 不存在",
                "available_commanders": self.list_commanders(),
            }

        logger.info(f"指挥官调度开始: {commander_name}，任务: {task[:50]}...")

        # 根据指挥官偏好的工作流调度
        if commander.preferred_workflow == "serial":
            # 串行：按角色列表顺序执行
            return await self.run_serial(task, commander.roles, pass_output=True, agent=agent)
        elif commander.preferred_workflow == "parallel":
            # 并行：为每个角色创建独立子任务
            subtasks = [
                {"role": role, "task": f"【{commander_name}】{task}"}
                for role in commander.roles
            ]
            return await self.run_parallel(subtasks, agent=agent)
        else:
            # 混合：先并行分析，再串行汇总
            # 第一阶段：并行执行前半部分角色
            mid = len(commander.roles) // 2
            first_half = commander.roles[:max(1, mid)]
            subtasks = [
                {"role": role, "task": f"【{commander_name}第一阶段】{task}"}
                for role in first_half
            ]
            first_result = await self.run_parallel(subtasks, agent=agent)

            # 第二阶段：串行执行后半部分角色（汇总）
            second_half = commander.roles[max(1, mid):]
            if second_half:
                combined_input = f"【{commander_name}第一阶段结果】\n" + \
                    "\n".join([f"- {r['role']}: {r['result'][:100]}..." for r in first_result.get("results", [])]) + \
                    f"\n\n【原始任务】\n{task}"
                second_result = await self.run_serial(combined_input, second_half, pass_output=True, agent=agent)
                return {
                    "mode": "hybrid",
                    "commander": commander_name,
                    "first_phase": first_result,
                    "second_phase": second_result,
                    "final_result": second_result.get("final_result", ""),
                }
            return first_result

    async def _execute_subtask(
        self,
        subtask: SubTask,
        index: int,
        agent: Any = None,
    ) -> SubTaskResult:
        """
        执行单个子任务

        Args:
            subtask: 子任务
            index: 子任务索引
            agent: Agent对象

        Returns:
            子任务结果
        """
        result = SubTaskResult(
            subtask_index=index,
            role=subtask.role,
            task=subtask.task,
            started_at=datetime.now(),
        )

        try:
            if agent is None:
                # 模拟执行（没有实际agent时）
                logger.info(f"[模拟执行] 角色 {subtask.role}: {subtask.task[:50]}...")
                result.result = f"【模拟执行结果】角色 {subtask.role} 已完成任务: {subtask.task[:50]}..."
                result.success = True
            else:
                # 实际执行（需要agent支持run_with_role方法）
                if hasattr(agent, 'run_with_role'):
                    output = await agent.run_with_role(subtask.role, subtask.task)
                    result.result = str(output)
                    result.success = True
                else:
                    raise ValueError("Agent不支持run_with_role方法")

        except Exception as e:
            result.error = str(e)
            result.success = False
            logger.error(f"子任务执行失败: 角色 {subtask.role}, 错误: {e}")

        result.finished_at = datetime.now()
        result.duration = (result.finished_at - result.started_at).total_seconds()
        return result

    def _result_to_dict(self, result: SubTaskResult) -> Dict:
        """将子任务结果转为字典"""
        return {
            "subtask_index": result.subtask_index,
            "role": result.role,
            "task": result.task,
            "result": result.result,
            "success": result.success,
            "error": result.error,
            "duration": result.duration,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "finished_at": result.finished_at.isoformat() if result.finished_at else None,
        }

    def _record_to_world_book(
        self,
        mode: str,
        task: str,
        roles: List[str],
        results: List[SubTaskResult],
        success: bool,
    ):
        """记录到世界书"""
        record = {
            "时间": datetime.now().isoformat(),
            "模式": mode,
            "任务": task,
            "角色": roles,
            "成功": success,
            "结果摘要": [
                {"角色": r.role, "成功": r.success, "时长": r.duration}
                for r in results
            ],
        }
        self.world_book["执行历史"].append(record)

        # 如果成功，添加到通气公告
        if success:
            self.world_book["通气公告"].append({
                "时间": datetime.now().isoformat(),
                "内容": f"{mode}成功完成: {task[:50]}...",
                "角色": roles,
            })

    def get_world_book(self) -> Dict:
        """获取世界书内容"""
        return self.world_book.copy()

    def add_resolution(self, content: str, roles: List[str] = None):
        """添加决议到决议台账"""
        self.world_book["决议台账"].append({
            "时间": datetime.now().isoformat(),
            "内容": content,
            "相关角色": roles or [],
        })
        logger.info(f"决议已添加到台账: {content[:50]}...")

    def status(self) -> str:
        """获取调度器状态"""
        lines = [
            "=== 多角色协同调度器状态 ===",
            f"指挥官数量: {len(self.commanders)}",
            f"世界书记录: 通气公告 {len(self.world_book['通气公告'])} 条, "
            f"决议台账 {len(self.world_book['决议台账'])} 条, "
            f"执行历史 {len(self.world_book['执行历史'])} 条",
            "",
            "可用指挥官:",
        ]
        for c in self.commanders.values():
            lines.append(f"  - {c.name} ({c.display_name})")
            lines.append(f"    管辖角色: {', '.join(c.roles)}")
            lines.append(f"    偏好工作流: {c.preferred_workflow}")
        return "\n".join(lines)
