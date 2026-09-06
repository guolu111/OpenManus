"""
角色选择器

根据用户任务自动选择最合适的角色卡。

选择策略：
1. 关键词匹配：根据任务中的关键词匹配角色卡的适用场景
2. 任务类型分类：分析/生成/教学/匹配/跑批/脚本管理等
3. 复杂度评估：简单任务用轻量角色，复杂任务用旗舰角色
4. 权限需求：需要修改文件用L1+，只读用L0

选择决策树：
任务来了
  ↓
是文件夹管理/任务调度？→ 文件夹管理员
  ↓ 否
是连载跑批业务？→ 每天更新
  ↓ 否
是脚本管理/工具开发？→ 脚本
  ↓ 否
是API调用/数据搬运？→ 小助手
  ↓ 否
是分析/诊断/统计？→ 分析
  ↓ 否
是生成/创作/编写？→ 生成
  ↓ 否
是教学/讲解/指导？→ 老师
  ↓ 否
是匹配/分类/相似度？→ 匹配
  ↓ 否
是学习/模仿/试错？→ 学生
  ↓ 否
默认 → 生成（最通用）
"""

import re
from typing import Dict, List, Optional, Tuple

from app.logger import logger
from app.role_cards.role_registry import RoleRegistry


class RoleSelector:
    """角色选择器

    根据用户任务自动选择最合适的角色卡。
    """

    def __init__(self, registry: RoleRegistry):
        """
        初始化选择器

        Args:
            registry: 角色卡注册表
        """
        self.registry = registry
        logger.info("角色选择器初始化完成")

    def select(self, task: str, context: Optional[dict] = None) -> Tuple[str, float, dict]:
        """
        选择最合适的角色卡

        Args:
            task: 用户任务描述
            context: 上下文信息（可选），如历史任务、用户偏好等

        Returns:
            (角色名, 匹配度0-1, 选择理由)
        """
        if not task or not task.strip():
            return "生成", 0.3, {"reason": "空任务，默认用生成卡"}

        task_lower = task.lower()
        context = context or {}

        # 计算每张角色卡的匹配度
        scores: Dict[str, float] = {}
        reasons: Dict[str, dict] = {}

        for role_name, metadata in self.registry.get_all().items():
            score, reason = self._calculate_match_score(role_name, metadata, task_lower, context)
            scores[role_name] = score
            reasons[role_name] = reason

        # 找出匹配度最高的角色卡
        best_role = max(scores, key=scores.get)
        best_score = scores[best_role]
        best_reason = reasons[best_role]

        # 如果最高匹配度太低，用默认生成卡
        if best_score < 0.15:
            logger.info(f"所有角色卡匹配度都很低（最高 {best_score:.2f}），默认用生成卡")
            return "生成", 0.3, {"reason": "低匹配度，默认用生成卡", "all_scores": scores}

        logger.info(
            f"角色选择完成: {best_role} (匹配度 {best_score:.2f}) - {best_reason.get('reason', '')}"
        )
        return best_role, best_score, best_reason

    def _calculate_match_score(
        self,
        role_name: str,
        metadata: dict,
        task_lower: str,
        context: dict,
    ) -> Tuple[float, dict]:
        """
        计算角色卡与任务的匹配度

        Args:
            role_name: 角色名
            metadata: 角色卡元信息
            task_lower: 小写的任务描述
            context: 上下文

        Returns:
            (匹配度0-1, 匹配详情)
        """
        score = 0.0
        details = {
            "keyword_matches": [],
            "negative_matches": [],
            "type_match": False,
            "permission_match": True,
        }

        # 1. 适用场景关键词匹配（权重0.5）
        # 优化算法：只要匹配到至少1个关键词就给0.5基础分，匹配越多分越高
        scenarios = metadata.get("适用场景", [])
        keyword_match_count = 0
        for keyword in scenarios:
            if keyword.lower() in task_lower:
                keyword_match_count += 1
                details["keyword_matches"].append(keyword)

        if keyword_match_count > 0:
            # 匹配1个给0.5，每多匹配1个加0.1，上限1.0
            keyword_score = min(0.5 + (keyword_match_count - 1) * 0.1, 1.0)
        else:
            keyword_score = 0.0
        score += keyword_score * 0.5

        # 2. 不适用场景惩罚（权重-0.3）
        not_scenarios = metadata.get("not_适用场景", [])
        negative_match_count = 0
        for keyword in not_scenarios:
            if keyword.lower() in task_lower:
                negative_match_count += 1
                details["negative_matches"].append(keyword)

        if negative_match_count > 0:
            # 匹配1个给0.5，每多匹配1个加0.1，上限1.0
            negative_score = min(0.5 + (negative_match_count - 1) * 0.1, 1.0)
        else:
            negative_score = 0.0
        score -= negative_score * 0.3

        # 3. 任务类型模式匹配（权重0.4）
        type_score = self._match_task_type(role_name, task_lower)
        if type_score > 0:
            details["type_match"] = True
        score += type_score * 0.4

        # 4. 权限需求匹配（权重0.1）
        permission_score = self._match_permission(metadata, task_lower)
        details["permission_match"] = permission_score > 0
        score += permission_score * 0.1

        # 5. 上下文偏好加成（权重+0.1）
        if context.get("preferred_role") == role_name:
            score += 0.1
            details["context_preference"] = True

        # 确保分数在0-1之间
        score = max(0.0, min(1.0, score))

        details["score"] = score
        details["reason"] = f"关键词匹配{len(details['keyword_matches'])}个" + \
                            (f"，类型匹配" if details["type_match"] else "") + \
                            (f"，不适用关键词{len(details['negative_matches'])}个" if details["negative_matches"] else "")

        return score, details

    def _match_task_type(self, role_name: str, task_lower: str) -> float:
        """
        任务类型模式匹配

        根据任务的动词和名词模式判断任务类型。
        """
        # 定义任务类型模式
        type_patterns = {
            "文件夹管理员": [
                r"文件夹", r"目录", r"索引", r"同步", r"检查",
                r"管理员", r"统帅", r"调度", r"角色卡", r"世界书",
                r"反刍", r"蒸馏", r"项目记忆",
            ],
            "分析": [
                r"分析", r"统计", r"诊断", r"检查.*问题", r"对比",
                r"评估", r"看看.*结构", r"分析一下", r"有什么问题",
                r"数据统计", r"文本分析",
            ],
            "生成": [
                r"生成", r"创建", r"写", r"编写", r"设计",
                r"构建", r"实现", r"做一个", r"帮我写", r"帮我生成",
                r"代码", r"脚本", r"方案", r"文档",
            ],
            "老师": [
                r"教学", r"讲解", r"教程", r"指导", r"学习",
                r"解释", r"怎么用", r"如何", r"为什么", r"原理",
                r"入门", r"教我",
            ],
            "学生": [
                r"学习", r"模仿", r"练习", r"试错", r"验证",
                r"初稿", r"简单", r"批量", r"去重", r"分类",
            ],
            "匹配": [
                r"匹配", r"相似度", r"分类", r"归类", r"关联",
                r"聚类", r"对比.*相似",
            ],
            "小助手": [
                r"api", r"中转", r"数据搬运", r"用量", r"额度",
                r"调用.*接口", r"json", r"小助手",
            ],
            "每天更新": [
                r"连载", r"跑批", r"金庸", r"分天", r"每日更新",
                r"章节", r"钩子", r"起承转合", r"鹿鼎记", r"射雕",
            ],
            "脚本": [
                r"脚本", r"工具", r"代码复用", r"脚本管理", r"工具注册",
                r"写脚本", r"改脚本", r"调试脚本", r"军械库",
            ],
        }

        patterns = type_patterns.get(role_name, [])
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, task_lower):
                match_count += 1

        if not patterns:
            return 0.0

        return min(match_count / len(patterns) * 2, 1.0)  # 放大系数2，更容易匹配

    def _match_permission(self, metadata: dict, task_lower: str) -> float:
        """
        权限需求匹配

        判断任务需要的权限级别与角色卡权限是否匹配。
        """
        permission = metadata.get("permission_level", "L1")

        # 检测任务是否需要写权限
        need_write = any(
            keyword in task_lower
            for keyword in ["修改", "删除", "写入", "保存", "创建文件", "重命名", "移动"]
        )

        # 检测任务是否需要执行权限
        need_execute = any(
            keyword in task_lower
            for keyword in ["执行", "运行", "跑", "启动", "调用"]
        )

        # 权限匹配逻辑
        if permission == "L0" and need_write:
            return 0.0  # 只读角色不能做写操作
        if permission == "L0" and need_execute:
            return 0.3  # 只读角色做执行操作匹配度低
        if permission in ["L1", "L2", "L3"] and need_write:
            return 1.0  # 有写权限的角色做写操作完全匹配
        if permission in ["L1", "L2", "L3"]:
            return 0.8  # 有执行权限的角色默认匹配度高

        return 0.5

    def rank_all(self, task: str, context: Optional[dict] = None) -> List[Tuple[str, float, dict]]:
        """
        对所有角色卡按匹配度排序

        Args:
            task: 用户任务
            context: 上下文

        Returns:
            排序后的列表 [(角色名, 匹配度, 详情), ...]
        """
        results = []
        for role_name in self.registry.get_names():
            metadata = self.registry.get(role_name)
            score, reason = self._calculate_match_score(
                role_name, metadata, task.lower(), context or {}
            )
            results.append((role_name, score, reason))

        # 按匹配度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def explain_selection(self, task: str, context: Optional[dict] = None) -> str:
        """
        生成选择解释（用于调试和展示）

        Args:
            task: 用户任务
            context: 上下文

        Returns:
            选择解释文本
        """
        best_role, best_score, best_reason = self.select(task, context)
        all_ranked = self.rank_all(task, context)

        lines = [
            f"=== 角色选择解释 ===",
            f"任务: {task[:100]}{'...' if len(task) > 100 else ''}",
            f"",
            f"✅ 选择: {best_role} (匹配度 {best_score:.2f})",
            f"   理由: {best_reason.get('reason', '')}",
            f"",
            f"📊 所有角色卡匹配度排名:",
        ]

        for i, (role, score, reason) in enumerate(all_ranked[:5], 1):
            marker = "⭐" if role == best_role else "  "
            lines.append(f"  {marker} {i}. {role}: {score:.2f} - {reason.get('reason', '')}")

        return "\n".join(lines)
