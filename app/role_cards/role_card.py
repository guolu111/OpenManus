"""
角色卡数据类和加载器

角色卡是一个独立的txt文件，包含：
- 角色名、角色定位
- 行为规范、工作流程
- 权限级别、工具白名单
- 适用场景、模型选择

加载器负责读取txt文件，解析成结构化的RoleCard对象。
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Set

from app.logger import logger


@dataclass
class RoleCard:
    """角色卡数据类"""

    # 基本信息
    name: str  # 角色名，如"分析"、"生成"
    display_name: str  # 显示名，如"分析师"、"生成器"
    file_path: str  # 角色卡文件路径

    # 角色定位
    role_position: str = ""  # 角色定位描述
    core_value: str = ""  # 核心价值

    # 权限和工具
    permission_level: str = "L1"  # 权限级别：L0只读/L1沙箱/L2受限/L3全局
    allowed_tools: List[str] = field(default_factory=list)  # 工具白名单（空表示全部允许）
    denied_tools: List[str] = field(default_factory=list)  # 工具黑名单

    # 模型选择
    preferred_model: str = ""  # 偏好模型（空表示用默认模型）
    fallback_model: str = ""  # 备用模型

    # 适用场景
    适用场景: List[str] = field(default_factory=list)  # 适用场景关键词
    not_适用场景: List[str] = field(default_factory=list)  # 不适用场景关键词

    # 系统提示词（从txt文件加载的完整内容）
    system_prompt: str = ""

    # 元信息
    version: str = "v1.0"
    description: str = ""

    def __post_init__(self):
        """初始化后处理"""
        if not self.display_name:
            self.display_name = self.name

    def can_use_tool(self, tool_name: str) -> bool:
        """检查是否可以使用某个工具"""
        # 黑名单优先
        if tool_name in self.denied_tools:
            return False
        # 白名单为空表示全部允许
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools

    def matches_task(self, task: str) -> float:
        """
        计算角色卡与任务的匹配度（0-1）
        基于适用场景关键词匹配
        """
        if not self.适用场景:
            return 0.5  # 没有定义适用场景，默认中等匹配

        task_lower = task.lower()
        match_count = 0
        for keyword in self.适用场景:
            if keyword.lower() in task_lower:
                match_count += 1

        # 简单匹配度计算
        if not self.适用场景:
            return 0.5
        return match_count / len(self.适用场景)

    def to_dict(self) -> dict:
        """转成字典"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "role_position": self.role_position,
            "permission_level": self.permission_level,
            "preferred_model": self.preferred_model,
            "适用场景": self.适用场景,
            "version": self.version,
            "description": self.description,
        }


class RoleCardLoader:
    """角色卡加载器

    负责从txt文件加载角色卡，解析成RoleCard对象。

    角色卡txt文件格式：
    - 第一行通常是角色名或标题
    - 包含【角色名】【角色定位】等标记
    - 其余内容作为系统提示词

    元信息可以通过注册表硬编码，也可以从文件中解析。
    当前MVP版本：元信息从注册表获取，系统提示词从文件加载。
    """

    def __init__(self, role_cards_dir: str):
        """
        初始化加载器

        Args:
            role_cards_dir: 角色卡目录路径
        """
        self.role_cards_dir = role_cards_dir
        self._cache: dict = {}  # 缓存已加载的角色卡

    def load(self, role_name: str, metadata: Optional[dict] = None) -> Optional[RoleCard]:
        """
        加载指定角色卡

        Args:
            role_name: 角色名（对应文件名，如"分析"对应"分析.txt"）
            metadata: 元信息字典（从注册表获取），包含定位、权限、适用场景等

        Returns:
            RoleCard对象，如果文件不存在返回None
        """
        # 检查缓存
        if role_name in self._cache:
            return self._cache[role_name]

        # 构造文件路径
        file_path = os.path.join(self.role_cards_dir, f"{role_name}.txt")
        if not os.path.exists(file_path):
            logger.warning(f"角色卡文件不存在: {file_path}")
            return None

        # 读取文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取角色卡文件失败 {file_path}: {e}")
            return None

        # 解析元信息（如果提供了metadata，优先用metadata）
        metadata = metadata or {}

        # 创建RoleCard对象
        role_card = RoleCard(
            name=role_name,
            display_name=metadata.get("display_name", role_name),
            file_path=file_path,
            role_position=metadata.get("role_position", ""),
            core_value=metadata.get("core_value", ""),
            permission_level=metadata.get("permission_level", "L1"),
            allowed_tools=metadata.get("allowed_tools", []),
            denied_tools=metadata.get("denied_tools", []),
            preferred_model=metadata.get("preferred_model", ""),
            fallback_model=metadata.get("fallback_model", ""),
            适用场景=metadata.get("适用场景", []),
            not_适用场景=metadata.get("not_适用场景", []),
            system_prompt=content,
            version=metadata.get("version", "v1.0"),
            description=metadata.get("description", ""),
        )

        # 缓存
        self._cache[role_name] = role_card
        logger.info(f"角色卡加载成功: {role_name} ({len(content)} 字符)")

        return role_card

    def load_all(self, registry_metadata: dict) -> List[RoleCard]:
        """
        加载所有角色卡

        Args:
            registry_metadata: 注册表元信息，格式 {role_name: {metadata}}

        Returns:
            RoleCard对象列表
        """
        role_cards = []
        for role_name, metadata in registry_metadata.items():
            role_card = self.load(role_name, metadata)
            if role_card:
                role_cards.append(role_card)
        logger.info(f"共加载 {len(role_cards)} 张角色卡")
        return role_cards

    def reload(self, role_name: str, metadata: Optional[dict] = None) -> Optional[RoleCard]:
        """
        重新加载角色卡（清除缓存）

        Args:
            role_name: 角色名
            metadata: 元信息

        Returns:
            RoleCard对象
        """
        if role_name in self._cache:
            del self._cache[role_name]
        return self.load(role_name, metadata)

    def get_available_roles(self) -> List[str]:
        """获取目录下所有可用的角色卡名称"""
        if not os.path.exists(self.role_cards_dir):
            return []
        roles = []
        for filename in os.listdir(self.role_cards_dir):
            if filename.endswith(".txt"):
                role_name = filename[:-4]  # 去掉.txt
                roles.append(role_name)
        return sorted(roles)
