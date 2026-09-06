"""
角色卡注册表

记录每张角色卡的元信息：
- 角色定位、核心价值
- 权限级别、工具白名单/黑名单
- 偏好模型、备用模型
- 适用场景关键词
- 版本、描述

注册表是角色卡体系的"编制表"，统帅根据注册表选择合适的角色卡。

权限级别定义：
- L0 只读：只能读取文件、搜索、浏览网页
- L1 沙箱：L0 + Python执行、代码生成（不修改系统文件）
- L2 受限：L1 + API调用、文件编辑（指定目录）
- L3 全局：所有工具（仅统帅/管理员可用）
"""

from enum import Enum
from typing import Dict, List, Optional

from app.logger import logger


class PermissionLevel(Enum):
    """权限级别枚举"""
    L0_READONLY = "L0"  # 只读
    L1_SANDBOX = "L1"  # 沙箱
    L2_RESTRICTED = "L2"  # 受限
    L3_GLOBAL = "L3"  # 全局


# 角色卡注册表
# 格式：{role_name: {metadata}}
ROLE_REGISTRY: Dict[str, dict] = {
    # ========== 统帅级 ==========
    "文件夹管理员": {
        "display_name": "文件夹管理员/统帅",
        "role_position": "《一念永恒》创作文件夹的总管理员，负责管理整个文件夹的所有内容，包括9个子文件夹、8个业务角色卡、世界书、运行记录、所有py脚本、项目记忆。",
        "core_value": "给MainAgent一个标准操作流程，减少遗漏；给MainAgent一个常用工具索引；给MainAgent一个项目记忆入口；统一管理8个业务角色卡；反刍机制：每次任务完成后自动检查、蒸馏、更新，越用越聪明。",
        "permission_level": "L3",  # 全局权限
        "allowed_tools": [],  # 空表示全部允许
        "denied_tools": [],
        "preferred_model": "gemini-2.5-pro",  # 复杂决策用旗舰模型
        "fallback_model": "gemini-2.5-flash-lite",
        "适用场景": [
            "文件夹管理", "目录索引", "同步检查", "任务调度",
            "反刍闭环", "角色卡管理", "世界书维护", "项目记忆",
            "管理员", "统帅", "总控",
        ],
        "not_适用场景": [
            "具体内容生成", "文本分析细节", "代码编写细节",
        ],
        "version": "v2.5",
        "description": "总管理员卡，统帅级，全局权限，负责调度和反刍",
    },

    # ========== 将级（业务核心） ==========
    "分析": {
        "display_name": "分析师",
        "role_position": "负责文本分析、数据统计、问题诊断。只读权限，不修改任何文件。",
        "core_value": "深度分析文本结构、人物关系、情节脉络；统计数据、发现规律；诊断问题、定位根因。",
        "permission_level": "L0",  # 只读
        "allowed_tools": [
            "read_file", "search_web", "browse", "python_execute",
            "web_search", "comment_search", "usage_tool", "status_monitor",
        ],
        "denied_tools": [
            "write_file", "delete_file", "bash", "str_replace_editor",
            "python_execute_write", "batch_run",
        ],
        "preferred_model": "gemini-2.5-flash-lite",
        "fallback_model": "glm-4.5-air",
        "适用场景": [
            "分析", "统计", "诊断", "检查", "对比", "评估",
            "文本分析", "数据分析", "问题分析", "结构分析",
            "人物分析", "情节分析", "钩子分析", "质量检查",
        ],
        "not_适用场景": [
            "生成", "创作", "编写", "修改", "删除",
        ],
        "version": "v1.0",
        "description": "分析师卡，只读权限，负责分析和诊断",
    },

    "生成": {
        "display_name": "生成器",
        "role_position": "负责内容生成、代码编写、方案设计。沙箱权限，可以生成内容和代码，但不修改系统关键文件。",
        "core_value": "根据需求生成高质量内容；编写可运行的代码；设计完整的方案；是最通用的业务角色卡。",
        "permission_level": "L1",  # 沙箱
        "allowed_tools": [
            "python_execute", "str_replace_editor", "read_file",
            "web_search", "comment_search", "ask_tag", "zhipu_helper",
            "siliconflow_helper", "ask_enhancer", "optimize_plans",
            "voice_correct", "memory_tool",
        ],
        "denied_tools": [
            "bash", "batch_run", "bridge_health", "notify_feishu",
        ],
        "preferred_model": "gemini-2.5-flash-lite",
        "fallback_model": "glm-4.5-air",
        "适用场景": [
            "生成", "创作", "编写", "设计", "构建", "实现",
            "写代码", "写脚本", "写文章", "写方案", "内容生成",
            "代码生成", "方案设计", "文档编写",
        ],
        "not_适用场景": [
            "分析", "统计", "诊断", "教学", "匹配",
        ],
        "version": "v1.0",
        "description": "生成器卡，沙箱权限，最通用的业务角色",
    },

    "老师": {
        "display_name": "导师",
        "role_position": "负责知识讲解、教程编写、学习指导。只读+教学权限，不修改业务文件。",
        "core_value": "把复杂知识讲清楚；编写系统化教程；指导学习路径；解答疑问。",
        "permission_level": "L0",  # 只读
        "allowed_tools": [
            "read_file", "search_web", "browse", "python_execute",
            "web_search", "comment_search", "ask_tag",
        ],
        "denied_tools": [
            "write_file", "delete_file", "bash", "str_replace_editor",
            "batch_run",
        ],
        "preferred_model": "gemini-2.5-flash-lite",
        "fallback_model": "glm-4.5-air",
        "适用场景": [
            "教学", "讲解", "教程", "指导", "学习", "解释",
            "知识讲解", "原理说明", "入门教程", "学习路径",
            "怎么用", "如何", "为什么",
        ],
        "not_适用场景": [
            "生成", "分析", "匹配", "跑批",
        ],
        "version": "v1.0",
        "description": "导师卡，只读权限，负责教学和讲解",
    },

    "学生": {
        "display_name": "学徒",
        "role_position": "负责模仿学习、练习生成、试错验证。沙箱权限，可以尝试和犯错，但需要老师/统帅审核。",
        "core_value": "模仿优秀案例；快速试错验证；生成初稿供审核；是成本最低的探索角色。",
        "permission_level": "L1",  # 沙箱
        "allowed_tools": [
            "python_execute", "read_file", "str_replace_editor",
            "zhipu_helper", "siliconflow_helper",
        ],
        "denied_tools": [
            "bash", "batch_run", "web_search", "ask_tag",
            "notify_feishu", "bridge_health",
        ],
        "preferred_model": "glm-4-9b",  # 学生用最便宜的模型
        "fallback_model": "glm-4.5-air",
        "适用场景": [
            "学习", "模仿", "练习", "试错", "验证", "初稿",
            "简单生成", "批量处理", "去重", "分类",
        ],
        "not_适用场景": [
            "复杂分析", "高质量生成", "教学", "决策",
        ],
        "version": "v1.0",
        "description": "学徒卡，沙箱权限，成本最低的探索角色",
    },

    "匹配": {
        "display_name": "匹配器",
        "role_position": "负责角色匹配、相似度计算、分类归类。只读+匹配权限。",
        "core_value": "计算文本相似度；匹配角色与场景；分类归类；建立关联关系。",
        "permission_level": "L0",  # 只读
        "allowed_tools": [
            "read_file", "python_execute", "search_web",
        ],
        "denied_tools": [
            "write_file", "delete_file", "bash", "str_replace_editor",
            "batch_run", "ask_tag",
        ],
        "preferred_model": "glm-4.5-air",
        "fallback_model": "glm-4-9b",
        "适用场景": [
            "匹配", "相似度", "分类", "归类", "关联", "对比",
            "角色匹配", "场景匹配", "文本相似度", "聚类",
        ],
        "not_适用场景": [
            "生成", "教学", "跑批", "决策",
        ],
        "version": "v1.0",
        "description": "匹配器卡，只读权限，负责匹配和分类",
    },

    # ========== 校级（专业功能） ==========
    "小助手": {
        "display_name": "中转API调度管家",
        "role_position": "负责中转API的调度、用量监控、数据搬运。受限权限，主要调用API，不修改业务文件。",
        "core_value": "统一管理多个中转API；监控用量防止超支；批量数据搬运；简单JSON处理；是统帅的数据搬运工。",
        "permission_level": "L2",  # 受限
        "allowed_tools": [
            "zhipu_helper", "siliconflow_helper", "ask_tag",
            "usage_tool", "status_monitor", "python_execute",
            "read_file", "str_replace_editor", "voice_correct",
        ],
        "denied_tools": [
            "bash", "batch_run", "web_search", "comment_search",
            "notify_feishu", "bridge_health", "ask_human",
        ],
        "preferred_model": "glm-4.5-air",  # 小助手用智谱，不占谷歌额度
        "fallback_model": "glm-4-9b",
        "适用场景": [
            "API", "中转", "数据搬运", "批量处理", "用量监控",
            "JSON处理", "去重", "分类", "简单问答",
            "小助手", "调用API", "数据处理",
        ],
        "not_适用场景": [
            "复杂分析", "高质量生成", "教学", "决策", "跑批",
        ],
        "version": "v1.0",
        "description": "小助手卡，受限权限，中转API调度和数据搬运",
    },

    "每天更新": {
        "display_name": "连载业务管家",
        "role_position": "负责金庸连载跑批、分天版生成、每日分析成果。沙箱+业务权限，专门处理连载业务。",
        "core_value": "标准化连载跑批流程；生成完整六项分析成果；管理15本书的进度；是连载业务的专属角色。",
        "permission_level": "L2",  # 受限（业务目录）
        "allowed_tools": [
            "batch_run", "python_execute", "str_replace_editor",
            "read_file", "status_monitor", "usage_tool",
            "notify_feishu", "zhipu_helper", "siliconflow_helper",
        ],
        "denied_tools": [
            "bash", "web_search", "comment_search", "ask_tag",
            "bridge_health", "ask_human",
        ],
        "preferred_model": "gemini-2.5-flash-lite",
        "fallback_model": "glm-4.5-air",
        "适用场景": [
            "连载", "跑批", "金庸", "分天版", "每日更新",
            "章节分析", "钩子", "起承转合", "15本书",
            "鹿鼎记", "射雕", "神雕", "倚天",
        ],
        "not_适用场景": [
            "其他小说", "通用分析", "教学", "匹配",
        ],
        "version": "v1.0",
        "description": "每天更新卡，受限权限，金庸连载业务专属",
    },

    "脚本": {
        "display_name": "脚本副将军/军械库总管",
        "role_position": "负责所有脚本的统一管理、工具注册、代码复用。沙箱+脚本权限，专门管理脚本仓库。",
        "core_value": "统一管理脚本仓库；防止重复生成；固化/临时两档管理；写脚本前必查注册表；是7将军的军械库总管。",
        "permission_level": "L1",  # 沙箱
        "allowed_tools": [
            "python_execute", "str_replace_editor", "read_file",
            "web_search", "comment_search", "zhipu_helper",
            "siliconflow_helper",
        ],
        "denied_tools": [
            "bash", "batch_run", "ask_tag", "notify_feishu",
            "bridge_health", "ask_human",
        ],
        "preferred_model": "gemini-2.5-flash-lite",
        "fallback_model": "glm-4.5-air",
        "适用场景": [
            "脚本", "工具", "代码复用", "脚本管理", "工具注册",
            "写脚本", "改脚本", "调试脚本", "脚本仓库",
            "军械库", "固化", "临时",
        ],
        "not_适用场景": [
            "内容生成", "文本分析", "教学", "跑批", "匹配",
        ],
        "version": "v1.0",
        "description": "脚本卡，沙箱权限，脚本仓库总管",
    },
}


