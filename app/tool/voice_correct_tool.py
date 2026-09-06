"""
voice_correct_tool.py — OpenManus 自定义语音纠错工具：L1固定词对 + L2拼音模糊匹配。

设计原则（用户铁律 · 2026-09-05）：
1. 纯本地纠错，不耗API（90%的错字用本地词库搞定）。
2. L1：固定词对快速替换（用户专属：前文→千问、之圃→质谱等）。
3. L2：拼音模糊匹配（维护正确词库，自动识别音近错误，不需要手动加每一个错字对）。
4. 纠错结果可反馈：用户修改后自动学习新词对。
5. 低置信度标注，不强行替换。

依赖：pypinyin（拼音转换）、_confusion_data.py（用户专属词库）。
"""

import os
import re
import sys
from typing import ClassVar, Dict, List, Optional, Tuple

from app.tool.base import BaseTool, ToolResult

# 项目路径
PROJECT_ROOT = r"D:\360Downloads\金庸\一念永恒"
VOICE_CORRECT_DIR = os.path.join(PROJECT_ROOT, "一念永恒小说", "语音纠正")

# 把语音纠正目录加入path，以便导入_confusion_data
if VOICE_CORRECT_DIR not in sys.path:
    sys.path.insert(0, VOICE_CORRECT_DIR)

# L1：用户专属固定词对（从_confusion_data.py导入）
# 注意：只用USER_CONFUSIONS（用户专属），不用GENERAL_CONFUSIONS（通用词对太激进，容易把正确的"的"换成"得"）
# 通用错字由L2拼音模糊匹配覆盖
try:
    from _confusion_data import USER_CONFUSIONS
    L1_PAIRS = USER_CONFUSIONS
except ImportError:
    # 降级：内置核心用户专属词对
    L1_PAIRS = [
        ("资道", "知道"), ("做业", "作业"), ("因该", "应该"),
        ("前文", "千问"), ("之圃", "质谱"), ("骨骼", "谷歌"),
        ("觉控力", "控制力"), ("栏板", "面板"), ("分部做", "分步做"),
        ("四目", "四幕"), ("大喜", "打戏"), ("预料", "语料"),
    ]

# L2：正确词库（项目专有名词，拼音模糊匹配用）
# 只需要维护"正确写法"，工具自动匹配所有音近错误
CORRECT_WORDS = [
    # API/模型相关
    "千问", "质谱", "智谱", "谷歌", "豆包", "硅基", "DeepSeek",
    "OpenManus", "最强大脑", "gcli", "bridge",
    # 项目相关
    "一念永恒", "金庸", "鹿鼎记", "神雕", "角色卡", "世界书",
    "任务面板", "任务看板", "跑批", "分天版", "中转API",
    "语音纠正", "语音纠错", "混淆词库",
    # 角色卡/将军
    "管理员", "每天更新", "分析", "生成", "学生", "匹配",
    "小助手", "脚本", "将军", "统帅",
    # 技术术语
    "MCP", "自定义工具", "断点续跑", "自愈", "封控", "风控",
    "历史会话", "有头模式", "无头模式",
]


def _to_pinyin(text: str) -> str:
    """把中文转成拼音字符串（不带声调），用于模糊匹配。"""
    try:
        from pypinyin import lazy_pinyin
        return "".join(lazy_pinyin(text))
    except ImportError:
        # pypinyin未安装时降级：只做L1
        return ""


def _pinyin_similarity(p1: str, p2: str) -> float:
    """计算两个拼音字符串的相似度（0~1）。"""
    if not p1 or not p2:
        return 0.0
    if p1 == p2:
        return 1.0
    # 简单的编辑距离相似度
    len1, len2 = len(p1), len(p2)
    if abs(len1 - len2) > max(len1, len2) * 0.5:
        return 0.0
    # 动态规划计算编辑距离
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if p1[i-1] == p2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    distance = dp[len1][len2]
    max_len = max(len1, len2)
    return 1.0 - distance / max_len


