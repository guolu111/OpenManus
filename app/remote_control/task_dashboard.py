"""
TaskDashboard - 任务看板

功能：
1. 实时监控任务状态（待执行/执行中/已完成/失败）
2. 任务队列管理
3. 任务进度追踪
4. 任务历史记录
5. 生成状态报告

使用方式：
    from app.remote_control import TaskDashboard

    dashboard = TaskDashboard()

    # 添加任务
    task_id = dashboard.add_task("分析文本", "分析", priority=1)

    # 更新任务状态
    dashboard.update_task(task_id, status="running", progress=50)

    # 完成任务
    dashboard.complete_task(task_id, result="分析完成")

    # 获取状态报告
    report = dashboard.get_status_report()
"""

import json
import os
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from app.logger import logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """任务"""
    task_id: str                          # 任务ID
    name: str                             # 任务名称
    description: str                      # 任务描述
    role: str                             # 分配的角色
    status: TaskStatus = TaskStatus.PENDING  # 状态
    priority: TaskPriority = TaskPriority.MEDIUM  # 优先级
    progress: int = 0                    # 进度（0-100）
    result: str = ""                     # 执行结果
    error: str = ""                      # 错误信息
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    started_at: Optional[datetime] = None  # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间
    duration: float = 0.0                # 执行时长（秒）
    retries: int = 0                     # 重试次数
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


class TaskDashboard:
    """
    任务看板

    实时监控任务状态，管理任务队列。
    """

    def __init__(self, state_file: str = "task_dashboard_state.json"):
        """
        初始化任务看板

        Args:
            state_file: 状态文件路径（用于持久化）
        """
        self.state_file = state_file
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []  # 按优先级排序的任务ID队列
        self._lock = threading.Lock()

        # 加载历史状态
        self._load_state()

        logger.info("任务看板初始化完成")

    def _load_state(self):
        """从文件加载状态"""
        if not os.path.exists(self.state_file):
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for task_data in data.get("tasks", []):
                task = Task(
                    task_id=task_data["task_id"],
                    name=task_data["name"],
                    description=task_data["description"],
                    role=task_data["role"],
                    status=TaskStatus(task_data["status"]),
                    priority=TaskPriority(task_data["priority"]),
                    progress=task_data.get("progress", 0),
                    result=task_data.get("result", ""),
                    error=task_data.get("error", ""),
                    created_at=datetime.fromisoformat(task_data["created_at"]),
                    started_at=datetime.fromisoformat(task_data["started_at"]) if task_data.get("started_at") else None,
                    completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None,
                    duration=task_data.get("duration", 0.0),
                    retries=task_data.get("retries", 0),
                    metadata=task_data.get("metadata", {}),
                )
                self.tasks[task.task_id] = task

            self.task_queue = data.get("task_queue", [])
            logger.info(f"从文件加载了 {len(self.tasks)} 个任务")

        except Exception as e:
            logger.error(f"加载状态文件失败: {e}")

    def _save_state(self):
        """保存状态到文件"""
        try:
            data = {
                "tasks": [],
                "task_queue": self.task_queue,
                "saved_at": datetime.now().isoformat(),
            }

            for task in self.tasks.values():
                task_dict = asdict(task)
                task_dict["status"] = task.status.value
                task_dict["priority"] = task.priority.value
                task_dict["created_at"] = task.created_at.isoformat()
                task_dict["started_at"] = task.started_at.isoformat() if task.started_at else None
                task_dict["completed_at"] = task.completed_at.isoformat() if task.completed_at else None
                data["tasks"].append(task_dict)

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    def add_task(
        self,
        name: str,
        role: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加任务

        Args:
            name: 任务名称
            role: 分配的角色
            description: 任务描述
            priority: 优先级
            metadata: 元数据

        Returns:
            任务ID
        """
        with self._lock:
            task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.tasks)}"

            task = Task(
                task_id=task_id,
                name=name,
                description=description,
                role=role,
                priority=priority,
                metadata=metadata or {},
            )

            self.tasks[task_id] = task

            # 按优先级插入队列
            self._insert_to_queue(task_id, priority)

            self._save_state()
            logger.info(f"任务添加: {task_id} - {name} (角色: {role}, 优先级: {priority.name})")

            return task_id

    def _insert_to_queue(self, task_id: str, priority: TaskPriority):
        """按优先级插入到队列"""
        insert_pos = 0
        for i, existing_id in enumerate(self.task_queue):
            existing_task = self.tasks.get(existing_id)
            if existing_task and existing_task.priority.value >= priority.value:
                insert_pos = i + 1
            else:
                break
        self.task_queue.insert(insert_pos, task_id)

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待执行的任务"""
        with self._lock:
            for task_id in self.task_queue:
                task = self.tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    return task
            return None

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 新进度
            result: 结果
            error: 错误信息
            metadata: 元数据更新

        Returns:
            是否更新成功
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False

            if status is not None:
                task.status = status
                if status == TaskStatus.RUNNING and not task.started_at:
                    task.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()
                    if task.started_at:
                        task.duration = (task.completed_at - task.started_at).total_seconds()

            if progress is not None:
                task.progress = max(0, min(100, progress))

            if result is not None:
                task.result = result

            if error is not None:
                task.error = error

            if metadata is not None:
                task.metadata.update(metadata)

            self._save_state()
            logger.info(f"任务更新: {task_id} - 状态: {task.status.value}, 进度: {task.progress}%")
            return True

    def complete_task(self, task_id: str, result: str = "") -> bool:
        """完成任务"""
        return self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            result=result,
        )

    def fail_task(self, task_id: str, error: str = "") -> bool:
        """任务失败"""
        return self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=error,
        )

    def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.PENDING
            task.progress = 0
            task.error = ""
            task.retries += 1
            task.started_at = None
            task.completed_at = None

            # 重新加入队列
            if task_id not in self.task_queue:
                self._insert_to_queue(task_id, task.priority)

            self._save_state()
            logger.info(f"任务重试: {task_id} (第{task.retries}次)")
            return True

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.update_task(task_id, status=TaskStatus.CANCELLED)

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务列表"""
        return [t for t in self.tasks.values() if t.status == status]

    def get_tasks_by_role(self, role: str) -> List[Task]:
        """按角色获取任务列表"""
        return [t for t in self.tasks.values() if t.role == role]

    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        total = len(self.tasks)
        pending = len(self.get_tasks_by_status(TaskStatus.PENDING))
        running = len(self.get_tasks_by_status(TaskStatus.RUNNING))
        completed = len(self.get_tasks_by_status(TaskStatus.COMPLETED))
        failed = len(self.get_tasks_by_status(TaskStatus.FAILED))
        cancelled = len(self.get_tasks_by_status(TaskStatus.CANCELLED))

        # 计算平均执行时长
        completed_tasks = self.get_tasks_by_status(TaskStatus.COMPLETED)
        avg_duration = sum(t.duration for t in completed_tasks) / len(completed_tasks) if completed_tasks else 0

        # 成功率
        success_rate = completed / (completed + failed) * 100 if (completed + failed) > 0 else 0

        return {
            "summary": {
                "total": total,
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "success_rate": round(success_rate, 1),
                "avg_duration": round(avg_duration, 2),
            },
            "queue_size": len(self.task_queue),
            "current_time": datetime.now().isoformat(),
        }

    def get_status_text(self) -> str:
        """获取状态文本（用于飞书消息）"""
        report = self.get_status_report()
        s = report["summary"]

        # 当前运行中的任务
        running_tasks = self.get_tasks_by_status(TaskStatus.RUNNING)
        running_text = ""
        if running_tasks:
            running_text = "\n\n🔄 正在执行:"
            for t in running_tasks[:3]:
                running_text += f"\n  - {t.name} ({t.role}) - {t.progress}%"

        # 待执行队列
        pending_tasks = self.get_tasks_by_status(TaskStatus.PENDING)
        pending_text = ""
        if pending_tasks:
            pending_text = f"\n\n📋 待执行: {len(pending_tasks)} 个任务"

        return f"""📊 任务看板状态