class RoleRegistry:
    """角色卡注册表

    提供角色卡元信息的查询和管理接口。
    """

    def __init__(self, registry: Optional[Dict[str, dict]] = None):
        """
        初始化注册表

        Args:
            registry: 自定义注册表，为空则使用默认ROLE_REGISTRY
        """
        self._registry = registry or ROLE_REGISTRY
        logger.info(f"角色卡注册表初始化完成，共 {len(self._registry)} 张角色卡")

    def get(self, role_name: str) -> Optional[dict]:
        """获取指定角色卡的元信息"""
        return self._registry.get(role_name)

    def get_all(self) -> Dict[str, dict]:
        """获取所有角色卡的元信息"""
        return self._registry.copy()

    def get_names(self) -> List[str]:
        """获取所有角色卡名称"""
        return list(self._registry.keys())

    def get_by_permission(self, level: str) -> List[str]:
        """按权限级别筛选角色卡"""
        return [
            name for name, meta in self._registry.items()
            if meta.get("permission_level") == level
        ]

    def get_by_scenario(self, scenario_keyword: str) -> List[str]:
        """按适用场景关键词筛选角色卡"""
        results = []
        for name, meta in self._registry.items():
            scenarios = meta.get("适用场景", [])
            if any(scenario_keyword in s for s in scenarios):
                results.append(name)
        return results

    def register(self, role_name: str, metadata: dict) -> bool:
        """
        注册新角色卡

        Args:
            role_name: 角色名
            metadata: 元信息

        Returns:
            是否注册成功
        """
        if role_name in self._registry:
            logger.warning(f"角色卡已存在，将覆盖: {role_name}")
        self._registry[role_name] = metadata
        logger.info(f"角色卡注册成功: {role_name}")
        return True

    def unregister(self, role_name: str) -> bool:
        """注销角色卡"""
        if role_name not in self._registry:
            logger.warning(f"角色卡不存在: {role_name}")
            return False
        del self._registry[role_name]
        logger.info(f"角色卡注销成功: {role_name}")
        return True

    def summary(self) -> str:
        """生成注册表摘要"""
        lines = ["=== 角色卡注册表摘要 ==="]
        lines.append(f"总计: {len(self._registry)} 张角色卡")
        lines.append("")

        # 按权限分组
        for level in ["L3", "L2", "L1", "L0"]:
            roles = self.get_by_permission(level)
            if roles:
                level_name = {
                    "L3": "全局权限（统帅级）",
                    "L2": "受限权限（校级）",
                    "L1": "沙箱权限（将级）",
                    "L0": "只读权限（尉级）",
                }.get(level, level)
                lines.append(f"[{level_name}] {len(roles)} 张:")
                for role in roles:
                    meta = self._registry[role]
                    lines.append(f"  - {role} ({meta.get('display_name', role)})")
                lines.append("")

        return "\n".join(lines)
