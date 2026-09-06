# -*- coding: utf-8 -*-
"""
event_bus.py · 轻量事件总线
==============================
P0核心稳定性 - 改造为事件驱动架构，兼容原有同步调用模式

设计原则（来自豆包架构分析建议）：
- 任务启动、角色切换、异常报错、执行完成全部抛出事件
- 驱动看板更新、日志采集、告警触发
- 适配实时日志驱动调试法
- 兼容原有同步调用模式，不破坏现有代码

事件类型：
- TaskSubmitted: 任务已提交
- TaskStart: 任务开始执行
- TaskProgress: 任务进度更新
- TaskDone: 任务完成
- TaskFailed: 任务失败
- TaskCancelled: 任务取消
- RoleActivate: 角色激活
- RoleDeactivate: 角色取消激活
- ErrorOccur: 错误发生
- AlertTrigger: 告警触发
- LogEvent: 日志事件
"""
import asyncio
import time
import json
from typing import Callable, Awaitable, Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class EventType(str, Enum):
    """事件类型枚举"""
    # 任务相关
    TASK_SUBMITTED = "task_submitted"
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_DONE = "task_done"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    
    # 角色相关
    ROLE_ACTIVATE = "role_activate"
    ROLE_DEACTIVATE = "role_deactivate"
    
    # 错误和告警
    ERROR_OCCUR = "error_occur"
    ALERT_TRIGGER = "alert_trigger"
    
    # 日志
    LOG_EVENT = "log_event"
    
    # 自定义
    CUSTOM = "custom"


@dataclass
class Event:
    """事件数据类"""
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    task_id: Optional[str] = None
    role_name: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        d = asdict(self)
        d["event_type"] = self.event_type.value
        d["datetime"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return d
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# 事件处理器类型
EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """轻量事件总线（单例模式）
    
    支持同步和异步两种模式：
    - 同步模式：事件立即分发给所有订阅者，兼容原有同步调用
    - 异步模式：事件放入队列，由后台worker异步分发（不阻塞主流程）
    
    设计原则：
    - 不破坏现有代码，原有同步调用模式完全兼容
    - 事件分发失败不影响主流程（只记录日志）
    - 支持通配符订阅（如 "task_*" 订阅所有任务事件）
    """
    
    _instance: Optional["EventBus"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, async_mode: bool = False, max_queue_size: int = 10000):
        """初始化事件总线
        
        Args:
            async_mode: 是否启用异步模式（默认False，兼容原有同步调用）
            max_queue_size: 异步模式下的最大队列大小
        """
        if self._initialized:
            return
        self._initialized = True
        
        self.async_mode = async_mode
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._event_queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        
        if async_mode:
            self._event_queue = asyncio.Queue(maxsize=max_queue_size)
            self._start_worker()
        
        print(f"  [EventBus] 初始化完成，模式: {'异步' if async_mode else '同步'}")
    
    @classmethod
    def get_instance(cls) -> "EventBus":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _start_worker(self):
        """启动异步分发worker"""
        if self._worker_task is None or self._worker_task.done():
            self._running = True
            self._worker_task = asyncio.create_task(self._dispatch_worker())
            print("  [EventBus] 异步分发worker已启动")
    
    async def _dispatch_worker(self):
        """异步分发worker（后台运行）"""
        while self._running:
            try:
                event = await self._event_queue.get()
                await self._dispatch(event)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"  [EventBus] ⚠️ 分发worker异常: {str(e)[:50]}")
                await asyncio.sleep(0.1)
    
    def subscribe(self, event_type: str, handler: EventHandler):
        """订阅事件
        
        Args:
            event_type: 事件类型，支持通配符（如 "task_*"）
            handler: 事件处理器（异步函数）
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        print(f"  [EventBus] ✓ 订阅: {event_type} (当前{len(self._subscribers[event_type])}个订阅者)")
    
    def unsubscribe(self, event_type: str, handler: EventHandler):
        """取消订阅"""
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                print(f"  [EventBus] ✓ 取消订阅: {event_type}")
    
    async def publish(self, event: Event):
        """发布事件
        
        Args:
            event: 事件对象
        """
        # 记录历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        if self.async_mode and self._event_queue is not None:
            # 异步模式：放入队列，不阻塞主流程
            try:
                self._event_queue.put_nowait(event)
            except asyncio.QueueFull:
                print(f"  [EventBus] ⚠️ 事件队列已满，丢弃事件: {event.event_type.value}")
        else:
            # 同步模式：立即分发（兼容原有同步调用）
            await self._dispatch(event)
    
    async def _dispatch(self, event: Event):
        """分发事件给所有订阅者
        
        事件分发失败不影响主流程（只记录日志）。
        """
        event_type_str = event.event_type.value
        
        # 找到所有匹配的订阅者（精确匹配 + 通配符匹配）
        matched_handlers = []
        for pattern, handlers in self._subscribers.items():
            if pattern == event_type_str:
                matched_handlers.extend(handlers)
            elif pattern.endswith("*") and event_type_str.startswith(pattern[:-1]):
                matched_handlers.extend(handlers)
        
        for handler in matched_handlers:
            try:
                await handler(event)
            except Exception as e:
                # 事件分发失败不影响主流程
                print(f"  [EventBus] ⚠️ 事件处理器异常: {str(e)[:50]}")
    
    async def publish_simple(self, event_type: EventType, message: str = "", 
                              task_id: str = None, role_name: str = None, 
                              data: Dict[str, Any] = None):
        """便捷方法：发布简单事件
        
        Args:
            event_type: 事件类型
            message: 消息
            task_id: 任务ID
            role_name: 角色名称
            data: 附加数据
        """
        event = Event(
            event_type=event_type,
            task_id=task_id,
            role_name=role_name,
            data=data or {},
            message=message,
        )
        await self.publish(event)
    
    def get_event_history(self, event_type: EventType = None, limit: int = 100) -> List[Event]:
        """获取事件历史（用于调试和监控）
        
        Args:
            event_type: 事件类型过滤（None表示所有）
            limit: 返回数量限制
        """
        if event_type is None:
            return self._event_history[-limit:]
        return [e for e in self._event_history if e.event_type == event_type][-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取事件总线统计信息"""
        return {
            "async_mode": self.async_mode,
            "subscribers_count": {k: len(v) for k, v in self._subscribers.items()},
            "event_history_count": len(self._event_history),
            "queue_size": self._event_queue.qsize() if self._event_queue else 0,
            "worker_running": self._running,
        }
    
    async def shutdown(self):
        """关闭事件总线（应用退出时调用）"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        print("  [EventBus] 已关闭")


# 全局便捷函数
def init_event_bus(async_mode: bool = False) -> EventBus:
    """初始化全局事件总线（应用启动时调用）"""
    return EventBus(async_mode=async_mode)


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return EventBus.get_instance()


async def publish_event(event_type: EventType, message: str = "", **kwargs):
    """便捷函数：发布全局事件"""
    bus = get_event_bus()
    await bus.publish_simple(event_type, message=message, **kwargs)
