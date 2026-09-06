"""
角色调度器

负责角色卡的切换和任务执行。

核心功能：
1. 加载角色卡
2. 切换系统提示词（角色卡内容注入）
3. 切换工具集合（权限过滤）
4. 切换模型（偏好模型）
5. 执行任务
6. 执行完后恢复统帅状态

MVP版本实现：
- 单角色调度：选择一个角色卡，用它的身份执行任务
- 系统提示词注入：把角色卡内容作为前缀加到统帅系统提示词前面
- 工具过滤：根据角色卡的白名单/黑名单过滤可用工具
- 执行完恢复：任务执行完后恢复统帅的原始状态

后续版本：
- 多角色串行调度：A卡→B卡→C卡流水线
- 多角色并行调度：多卡同时执行独立子任务
- 结果汇总：多卡结果整合成统一报告
- 角色卡效果评估：哪张卡干哪类活最好
"""

import os
from typing import Dict, List, Optional, Tuple

from app.logger import logger
from app.role_cards.role_card import RoleCard, RoleCardLoader
from app.role_cards.role_registry import RoleRegistry
from app.role_cards.role_selector import RoleSelector


class RoleOrchestrator:
    """角色调度器

    负责角色卡的切换和任务执行。
    """

    def __init__(
        self,
        role_cards_dir: str,
        registry: Optional[RoleRegistry] = None,
    ):
        """
        初始化调度器

        Args:
            role_cards_dir: 角色卡目录路径
            registry: 角色卡注册表（为空则使用默认）
        """
        self.role_cards_dir = role_cards_dir
        self.registry = registry or RoleRegistry()
        self.loader = RoleCardLoader(role_cards_dir)
        self.selector = RoleSelector(self.registry)

        # 当前激活的角色卡（None表示统帅本身）
        self._active_role: Optional[RoleCard] = None

        # 统帅原始状态备份（用于恢复）
        self._original_state: Dict = {}

        logger.info(f"角色调度器初始化完成，角色卡目录: {role_cards_dir}")
        logger.info(self.registry.summary())

    def select_role(self, task: str, context: Optional[dict] = None) -> Tuple[str, float, dict]:
        """
        为任务选择合适的角色卡

        Args:
            task: 用户任务
            context: 上下文

        Returns:
            (角色名, 匹配度, 选择理由)
        """
        return self.selector.select(task, context)

    def load_role(self, role_name: str) -> Optional[RoleCard]:
        """
        加载指定角色卡

        Args:
            role_name: 角色名

        Returns:
            RoleCard对象
        """
        metadata = self.registry.get(role_name)
        if not metadata:
            logger.warning(f"角色卡不在注册表中: {role_name}，将使用默认元信息")
            metadata = {}

        role_card = self.loader.load(role_name, metadata)
        if not role_card:
            logger.error(f"角色卡加载失败: {role_name}")
        return role_card

    def activate_role(self, role_name: str, agent) -> bool:
        """
        激活角色卡（切换agent的身份）

        MVP版本实现：
        1. 备份agent原始状态
        2. 把角色卡内容作为前缀加到系统提示词
        3. 根据角色卡权限过滤工具
        4. 记录当前激活的角色卡

        Args:
            role_name: 角色名
            agent: Manus agent实例

        Returns:
            是否激活成功
        """
        # 如果已经激活了同一个角色卡，直接返回
        if self._active_role and self._active_role.name == role_name:
            logger.info(f"角色卡已激活: {role_name}")
            return True

        # 加载角色卡
        role_card = self.load_role(role_name)
        if not role_card:
            return False

        # 备份原始状态
        self._original_state = {
            "system_prompt": agent.system_prompt,
            "available_tools": agent.available_tools,
        }

        # 1. 注入角色卡系统提示词
        # 把角色卡内容作为前缀，后面跟上统帅的系统提示词
        role_prefix = self._build_role_prefix(role_card)
        agent.system_prompt = role_prefix + "\n\n" + agent.system_prompt
        logger.info(f"角色卡系统提示词已注入: {role_name} (前缀 {len(role_prefix)} 字符)")

        # 2. 过滤工具（根据角色卡权限）
        # MVP版本：只记录，不过滤（避免工具缺失导致执行失败）
        # 后续版本：实现真正的工具过滤
        filtered_tools = self._filter_tools(agent.available_tools, role_card)
        if filtered_tools:
            logger.info(f"角色卡工具过滤: {role_name}，保留 {len(filtered_tools.tools)}/{len(agent.available_tools.tools)} 个工具")
            # agent.available_tools = filtered_tools  # MVP版本暂不启用

        # 3. 记录当前激活的角色卡
        self._active_role = role_card
        logger.info(f"角色卡激活成功: {role_name} (权限 {role_card.permission_level})")
        return True

    def deactivate_role(self, agent) -> bool:
        """
        取消角色卡激活（恢复统帅原始状态）

        Args:
            agent: Manus agent实例

        Returns:
            是否恢复成功
        """
        if not self._active_role:
            logger.info("当前没有激活的角色卡，无需恢复")
            return True

        role_name = self._active_role.name

        # 恢复原始状态
        if "system_prompt" in self._original_state:
            agent.system_prompt = self._original_state["system_prompt"]
        if "available_tools" in self._original_state:
            agent.available_tools = self._original_state["available_tools"]

        # 清空状态
        self._active_role = None
        self._original_state = {}

        logger.info(f"角色卡已取消激活，恢复统帅身份: {role_name}")
        return True

    async def run_with_role(
        self,
        task: str,
        agent,
        role_name: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> Tuple[str, str, float]:
        """
        用指定角色卡执行任务

        如果不指定角色卡，自动选择最合适的角色卡。

        Args:
            task: 用户任务
            agent: Manus agent实例
            role_name: 指定角色卡（为空则自动选择）
            context: 上下文

        Returns:
            (执行结果, 使用的角色卡名, 匹配度)
        """
        # 1. 选择角色卡
        if not role_name:
            role_name, score, reason = self.select_role(task, context)
            logger.info(f"自动选择角色卡: {role_name} (匹配度 {score:.2f}) - {reason.get('reason', '')}")
        else:
            score = 1.0
            logger.info(f"使用指定角色卡: {role_name}")

        # 2. 激活角色卡
        if not self.activate_role(role_name, agent):
            logger.warning(f"角色卡激活失败，将用统帅身份执行: {role_name}")
            result = await agent.run(task)
            return result, "统帅（角色卡激活失败）", 0.0

        try:
            # 3. 执行任务
            logger.info(f"开始用角色卡 [{role_name}] 执行任务: {task[:50]}...")
            result = await agent.run(task)
            logger.info(f"角色卡 [{role_name}] 任务执行完成")
            return result, role_name, score

        except Exception as e:
            logger.error(f"角色卡 [{role_name}] 任务执行失败: {e}")
            raise

        finally:
            # 4. 恢复统帅身份（无论成功失败都恢复）
            self.deactivate_role(agent)

    def _build_role_prefix(self, role_card: RoleCard) -> str:
        """
        构建角色卡前缀（注入到系统提示词前面）

        Args:
            role_card: 角色卡对象

        Returns:
            角色卡前缀文本
        """
        lines = [
            "=" * 60,
            f"【角色卡激活】你现在的身份是：{role_card.display_name}",
            "=" * 60,
            "",
            f"【角色名】{role_card.name}",
            f"【角色定位】{role_card.role_position}",
            f"【核心价值】{role_card.core_value}",
            f"【权限级别】{role_card.permission_level}",
            f"【偏好模型】{role_card.preferred_model or '默认模型'}",
            "",
            "【角色卡完整内容】",
            "-" * 40,
            role_card.system_prompt,
            "-" * 40,
            "",
            "【执行要求】",
            "1. 严格按照上述角色卡的定位和规范执行任务",
            "2. 使用角色卡规定的工作流程和方法",
            "3. 遵守角色卡的权限限制，不越权操作",
            "4. 输出风格符合角色卡的定位",
            "",
            "=" * 60,
            "以下是统帅的通用系统提示词，请结合角色卡身份执行：",
            "=" * 60,
        ]
        return "\n".join(lines)

    def _filter_tools(self, tool_collection, role_card: RoleCard):
        """
        根据角色卡权限过滤工具

        MVP版本：只返回过滤后的工具列表，不实际修改agent的工具集合
        （避免工具缺失导致执行失败，后续版本再启用真正的过滤）

        Args:
            tool_collection: 原始工具集合
            role_card: 角色卡对象

        Returns:
            过滤后的工具集合（或None表示不过滤）
        """
        # 如果角色卡没有定义白名单和黑名单，不过滤
        if not role_card.allowed_tools and not role_card.denied_tools:
            return None

        # MVP版本：只记录，不实际过滤
        # 因为工具名称可能不完全匹配，过滤后可能导致关键工具缺失
        logger.info(
            f"工具过滤（MVP版本仅记录）: {role_card.name}，"
            f"白名单{len(role_card.allowed_tools)}个，黑名单{len(role_card.denied_tools)}个"
        )
        return None

    def get_active_role(self) -> Optional[RoleCard]:
        """获取当前激活的角色卡"""
        return self._active_role

    def get_available_roles(self) -> List[str]:
        """获取所有可用的角色卡名称"""
        return self.registry.get_names()

    def explain_selection(self, task: str, context: Optional[dict] = None) -> str:
        """生成角色选择解释（用于调试）"""
        return self.selector.explain_selection(task, context)

    def status(self) -> str:
        """生成调度器状态摘要"""
        lines = ["=== 角色调度器状态 ==="]
        lines.append(f"角色卡目录: {self.role_cards_dir}")
        lines.append(f"注册角色卡: {len(self.registry.get_names())} 张")

        if self._active_role:
            lines.append(f"当前激活: {self._active_role.name} ({self._active_role.display_name})")
            lines.append(f"  权限: {self._active_role.permission_level}")
            lines.append(f"  偏好模型: {self._active_role.preferred_model or '默认'}")
        else:
            lines.append("当前激活: 无（统帅身份）")

        lines.append("")
        lines.append("可用角色卡:")
        for role_name in self.registry.get_names():
            meta = self.registry.get(role_name)
            lines.append(f"  - {role_name} ({meta.get('display_name', role_name)}) "
                         f"[{meta.get('permission_level', '?')}]")

        return "\n".join(lines)