class VoiceCorrect(BaseTool):
    """语音转文字纠错工具：L1固定词对替换 + L2拼音模糊匹配。

    当用户输入是语音转文字结果、可能含同音/音近错字时使用本工具。
    纯本地纠错，不耗API。返回纠错后的文本和替换记录。
    参数: text=待纠错文本(必填); context=上下文(可选,用于提高准确率)。
    """

    name: str = "voice_correct"
    description: str = (
        "语音转文字纠错工具。对语音识别结果中的同音/音近错字进行纠正。"
        "两层纠错：L1固定词对快速替换（用户专属，如前文→千问、之圃→质谱）；"
        "L2拼音模糊匹配（维护正确词库，自动识别音近错误）。"
        "纯本地运行不耗API。参数: text=待纠错文本(必填); context=上下文语境(可选)。"
    )
    parameters: ClassVar[Dict] = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "待纠错的语音转文字文本",
            },
            "context": {
                "type": "string",
                "description": "上下文语境（可选，如当前讨论的话题、打开的文件名），用于提高纠错准确率",
            },
        },
        "required": ["text"],
    }

    async def execute(self, text: str, context: Optional[str] = None, **kwargs) -> ToolResult:
        """执行纠错：L1固定词对 → L2拼音模糊匹配 → 返回结果。"""
        if not text or not text.strip():
            return ToolResult(output="（空文本，无需纠错）", replacements=[])

        original = text
        replacements = []

        # ===== L1：固定词对快速替换 =====
        corrected = text
        for wrong, right in L1_PAIRS:
            if wrong in corrected:
                count = corrected.count(wrong)
                corrected = corrected.replace(wrong, right)
                replacements.append({
                    "layer": "L1",
                    "wrong": wrong,
                    "right": right,
                    "count": count,
                    "confidence": "high",
                })

        # ===== L2：拼音模糊匹配 =====
        pinyin_available = _to_pinyin("测试") != ""
        if pinyin_available:
            # 预计算正确词库的拼音
            word_pinyins = [(w, _to_pinyin(w)) for w in CORRECT_WORDS if len(w) >= 2]

            # 对文本中的2~4字词组做拼音匹配
            words_found = set()
            for length in [4, 3, 2]:  # 从长到短匹配
                for i in range(len(corrected) - length + 1):
                    segment = corrected[i:i+length]
                    # 跳过已经是正确词的、纯英文/数字的
                    if segment in CORRECT_WORDS:
                        continue
                    if not re.search(r'[\u4e00-\u9fff]', segment):
                        continue
                    seg_pinyin = _to_pinyin(segment)
                    if not seg_pinyin:
                        continue
                    # 找最匹配的正确词
                    best_match = None
                    best_score = 0.0
                    for word, wp in word_pinyins:
                        if word == segment:
                            continue
                        score = _pinyin_similarity(seg_pinyin, wp)
                        if score > best_score:
                            best_score = score
                            best_match = word
                    # 相似度>0.85才替换（高置信度）
                    if best_match and best_score >= 0.85 and segment not in words_found:
                        words_found.add(segment)
                        corrected = corrected.replace(segment, best_match)
                        replacements.append({
                            "layer": "L2",
                            "wrong": segment,
                            "right": best_match,
                            "pinyin_similarity": round(best_score, 3),
                            "confidence": "medium" if best_score < 0.95 else "high",
                        })

        # ===== 生成结果 =====
        changed = corrected != original
        result = {
            "original": original,
            "corrected": corrected,
            "changed": changed,
            "replacements": replacements,
            "layers_used": ["L1"] + (["L2"] if pinyin_available else ["L2(pypinyin未安装，已跳过)"]),
        }

        output_lines = [
            f"原文: {original}",
            f"纠错: {corrected}",
            f"变更: {'是' if changed else '否'}",
        ]
        if replacements:
            output_lines.append("替换记录:")
            for r in replacements:
                if r["layer"] == "L1":
                    output_lines.append(f"  L1 {r['wrong']} → {r['right']} (×{r['count']})")
                else:
                    output_lines.append(f"  L2 {r['wrong']} → {r['right']} (拼音相似度{r['pinyin_similarity']})")

        return ToolResult(output="\n".join(output_lines), **result)
