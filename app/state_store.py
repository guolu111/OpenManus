# -*- coding: utf-8 -*-
"""
state_store.py · 全局统一状态中心
====================================
P0核心稳定性 - 消除状态孤岛，集中持久保存所有状态

设计原则（来自豆包架构分析建议）：
- 集中持久保存任务元数据、角色运行快照、执行历史、告警标签
- TaskDashboard、RoleOrchestrator、LogMonitor全部读写同一个状态数据源
- 跑完任务自动打包运行记录，写入经验包目录
- 任务失败时可一键汇总「任务信息 + 角色快照 + 完整运行日志」

状态分类：
- tasks: 任务状态（pending/running/completed/failed/cancelled）
- roles: 角色状态（active/inactive，当前激活的角色卡）
- alerts: 告警状态（active/acknowledged/resolved）
- logs: 日志索引（按任务和时间索引）
- snapshots: 运行快照（任务执行过程中的关键状态快照）
"""
import json
import time
import asyncio
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RoleStatus(str, Enum):
    """角色状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class AlertStatus(str, Enum):
    """告警状态枚举"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    role_name: Optional[str] = None
    command: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleState:
    """角色状态"""
    role_name: str
    status: RoleStatus = RoleStatus.INACTIVE
    activated_at: Optional[float] = None
    deactivated_at: Optional[float] = None
    current_task_id: Optional[str] = None
    permission_level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertState:
    """告警状态"""
    alert_id: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    alert_type: str = ""
    message: str = ""
    task_id: Optional[str] = None
    role_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSnapshot:
    """运行快照"""
    snapshot_id: str
    task_id: Optional[str] = None
    role_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    state: Dict[str, Any] = field(default_factory=dict)


