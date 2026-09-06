"""
自动记忆提取器（AutoMemoryExtractor）
每轮对话结束后，自动调用 LLM 分析对话内容，提取关键信息并存入长期记忆。

参考 Mem0 的设计思路：LLM 自动从对话中提取事实，不需要 Agent 主动调用 remember。
但比 Mem0 轻量：纯文件存储、不依赖向量数据库、不花额外服务。

提取规则：
1. 只提取用户明确表达的偏好、决定、配置、重要事件、踩过的坑
2. 不提取临时的、一次性的、无关紧要的内容
3. 自动去重：相同 key 的记忆不重复存储
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger
from app.schema import Message
from app.tool.memory_tool import MemoryTool, _load_store


AUTO_EXTRACT_SYSTEM_PROMPT = """你是一个记忆提取器。你的任务是从对话中提取需要长期记住的关键信息。

## 提取规则
1. 只提取以下类型的信息：
   - facts（事实记忆）：用户偏好、项目配置、常用路径、API密钥位置、环境设置
   - episodes（情景记忆）：重要决定、任务结果、踩过的坑、异常事件、里程碑
   - skills（程序性记忆）：常用命令、工作流、代码片段、操作步骤、脚本用法
2. 不提取：临时的问候、一次性的请求、无关紧要的闲聊、已经在记忆里的重复信息
3. 每条记忆的 key 要简短描述性（如"用户浏览器偏好"、"神雕侠侣跑批完成"），value 要详细
4. 如果对话中没有值得长期记住的信息，返回空数组

## 输出格式
严格返回 JSON 数组，不要包含任何其他文字：
[
  {"store": "facts", "key": "简短标题", "value": "详细内容"},
  {"store": "episodes", "key": "简短标题", "value": "详细内容"}
]

## 对话内容
{conversation}
"""


class AutoMemoryExtractor:
    """自动记忆提取器：每轮对话结束后自动提取关键信息并存入长期记忆。"""

    def __init__(self, llm, memory_tool: Optional[MemoryTool] = None):
        self.llm = llm
        self.memory_tool = memory_tool or MemoryTool()

    def _format_conversation(self, messages: List[Message]) -> str:
        """将消息列表格式化为可读的对话文本。"""
        lines = []
        for msg in messages:
            role = msg.role
            content = msg.content or ""
            # 跳过空内容和系统消息（系统消息是prompt，不是对话内容）
            if not content or role == "system":
                continue
            # 截断过长的工具输出
            if role == "tool" and len(content) > 500:
                content = content[:500] + "...(已截断)"
            role_label = {
                "user": "用户",
                "assistant": "助手",
                "tool": "工具",
            }.get(role, role)
            lines.append(f"[{role_label}]: {content}")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> List[Dict[str, str]]:
        """解析 LLM 返回的 JSON 数组，兼容各种格式。"""
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 块
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个 [ 到最后一个 ] 之间的内容
        start = response.find("[")
        end = response.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(response[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(f"自动记忆提取：无法解析 LLM 响应为 JSON: {response[:200]}")
        return []

    def _validate_memory_item(self, item: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """验证单条记忆条目，返回 (store, key, value) 或 None。"""
        if not isinstance(item, dict):
            return None
        store = item.get("store", "").lower()
        key = item.get("key", "").strip()
        value = item.get("value", "").strip()
        if store not in ("facts", "episodes", "skills"):
            return None
        if not key or not value:
            return None
        # 过滤掉太短或无意义的记忆
        if len(value) < 5:
            return None
        return (store, key, value)

    def _is_duplicate(self, store: str, key: str, value: str) -> bool:
        """检查记忆是否已存在（key 相同或 value 高度相似）。"""
        existing = _load_store(store)
        # key 完全相同
        if key in existing:
            return True
        # value 高度相似（简单的包含检查）
        for existing_key, existing_val in existing.items():
            existing_content = existing_val.get("content", "") if isinstance(existing_val, dict) else str(existing_val)
            if value in existing_content or existing_content in value:
                if len(value) > 20 and len(existing_content) > 20:
                    return True
        return False

    async def extract_and_store(self, messages: List[Message]) -> Dict[str, Any]:
        """
        从对话中提取关键信息并存入长期记忆。

        Args:
            messages: 当前对话的所有消息

        Returns:
            dict: {extracted: 提取数量, stored: 实际存储数量, skipped: 跳过数量, items: 存储的记忆列表}
        """
        conversation = self._format_conversation(messages)
        if not conversation:
            return {"extracted": 0, "stored": 0, "skipped": 0, "items": [], "reason": "对话为空"}

        # 对话太短不提取（少于3条消息）
        if len([m for m in messages if m.content and m.role != "system"]) < 3:
            return {"extracted": 0, "stored": 0, "skipped": 0, "items": [], "reason": "对话太短"}

        try:
            # 调用 LLM 提取
            prompt = AUTO_EXTRACT_SYSTEM_PROMPT.format(conversation=conversation)
            response = await self.llm.ask(
                messages=[Message.user_message("请提取以下对话中的关键记忆信息。")],
                system_msgs=[Message.system_message(prompt)],
                stream=False,
                temperature=0,
            )

            # 解析结果
            items = self._parse_llm_response(response)
            if not items:
                return {"extracted": 0, "stored": 0, "skipped": 0, "items": [], "reason": "LLM未返回有效记忆"}

            # 验证、去重、存储
            stored_items = []
            skipped = 0
            for item in items:
                validated = self._validate_memory_item(item)
                if not validated:
                    skipped += 1
                    continue
                store, key, value = validated
                if self._is_duplicate(store, key, value):
                    skipped += 1
                    continue
                # 存入记忆
                result = await self.memory_tool.execute(
                    action="remember", store=store, key=key, value=value
                )
                if result.error:
                    logger.warning(f"自动记忆提取：存储失败 [{store}] {key}: {result.error}")
                    skipped += 1
                else:
                    stored_items.append({"store": store, "key": key, "value": value})

            logger.info(
                f"🧠 自动记忆提取完成：提取 {len(items)} 条，存储 {len(stored_items)} 条，跳过 {skipped} 条"
            )
            return {
                "extracted": len(items),
                "stored": len(stored_items),
                "skipped": skipped,
                "items": stored_items,
            }

        except Exception as e:
            logger.error(f"自动记忆提取失败：{e}")
            return {"extracted": 0, "stored": 0, "skipped": 0, "items": [], "error": str(e)}
