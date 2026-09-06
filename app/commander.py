# -*- coding: utf-8 -*-
"""
commander.py · 统一门面Commander统帅入口
============================================
P0核心稳定性 - 封装ManusWithRoles和MultiRoleOrchestrator，自动判断单角色/多角色路由

设计原则（来自豆包架构分析建议）：
- 不废弃ManusWithRoles、MultiRoleOrchestrator，由Commander作为唯一对外调用门面
- 自动判断单角色/多角色协同路由
- 统一入参格式、统一返回结构、统一提交任务到状态中心
- 飞书/本地脚本后续只对接Commander
- 兼容两种运行模式：同步阻塞（旧脚本兼容）/ 异步后台任务（飞书长流程）

Commander职责：
1. 接收标准化指令，解析任务类型（单角色/多角色集群）
2. 生成唯一task_id，写入StateStore，抛出TaskSubmitted事件
3. 判断任务类型：分发至ManusWithRoles / MultiRoleOrchestrator
4. 调度器激活角色、更新角色状态，抛出RoleActivated事件
5. 运行过程实时抛出日志、进度、异常事件，LogMonitor监听告警，TaskDashboard刷新看板
6. 任务完成抛出TaskFinished事件，ExperienceArchiver自动归档本次运行记录至经验包
7. 异步回调推送结果至飞书告警通道
"""
import asyncio
import time
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

# 导入核心模块（延迟导入，避免循环依赖）
# from app.agent.manus_with_roles import ManusWithRoles
# from app.role_cards.multi_role_orchestrator import MultiRoleOrchestrator
from app.event_bus import EventBus, EventType, Event, get_event_bus, publish_event
from app.state_store import StateStore, TaskStatus, get_state_store
from app.resource_manager import ResourceManager, get_resource_manager, setup_global_timeout


class TaskType(str, Enum):
    """任务类型枚举"""
    SINGLE_ROLE = "single_role"       # 单角色执行
    MULTI_ROLE = "multi_role"         # 多角色协同
    AUTO = "auto"                      # 自动判断


class RunMode(str, Enum):
    """运行模式枚举"""
    SYNC = "sync"          # 同步阻塞（旧脚本兼容）
    ASYNC = "async"        # 异步后台任务（飞书长流程）


