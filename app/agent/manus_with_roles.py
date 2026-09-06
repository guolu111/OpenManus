"""
ManusWithRoles - 带角色卡体系的统帅类

继承Manus，添加角色卡支持：
- 角色选择（自动选择最合适的角色卡）
- 角色激活/取消激活（注入角色卡前缀到system_prompt）
- 工具权限过滤（白名单/黑名单）
- 模型路由（不同角色用不同模型）
- run_with_role方法（用指定角色卡执行任务）

使用方式：
    from app.agent.manus_with_roles import ManusWithRoles
    
    agent = await ManusWithRoles.create()
    
    # 自动选择角色卡执行
    result = await agent.run_with_auto_role("帮我分析一下这段文本的结构")
    
    # 指定角色卡执行
    result = await agent.run_with_role("分析", "帮我分析一下这段文本的结构")
    
    # 查看当前状态
    print(agent.role_status())
"""

import os
from typing import Dict, List, Optional, Tuple

from pydantic import Field

from app.agent.manus import Manus
from app.config import config
from app.logger import logger
from app.role_cards import RoleOrchestrator, RoleCard


class ManusWithRoles(Manus):
    """
    带角色卡体系的统帅类

    继承Manus，添加角色卡支持：
    - 角色选择（自动选择最合适的角色卡）
    - 角色激活/取消激活
    - 工具权限过滤
    - 模型路由
    """

    # 角色卡调度器（用下划线前缀表示私有属性，不参与pydantic验证）
    _role_orchestrator: Optional[RoleOrchestrator] = None
    _roles_initialized: bool = False

    @classmethod
    async def create(cls, **kwargs) -> "ManusWithRoles":
        """
        Factory method to create and properly initialize a ManusWithRoles instance.
        """
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()

        # 初始化自动记忆提取器
        try:
            from app.tool.memory_tool import MemoryTool
            from app.tool.auto_memory import AutoMemoryExtractor
            instance._auto_memory = AutoMemoryExtractor()
        except Exception as e:
            logger.warning(f"AutoMemoryExtractor initialization failed: {e}")
            instance._auto_memory = None

        instance._initialized = True

        # 初始化角色卡调度器
        instance._init_role_orchestrator()

        return instance

    def _init_role_orchestrator(self):
        """初始化角色卡调度器"""
        if self._roles_initialized:
            return

        try:
            # 角色卡目录
            role_cards_dir = os.path.join(config.workspace_root, "角色卡")
            if not os.path.exists(role_cards_dir):
                # 尝试项目根目录下的角色卡
                role_cards_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "角色卡")

            self._role_orchestrator = RoleOrchestrator(role_cards_dir)
            self._roles_initialized = True
            logger.info(f"角色卡调度器初始化成功，目录: {role_cards_dir}")
        except Exception as e:
            logger.error(f"角色卡调度器初始化失败: {e}")
            self._role_orchestrator = None
            self._roles_initialized = False

    def role_status(self) -> str:
        """查看角色卡状态"""
        if not self._role_orchestrator:
            return "角色卡调度器未初始化"
        return self._role_orchestrator.status()

    def select_role(self, task: str) -> Tuple[str, float, dict]:
        """
        自动选择最合适的角色卡

        Args:
            task: 任务描述

        Returns:
            (角色名, 匹配度, 匹配详情)
        """
        if not self._role_orchestrator:
            return "生成", 0.3, {"reason": "角色卡调度器未初始化，默认用生成卡"}

        return self._role_orchestrator.select_role(task)

    def activate_role(self, role_name: str) -> bool:
        """
        激活指定角色卡（注入角色卡前缀到system_prompt）

        Args:
            role_name: 角色卡名称

        Returns:
            是否激活成功
        """
        if not self._role_orchestrator:
            logger.error("角色卡调度器未初始化，无法激活角色卡")
            return False

        # 备份原始system_prompt（只备份一次）
        if not hasattr(self, '_original_system_prompt'):
            self._original_system_prompt = self.system_prompt

        result = self._role_orchestrator.activate_role(role_name, self)
        if result:
            logger.info(f"角色卡激活成功: {role_name}")
        else:
            logger.error(f"角色卡激活失败: {role_name}")
        return result

    def deactivate_role(self) -> bool:
        """
        取消激活角色卡，恢复统帅身份

        Returns:
            是否取消成功
        """
        if not self._role_orchestrator:
            return False

        result = self._role_orchestrator.deactivate_role(self)
        if result:
            logger.info("角色卡已取消激活，恢复统帅身份")
        return result

    def get_active_role(self) -> Optional[RoleCard]:
        """获取当前激活的角色卡"""
        if not self._role_orchestrator:
            return None
        return self._role_orchestrator.get_active_role()

    async def run_with_role(self, role_name: str, prompt: str, **kwargs) -> str:
        """
        用指定角色卡执行任务

        Args:
            role_name: 角色卡名称
            prompt: 任务提示词
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        logger.info(f"用角色卡 [{role_name}] 执行任务: {prompt[:50]}...")

        # 激活角色卡
        activated = self.activate_role(role_name)
        if not activated:
            logger.warning(f"角色卡激活失败，用统帅身份执行")

        try:
            # 执行任务（调用父类的run方法）
            # 注意：Manus的run方法需要根据实际签名调用
            # 这里先用简单的方式，后续根据实际Manus的run方法调整
            result = await self.run(prompt, **kwargs)
            return result
        finally:
            # 取消激活角色卡，恢复统帅身份
            if activated:
                self.deactivate_role()

    async def run_with_auto_role(self, prompt: str, **kwargs) -> str:
        """
        自动选择角色卡执行任务

        Args:
            prompt: 任务提示词
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        # 自动选择角色卡
        role_name, score, reason = self.select_role(prompt)
        logger.info(f"自动选择角色卡: {role_name} (匹配度 {score:.2f})")

        # 用选择的角色卡执行
        return await self.run_with_role(role_name, prompt, **kwargs)

    def explain_role_selection(self, task: str) -> str:
        """
        解释角色选择的原因（用于调试）

        Args:
            task: 任务描述

        Returns:
            选择解释
        """
        if not self._role_orchestrator:
            return "角色卡调度器未初始化"
        return self._role_orchestrator.explain_selection(task)

    def list_available_roles(self) -> List[Dict]:
        """列出所有可用的角色卡"""
        if not self._role_orchestrator:
            return []
        return self._role_orchestrator.list_roles()