class StateStore:
    """全局统一状态中心（单例模式）
    
    集中管理所有状态，消除状态孤岛。
    支持持久化到JSON文件，应用重启后可恢复状态。
    """
    
    _instance: Optional["StateStore"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, persist_dir: str = None, auto_persist: bool = True):
        """初始化状态中心
        
        Args:
            persist_dir: 持久化目录（None表示不持久化）
            auto_persist: 是否自动持久化（每次状态变更后自动保存）
        """
        if self._initialized:
            return
        self._initialized = True
        
        self.persist_dir = persist_dir
        self.auto_persist = auto_persist
        
        self.tasks: Dict[str, TaskState] = {}
        self.roles: Dict[str, RoleState] = {}
        self.alerts: Dict[str, AlertState] = {}
        self.snapshots: List[StateSnapshot] = []
        self.logs: Dict[str, List[Dict[str, Any]]] = {}  # task_id -> logs
        
        self._max_snapshots = 1000
        self._max_logs_per_task = 1000
        
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            self._load()
        
        print(f"  [StateStore] 初始化完成，持久化: {'是' if persist_dir else '否'}")
    
    @classmethod
    def get_instance(cls) -> "StateStore":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ===== 任务状态管理 =====
    
    async def create_task(self, task_id: str, command: str = "", priority: int = 0,
                          role_name: str = None, metadata: Dict[str, Any] = None) -> TaskState:
        """创建任务"""
        async with self._lock:
            task = TaskState(
                task_id=task_id,
                command=command,
                priority=priority,
                role_name=role_name,
                metadata=metadata or {},
            )
            self.tasks[task_id] = task
            if self.auto_persist:
                self._save()
            return task
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                  progress: float = None, error: str = None,
                                  result: Dict[str, Any] = None) -> Optional[TaskState]:
        """更新任务状态"""
        async with self._lock:
            if task_id not in self.tasks:
                return None
            task = self.tasks[task_id]
            task.status = status
            if progress is not None:
                task.progress = progress
            if error is not None:
                task.error = error
            if result is not None:
                task.result = result
            
            if status == TaskStatus.RUNNING and task.started_at is None:
                task.started_at = time.time()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.completed_at = time.time()
            
            if self.auto_persist:
                self._save()
            return task
    
    async def get_task(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    async def get_all_tasks(self, status: TaskStatus = None) -> List[TaskState]:
        """获取所有任务（可按状态过滤）"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    # ===== 角色状态管理 =====
    
    async def activate_role(self, role_name: str, permission_level: int = 0,
                            task_id: str = None, metadata: Dict[str, Any] = None) -> RoleState:
        """激活角色"""
        async with self._lock:
            role = RoleState(
                role_name=role_name,
                status=RoleStatus.ACTIVE,
                activated_at=time.time(),
                current_task_id=task_id,
                permission_level=permission_level,
                metadata=metadata or {},
            )
            self.roles[role_name] = role
            if self.auto_persist:
                self._save()
            return role
    
    async def deactivate_role(self, role_name: str) -> Optional[RoleState]:
        """取消激活角色"""
        async with self._lock:
            if role_name not in self.roles:
                return None
            role = self.roles[role_name]
            role.status = RoleStatus.INACTIVE
            role.deactivated_at = time.time()
            role.current_task_id = None
            if self.auto_persist:
                self._save()
            return role
    
    async def get_active_roles(self) -> List[RoleState]:
        """获取所有激活的角色"""
        return [r for r in self.roles.values() if r.status == RoleStatus.ACTIVE]
    
    # ===== 告警状态管理 =====
    
    async def create_alert(self, alert_id: str, alert_type: str, message: str,
                           task_id: str = None, role_name: str = None,
                           metadata: Dict[str, Any] = None) -> AlertState:
        """创建告警"""
        async with self._lock:
            alert = AlertState(
                alert_id=alert_id,
                alert_type=alert_type,
                message=message,
                task_id=task_id,
                role_name=role_name,
                metadata=metadata or {},
            )
            self.alerts[alert_id] = alert
            if self.auto_persist:
                self._save()
            return alert
    
    async def acknowledge_alert(self, alert_id: str) -> Optional[AlertState]:
        """确认告警"""
        async with self._lock:
            if alert_id not in self.alerts:
                return None
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            if self.auto_persist:
                self._save()
            return alert
    
    async def resolve_alert(self, alert_id: str) -> Optional[AlertState]:
        """解决告警"""
        async with self._lock:
            if alert_id not in self.alerts:
                return None
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            if self.auto_persist:
                self._save()
            return alert
    
    async def get_active_alerts(self) -> List[AlertState]:
        """获取所有活跃告警"""
        return [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
    
    # ===== 快照和日志管理 =====
    
    async def create_snapshot(self, task_id: str = None, role_name: str = None,
                              description: str = "", state: Dict[str, Any] = None) -> StateSnapshot:
        """创建运行快照"""
        async with self._lock:
            snapshot = StateSnapshot(
                snapshot_id=f"snap_{int(time.time() * 1000)}",
                task_id=task_id,
                role_name=role_name,
                description=description,
                state=state or {},
            )
            self.snapshots.append(snapshot)
            if len(self.snapshots) > self._max_snapshots:
                self.snapshots.pop(0)
            return snapshot
    
    async def add_log(self, task_id: str, log_entry: Dict[str, Any]):
        """添加日志条目"""
        async with self._lock:
            if task_id not in self.logs:
                self.logs[task_id] = []
            log_entry["timestamp"] = log_entry.get("timestamp", time.time())
            self.logs[task_id].append(log_entry)
            if len(self.logs[task_id]) > self._max_logs_per_task:
                self.logs[task_id].pop(0)
    
    async def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有日志"""
        return self.logs.get(task_id, [])
    
    # ===== 汇总和导出 =====
    
    async def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """获取任务完整汇总（任务信息 + 角色快照 + 完整运行日志）
        
        用于任务失败时一键汇总，方便调试和经验包蒸馏。
        """
        task = self.tasks.get(task_id)
        if not task:
            return {"error": f"任务 {task_id} 不存在"}
        
        role = None
        if task.role_name:
            role = self.roles.get(task.role_name)
        
        logs = self.logs.get(task_id, [])
        task_snapshots = [s for s in self.snapshots if s.task_id == task_id]
        task_alerts = [a for a in self.alerts.values() if a.task_id == task_id]
        
        return {
            "task": asdict(task) if task else None,
            "role": asdict(role) if role else None,
            "logs": logs,
            "snapshots": [asdict(s) for s in task_snapshots],
            "alerts": [asdict(a) for a in task_alerts],
            "summary": {
                "task_id": task_id,
                "status": task.status.value,
                "duration": (task.completed_at or time.time()) - task.created_at if task.created_at else 0,
                "log_count": len(logs),
                "snapshot_count": len(task_snapshots),
                "alert_count": len(task_alerts),
                "error": task.error,
            }
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取状态中心统计信息"""
        return {
            "tasks_total": len(self.tasks),
            "tasks_pending": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "tasks_running": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            "tasks_completed": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
            "tasks_failed": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
            "roles_active": len([r for r in self.roles.values() if r.status == RoleStatus.ACTIVE]),
            "alerts_active": len([a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]),
            "snapshots_total": len(self.snapshots),
            "logs_total": sum(len(logs) for logs in self.logs.values()),
        }
    
    # ===== 持久化 =====
    
    def _save(self):
        """保存状态到文件（内部方法，调用时应持有锁）"""
        if not self.persist_dir:
            return
        try:
            data = {
                "tasks": {k: asdict(v) for k, v in self.tasks.items()},
                "roles": {k: asdict(v) for k, v in self.roles.items()},
                "alerts": {k: asdict(v) for k, v in self.alerts.items()},
                "snapshots": [asdict(s) for s in self.snapshots[-100:]],  # 只保存最近100个快照
                "logs": {k: v[-100:] for k, v in self.logs.items()},  # 每个任务只保存最近100条日志
                "saved_at": time.time(),
            }
            filepath = os.path.join(self.persist_dir, "state_store.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [StateStore] ⚠️ 保存状态失败: {str(e)[:50]}")
    
    def _load(self):
        """从文件加载状态（内部方法）"""
        if not self.persist_dir:
            return
        try:
            filepath = os.path.join(self.persist_dir, "state_store.json")
            if not os.path.exists(filepath):
                return
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for task_id, task_data in data.get("tasks", {}).items():
                task_data["status"] = TaskStatus(task_data["status"])
                self.tasks[task_id] = TaskState(**task_data)
            
            for role_name, role_data in data.get("roles", {}).items():
                role_data["status"] = RoleStatus(role_data["status"])
                self.roles[role_name] = RoleState(**role_data)
            
            for alert_id, alert_data in data.get("alerts", {}).items():
                alert_data["status"] = AlertStatus(alert_data["status"])
                self.alerts[alert_id] = AlertState(**alert_data)
            
            for snap_data in data.get("snapshots", []):
                self.snapshots.append(StateSnapshot(**snap_data))
            
            for task_id, logs in data.get("logs", {}).items():
                self.logs[task_id] = logs
            
            print(f"  [StateStore] ✓ 状态已加载（{len(self.tasks)}个任务，{len(self.roles)}个角色，{len(self.alerts)}个告警）")
        except Exception as e:
            print(f"  [StateStore] ⚠️ 加载状态失败: {str(e)[:50]}")


# 全局便捷函数
def init_state_store(persist_dir: str = None) -> StateStore:
    """初始化全局状态中心（应用启动时调用）"""
    return StateStore(persist_dir=persist_dir)


def get_state_store() -> StateStore:
    """获取全局状态中心实例"""
    return StateStore.get_instance()
