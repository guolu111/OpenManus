"""
ask_enhancer_tool.py — OpenManus 自定义提问增强工具：把模糊提问增强成结构化高质量提问。

设计原则（用户铁律 · 2026-09-05）：
1. 调用三个标签（豆包/千问/智谱）前，先用本工具把问题增强成高质量提问。
2. 四要素结构：背景/目标/约束/输出格式，缺了自动补全。
3. 短提问（<50字）自动补充要求。
4. 可选生成澄清问题（信息不足时）。
5. 纯本地处理，不耗API。

依赖：提问机器 _ask.py 的 enhance() 和 clarify() 函数。
"""

import os
import sys
from typing import ClassVar, Dict, List, Optional

from app.tool.base import BaseTool, ToolResult

# 提问机器路径
ASK_DIR = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\提问机器"
if ASK_DIR not in sys.path:
    sys.path.insert(0, ASK_DIR)

# 导入提问机器的核心函数
try:
    from _ask import enhance, clarify
    ASK_AVAILABLE = True
except ImportError:
    ASK_AVAILABLE = False


def _local_enhance(intent: str) -> str:
    """本地降级版提问增强（_ask.py导入失败时使用）。"""
    raw = (intent or "").strip()
    if not raw:
        return "[错误] 提问为空"
    if len(raw) < 50:
        raw = f"{raw}\n【补充要求】请补充具体背景、目标、输出格式和约束条件，然后给出完整分析。"
    tpl = (
        f"【角色】你是该领域的资深专家。\n"
        f"【背景】{raw}\n"
        f"【目标】请围绕上述内容，明确要解决的问题，给出结构化、分步骤、可执行的结论。\n"
        f"【约束】基于事实，不编造；如信息不足请明确指出。\n"
        f"【输出格式】结构化分点，关键结论明确，直接可用。"
    )
    # 确保四要素齐全
    required = ["【背景】", "【目标】", "【约束】", "【输出格式】"]
    for tag in required:
        if tag not in tpl:
            tpl += f"\n{tag} 无特殊要求。"
    return tpl + "\n\n【要求】请给出结构化、分步骤、可执行的结论，不要泛泛而谈。"


def _local_clarify(intent: str) -> List[str]:
    """本地降级版澄清问题生成。"""
    questions = []
    keys = ["时间", "目标", "范围", "预算", "主体"]
    missing = [k for k in keys if k not in intent]
    for m in missing[:2]:
        questions.append(f"请补充：{m}？（影响回答方向）")
    return questions


class AskEnhancer(BaseTool):
    """提问增强工具：把模糊/口语化提问增强成结构化高质量提问。

    当需要调用三个标签（豆包/千问/智谱）进行深度思考或交叉验证前，
    先用本工具把原始提问增强成四要素结构（背景/目标/约束/输出格式），
    提高标签回答的准确率和完整性。
    参数: intent=原始提问(必填); clarify=是否生成澄清问题(可选,默认false)。
    """

    name: str = "ask_enhancer"
    description: str = (
        "提问增强工具。把模糊/口语化的提问增强成结构化高质量提问（四要素：背景/目标/约束/输出格式），"
        "供调用三个标签（豆包/千问/智谱）深度思考时使用。"
        "短提问自动补全，可选生成澄清问题。纯本地运行不耗API。"
        "参数: intent=原始提问(必填); clarify=是否生成澄清问题(可选,默认false)。"
    )
    parameters: ClassVar[Dict] = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "原始提问/任务描述（模糊或口语化均可）",
            },
            "clarify": {
                "type": "boolean",
                "description": "是否生成澄清问题（信息不足时提示补充），默认false",
                "default": False,
            },
        },
        "required": ["intent"],
    }

    async def execute(self, intent: str, clarify: bool = False, **kwargs) -> ToolResult:
        """执行提问增强：四要素结构化 + 可选澄清问题。"""
        if not intent or not intent.strip():
            return ToolResult(output="（空提问，无需增强）", enhanced="", questions=[])

        # 调用提问机器或本地降级
        if ASK_AVAILABLE:
            enhanced = enhance(intent)
            source = "提问机器_ask.py"
        else:
            enhanced = _local_enhance(intent)
            source = "本地降级版"

        # 生成澄清问题
        questions = []
        if clarify:
            if ASK_AVAILABLE:
                questions = clarify_func(intent) if callable(clarify_func) else _local_clarify(intent)
            else:
                questions = _local_clarify(intent)

        result = {
            "original": intent,
            "enhanced": enhanced,
            "questions": questions,
            "source": source,
        }

        output_lines = [
            f"原始提问: {intent}",
            f"增强来源: {source}",
            "",
            "【增强后提问】",
            enhanced,
        ]
        if questions:
            output_lines.append("")
            output_lines.append("【澄清问题】")
            for i, q in enumerate(questions, 1):
                output_lines.append(f"  {i}. {q}")

        return ToolResult(output="\n".join(output_lines), **result)


# clarify可能和参数名冲突，用别名
try:
    from _ask import clarify as clarify_func
except ImportError:
    clarify_func = None
