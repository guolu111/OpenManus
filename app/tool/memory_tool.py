"""
长期记忆工具（MemoryTool）
为 OpenManus 增加跨会话持久化记忆能力，参考 Manus 商业版"文件系统即终极上下文"哲学。

三类记忆：
  - facts    事实记忆：用户偏好、项目配置、常用路径、API密钥位置
  - episodes 情景记忆：跑批结果、重要事件、踩过的坑、任务完成状态
  - skills   程序性记忆：常用脚本、工作流、代码片段、操作步骤

四个操作：
  - remember  存记忆（action=remember, store, key, value）
  - recall    查记忆（action=recall, store, query）
  - forget    删记忆（action=forget, store, key）
  - list      列记忆（action=list, store）

存储位置：项目根目录/memory/ 下的三个 JSON 文件
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.tool.base import BaseTool, ToolResult


MEMORY_DIR = "memory"
STORES = ("facts", "episodes", "skills")


def _ensure_dir() -> None:
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)


def _store_path(store_type: str) -> str:
    return os.path.join(MEMORY_DIR, f"{store_type}.json")


def _load_store(store_type: str) -> Dict[str, Any]:
    path = _store_path(store_type)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_store(store_type: str, data: Dict[str, Any]) -> None:
    _ensure_dir()
    path = _store_path(store_type)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _search(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """简单关键词检索：key 或 content 包含 query 即命中。后续可升级为向量检索。"""
    if not query:
        return data
    q = query.lower()
    results = {}
    for key, val in data.items():
        content = val.get("content", "") if isinstance(val, dict) else str(val)
        if q in key.lower() or q in str(content).lower():
            results[key] = val
    return results


class MemoryTool(BaseTool):
    name: str = "memory"
    description: str = (
        "长期记忆工具：跨会话持久化存储和检索关键信息。"
        "三类记忆：facts(事实/偏好/配置)、episodes(事件/跑批结果/踩坑)、skills(脚本/工作流/代码片段)。"
        "遇到用户偏好、项目配置、常用路径、重要决定、跑批结果、踩过的坑时，主动用 remember 记住；"
        "需要回忆历史信息时，主动用 recall 检索。记忆会持久化保存，下次会话还能查到。"
    )
    parameters: Optional[dict] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["remember", "recall", "forget", "list"],
                "description": "remember=存记忆, recall=查记忆, forget=删记忆, list=列出所有记忆的key",
            },
            "store": {
                "type": "string",
                "enum": ["facts", "episodes", "skills"],
                "description": "记忆分类：facts=事实/偏好/配置, episodes=事件/跑批结果/踩坑, skills=脚本/工作流/代码片段。默认facts",
            },
            "key": {
                "type": "string",
                "description": "记忆的关键词/标题（remember/forget时必填，简短描述性名称）",
            },
            "value": {
                "type": "string",
                "description": "记忆的内容（remember时必填，详细信息）",
            },
            "query": {
                "type": "string",
                "description": "搜索关键词（recall时用，模糊匹配key和内容）",
            },
        },
        "required": ["action"],
    }

    async def execute(
        self,
        action: str,
        store: str = "facts",
        key: str = None,
        value: str = None,
        query: str = None,
        **kwargs,
    ) -> ToolResult:
        # 兼容 store_type 别名（LLM 可能用 store_type 代替 store）
        if "store_type" in kwargs and kwargs["store_type"]:
            store = kwargs["store_type"]
        if store not in STORES:
            return ToolResult(error=f"未知记忆分类 '{store}'，可选: {', '.join(STORES)}")

        if action == "remember":
            if not key or not value:
                return ToolResult(error="remember 需要 key 和 value 参数")
            data = _load_store(store)
            data[key] = {
                "content": value,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            _save_store(store, data)
            return ToolResult(output=f"✅ 已记住 [{store}] {key}")

        elif action == "recall":
            data = _load_store(store)
            results = _search(data, query) if query else data
            if not results:
                return ToolResult(output=f"📭 [{store}] 没有找到相关记忆" + (f"（关键词: {query}）" if query else ""))
            output_lines = [f"🧠 [{store}] 检索到 {len(results)} 条记忆："]
            for k, v in results.items():
                content = v.get("content", "") if isinstance(v, dict) else str(v)
                ts = v.get("timestamp", "") if isinstance(v, dict) else ""
                output_lines.append(f"  • {k}: {content}" + (f"  ({ts})" if ts else ""))
            return ToolResult(output="\n".join(output_lines))

        elif action == "forget":
            if not key:
                return ToolResult(error="forget 需要 key 参数")
            data = _load_store(store)
            if key in data:
                del data[key]
                _save_store(store, data)
                return ToolResult(output=f"🗑️ 已删除记忆 [{store}] {key}")
            return ToolResult(output=f"📭 [{store}] 没有找到 '{key}'，无需删除")

        elif action == "list":
            data = _load_store(store)
            if not data:
                return ToolResult(output=f"📭 [{store}] 暂无记忆")
            keys = list(data.keys())
            output_lines = [f"📋 [{store}] 共 {len(keys)} 条记忆："]
            for i, k in enumerate(keys, 1):
                v = data[k]
                ts = v.get("timestamp", "") if isinstance(v, dict) else ""
                output_lines.append(f"  {i}. {k}" + (f"  ({ts})" if ts else ""))
            return ToolResult(output="\n".join(output_lines))

        else:
            return ToolResult(error=f"未知操作 '{action}'，可选: remember, recall, forget, list")