总计: {s['total']} 个任务
✅ 已完成: {s['completed']}
🔄 执行中: {s['running']}
⏳ 待执行: {s['pending']}
❌ 失败: {s['failed']}
🚫 已取消: {s['cancelled']}

📈 成功率: {s['success_rate']}%
⏱️ 平均时长: {s['avg_duration']}秒
{running_text}{pending_text}
"""

    def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """获取最近的任务"""
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return sorted_tasks[:limit]

    def clear_completed(self, older_than_hours: int = 24) -> int:
        """清理已完成的任务"""
        with self._lock:
            now = datetime.now()
            to_remove = []

            for task_id, task in self.tasks.items():
                if task.status == TaskStatus.COMPLETED and task.completed_at:
                    age = (now - task.completed_at).total_seconds() / 3600
                    if age > older_than_hours:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]
                if task_id in self.task_queue:
                    self.task_queue.remove(task_id)

            self._save_state()
            logger.info(f"清理了 {len(to_remove)} 个已完成任务")
            return len(to_remove)

    def status(self) -> str:
        """获取看板状态"""
        report = self.get_status_report()
        s = report["summary"]
        return f"""=== 任务看板状态 ===
总任务: {s['total']}
待执行: {s['pending']}
执行中: {s['running']}
已完成: {s['completed']}
失败: {s['failed']}
成功率: {s['success_rate']}%
队列大小: {report['queue_size']}
"""