@dataclass
class TaskMeta:
    """任务元数据"""
    task_id: str
    task_type: TaskType
    run_mode: RunMode
    command: str
    role_name: Optional[str] = None
    role_names: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: TaskStatus = TaskStatus.PENDING
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class CommanderResult:
    """Commander统一返回结构"""
    task_id: str
    status: TaskStatus
    task_type: TaskType
    run_mode: RunMode
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: float = 0.0
    role_used: Optional[str] = None
    roles_used: List[str] = field(default_factory=list)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class Commander:
    """统一门面Commander统帅入口（单例模式）
    
    作为唯一对外调用门面，自动判断单角色/多角色路由，
    统一入参格式、统一返回结构、统一提交任务到状态中心。
    
    设计原则：
    - 门面模式，不重写已有业务类，内部持有实例引用
    - 对外只有一套统一入参、一套统一返回结构
    - 兼容两种运行模式：同步阻塞（旧脚本兼容）/ 异步后台任务（飞书长流程）
    - 自动对接EventBus与StateStore，所有操作自动落状态、抛事件
    """
    
    _instance: Optional["Commander"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化Commander
        
        Args:
            config: 配置字典（可选）
        """
        if self._initialized:
            return
        self._initialized = True
        
        self.config = config or {}
        
        # 核心组件（延迟初始化，避免启动时加载过重）
        self._manus_with_roles = None
        self._multi_role_orchestrator = None
        
        # 全局组件
        self.event_bus = get_event_bus()
        self.state_store = get_state_store()
        self.resource_manager = get_resource_manager()
        
        # 异步任务注册表
        self._async_tasks: Dict[str, asyncio.Task] = {}
        
        print("  [Commander] 初始化完成，统一门面已就绪")
    
    @classmethod
    def get_instance(cls) -> "Commander":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _init_manus_with_roles(self):
        """延迟初始化ManusWithRoles"""
        if self._manus_with_roles is None:
            try:
                from app.agent.manus_with_roles import ManusWithRoles
                self._manus_with_roles = ManusWithRoles(config=self.config)
                print("  [Commander] ✓ ManusWithRoles已初始化")
            except Exception as e:
                print(f"  [Commander] ⚠️ ManusWithRoles初始化失败: {str(e)[:50]}")
                raise
        return self._manus_with_roles
    
    def _init_multi_role_orchestrator(self):
        """延迟初始化MultiRoleOrchestrator"""
        if self._multi_role_orchestrator is None:
            try:
                from app.role_cards.multi_role_orchestrator import MultiRoleOrchestrator
                self._multi_role_orchestrator = MultiRoleOrchestrator(config=self.config)
                print("  [Commander] ✓ MultiRoleOrchestrator已初始化")
            except Exception as e:
                print(f"  [Commander] ⚠️ MultiRoleOrchestrator初始化失败: {str(e)[:50]}")
                raise
        return self._multi_role_orchestrator
    
    def _generate_task_id(self) -> str:
        """生成唯一任务ID"""
        return f"task_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    def _detect_task_type(self, command: str, role_name: str = None, 
                           role_names: List[str] = None) -> TaskType:
        """自动判断任务类型
        
        判断规则：
        - 如果指定了多个角色（role_names长度>1），则为多角色协同
        - 如果指定了单个角色，则为单角色执行
        - 如果没有指定角色，根据命令内容判断（包含"协同"/"并行"/"多角色"等关键词则为多角色）
        """
        if role_names and len(role_names) > 1:
            return TaskType.MULTI_ROLE
        if role_name:
            return TaskType.SINGLE_ROLE
        
        # 根据命令内容判断
        multi_role_keywords = ["协同", "并行", "多角色", "多个角色", "同时", "分工", "流水线", "串行", "混合"]
        if any(kw in command for kw in multi_role_keywords):
            return TaskType.MULTI_ROLE
        
        return TaskType.SINGLE_ROLE
    
    async def submit_task(self, command: str, task_type: TaskType = TaskType.AUTO,
                          run_mode: RunMode = RunMode.SYNC,
                          role_name: str = None, role_names: List[str] = None,
                          metadata: Dict[str, Any] = None) -> Union[CommanderResult, str]:
        """提交任务（统一入口）
        
        Args:
            command: 任务指令
            task_type: 任务类型（AUTO自动判断/SINGLE_ROLE单角色/MULTI_ROLE多角色）
            run_mode: 运行模式（SYNC同步阻塞/ASYNC异步后台）
            role_name: 单角色模式下的角色名称
            role_names: 多角色模式下的角色名称列表
            metadata: 附加元数据
        
        Returns:
            SYNC模式: CommanderResult（包含完整结果）
            ASYNC模式: str（task_id，可通过get_task_status查询状态）
        """
        # 生成任务ID
        task_id = self._generate_task_id()
        start_time = time.time()
        
        # 自动判断任务类型
        if task_type == TaskType.AUTO:
            task_type = self._detect_task_type(command, role_name, role_names)
        
        # 创建任务元数据
        task_meta = TaskMeta(
            task_id=task_id,
            task_type=task_type,
            run_mode=run_mode,
            command=command,
            role_name=role_name,
            role_names=role_names or [],
        )
        
        # 写入状态中心
        await self.state_store.create_task(
            task_id=task_id,
            command=command,
            priority=metadata.get("priority", 0) if metadata else 0,
            role_name=role_name,
            metadata=metadata or {},
        )
        
        # 抛出任务提交事件
        await publish_event(
            EventType.TASK_SUBMITTED,
            message=f"任务已提交: {command[:50]}",
            task_id=task_id,
            role_name=role_name,
            data={"task_type": task_type.value, "run_mode": run_mode.value},
        )
        
        print(f"  [Commander] 任务已提交: {task_id} | 类型: {task_type.value} | 模式: {run_mode.value}")
        
        if run_mode == RunMode.ASYNC:
            # 异步模式：启动后台任务，立即返回task_id
            async_task = asyncio.create_task(self._execute_task(task_meta))
            self._async_tasks[task_id] = async_task
            # 任务完成后自动清理
            async_task.add_done_callback(lambda t: self._async_tasks.pop(task_id, None))
            return task_id
        else:
            # 同步模式：直接执行，等待完成
            return await self._execute_task(task_meta)
    
    async def _execute_task(self, task_meta: TaskMeta) -> CommanderResult:
        """执行任务（内部方法）"""
        start_time = time.time()
        task_id = task_meta.task_id
        
        try:
            # 更新任务状态为运行中
            await self.state_store.update_task_status(task_id, TaskStatus.RUNNING)
            await publish_event(
                EventType.TASK_START,
                message=f"任务开始执行: {task_meta.command[:50]}",
                task_id=task_id,
                role_name=task_meta.role_name,
            )
            
            result = {}
            role_used = None
            roles_used = []
            
            if task_meta.task_type == TaskType.SINGLE_ROLE:
                # 单角色执行
                role_used = task_meta.role_name or "default"
                result = await self._execute_single_role(task_meta)
            elif task_meta.task_type == TaskType.MULTI_ROLE:
                # 多角色协同
                roles_used = task_meta.role_names or []
                result = await self._execute_multi_role(task_meta)
            
            # 更新任务状态为完成
            duration = time.time() - start_time
            await self.state_store.update_task_status(
                task_id, TaskStatus.COMPLETED, progress=1.0, result=result
            )
            await publish_event(
                EventType.TASK_DONE,
                message=f"任务完成: {task_meta.command[:50]}",
                task_id=task_id,
                role_name=task_meta.role_name,
                data={"duration": duration, "result": result},
            )
            
            print(f"  [Commander] ✓ 任务完成: {task_id} | 耗时: {duration:.1f}s")
            
            return CommanderResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                task_type=task_meta.task_type,
                run_mode=task_meta.run_mode,
                result=result,
                duration=duration,
                role_used=role_used,
                roles_used=roles_used,
                message="任务执行成功",
            )
            
        except Exception as e:
            # 任务失败
            duration = time.time() - start_time
            error_msg = str(e)
            await self.state_store.update_task_status(
                task_id, TaskStatus.FAILED, error=error_msg
            )
            await publish_event(
                EventType.TASK_FAILED,
                message=f"任务失败: {error_msg[:50]}",
                task_id=task_id,
                role_name=task_meta.role_name,
                data={"error": error_msg, "duration": duration},
            )
            
            print(f"  [Commander] ❌ 任务失败: {task_id} | 错误: {error_msg[:50]}")
            
            return CommanderResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                task_type=task_meta.task_type,
                run_mode=task_meta.run_mode,
                error=error_msg,
                duration=duration,
                role_used=task_meta.role_name,
                roles_used=task_meta.role_names,
                message=f"任务执行失败: {error_msg}",
            )
    
    async def _execute_single_role(self, task_meta: TaskMeta) -> Dict[str, Any]:
        """执行单角色任务（内部方法）"""
        # 获取资源锁（确保Chrome实例不冲突）
        async with self.resource_manager.acquire_browser(f"单角色_{task_meta.role_name}"):
            manus = self._init_manus_with_roles()
            
            # 激活角色
            if task_meta.role_name:
                await self.state_store.activate_role(
                    role_name=task_meta.role_name,
                    task_id=task_meta.task_id,
                )
                await publish_event(
                    EventType.ROLE_ACTIVATE,
                    message=f"角色激活: {task_meta.role_name}",
                    task_id=task_meta.task_id,
                    role_name=task_meta.role_name,
                )
            
            try:
                # 执行任务
                if hasattr(manus, "run_with_role") and task_meta.role_name:
                    result = await manus.run_with_role(task_meta.role_name, task_meta.command)
                elif hasattr(manus, "run_with_auto_role"):
                    result = await manus.run_with_auto_role(task_meta.command)
                else:
                    # 降级：直接调用Manus
                    result = await manus.run(task_meta.command)
                
                return {"output": result, "role": task_meta.role_name}
            finally:
                # 取消激活角色
                if task_meta.role_name:
                    await self.state_store.deactivate_role(task_meta.role_name)
                    await publish_event(
                        EventType.ROLE_DEACTIVATE,
                        message=f"角色取消激活: {task_meta.role_name}",
                        task_id=task_meta.task_id,
                        role_name=task_meta.role_name,
                    )
    
    async def _execute_multi_role(self, task_meta: TaskMeta) -> Dict[str, Any]:
        """执行多角色协同任务（内部方法）"""
        # 获取资源锁（多角色模式下更需要控制并发）
        async with self.resource_manager.acquire_browser(f"多角色_{'_'.join(task_meta.role_names)}"):
            orchestrator = self._init_multi_role_orchestrator()
            
            # 执行多角色协同
            if hasattr(orchestrator, "run_pipeline") and task_meta.role_names:
                result = await orchestrator.run_pipeline(
                    role_names=task_meta.role_names,
                    initial_input=task_meta.command,
                )
            elif hasattr(orchestrator, "run_parallel") and task_meta.role_names:
                result = await orchestrator.run_parallel(
                    role_names=task_meta.role_names,
                    tasks=[task_meta.command] * len(task_meta.role_names),
                )
            else:
                # 降级：串行执行
                results = []
                for role_name in task_meta.role_names:
                    single_meta = TaskMeta(
                        task_id=task_meta.task_id,
                        task_type=TaskType.SINGLE_ROLE,
                        run_mode=RunMode.SYNC,
                        command=task_meta.command,
                        role_name=role_name,
                    )
                    r = await self._execute_single_role(single_meta)
                    results.append(r)
                result = {"results": results, "mode": "serial_fallback"}
            
            return {"output": result, "roles": task_meta.role_names}
    
    async def get_task_status(self, task_id: str) -> Optional[CommanderResult]:
        """获取任务状态（异步模式下查询）"""
        task = await self.state_store.get_task(task_id)
        if not task:
            return None
        
        return CommanderResult(
            task_id=task_id,
            status=task.status,
            task_type=TaskType.SINGLE_ROLE,  # 简化，实际应从metadata获取
            run_mode=RunMode.ASYNC,
            result=task.result,
            error=task.error,
            role_used=task.role_name,
            message=f"任务状态: {task.status.value}",
        )
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._async_tasks:
            self._async_tasks[task_id].cancel()
            await self.state_store.update_task_status(task_id, TaskStatus.CANCELLED)
            await publish_event(
                EventType.TASK_CANCELLED,
                message=f"任务已取消: {task_id}",
                task_id=task_id,
            )
            return True
        return False
    
    def list_available_roles(self) -> List[str]:
        """列出可用角色"""
        try:
            manus = self._init_manus_with_roles()
            if hasattr(manus, "list_available_roles"):
                return manus.list_available_roles()
        except Exception:
            pass
        return []
    
    def explain_role_selection(self, command: str) -> Dict[str, Any]:
        """解释角色选择（为什么选择这个角色）"""
        try:
            manus = self._init_manus_with_roles()
            if hasattr(manus, "explain_role_selection"):
                return manus.explain_role_selection(command)
        except Exception:
            pass
        return {"selected": "auto", "reason": "自动判断"}
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取Commander统计信息"""
        return {
            "async_tasks_running": len(self._async_tasks),
            "manus_initialized": self._manus_with_roles is not None,
            "orchestrator_initialized": self._multi_role_orchestrator is not None,
        }


# 全局便捷函数
def init_commander(config: Dict[str, Any] = None) -> Commander:
    """初始化全局Commander（应用启动时调用）"""
    return Commander(config=config)


def get_commander() -> Commander:
    """获取全局Commander实例"""
    return Commander.get_instance()


async def submit_command(command: str, **kwargs) -> Union[CommanderResult, str]:
    """便捷函数：提交命令到全局Commander"""
    commander = get_commander()
    return await commander.submit_task(command, **kwargs)
