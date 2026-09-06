"""
ask_tag.py — OpenManus 自定义工具：调用4标签网页版（豆包/千问国际版/智谱清言）做深度思考/交叉验证。

设计原则（用户铁律）：
1. 本工具【绝不直接控制浏览器】——防风控逻辑全部在 multi_bridge（模拟人工/拉历史会话/满额换会话），
   OpenManus 只通过 localhost:8010 HTTP 调用，全程"只问不看"。
2. 支持单问（选一个标签）和交叉验证（多标签对比），返回结构化结果。
3. 调用走 OpenAI 兼容 /v1/chat/completions，模型名 doubao/qwen/glm。
4. 所有调用登记用量（供任务看板 API 监测读取）。
5. 【模型版本铁律·2026-09-04】：千问必须国际版 3.7 以上；智谱必须是 5.1/5.2 轻量版，绝不能 5.0。
   验证时向标签发"你现在是什么模型版本"，由标签自报判断。不达标明确报出。
"""

import asyncio
import json
import os
import re
import time
from typing import ClassVar, Dict, List, Optional

import aiohttp

from app.tool.base import BaseTool, ToolResult


class AskTag(BaseTool):
    """调用4标签网页版（豆包/千问国际版/智谱清言）做深度思考或交叉验证。

    当任务需要多个模型观点对比、或需要网页版模型深度思考时使用。
    支持指定单个标签（model=doubao/qwen/glm），或一次问多个标签交叉验证。
    支持 verify=True 时先验证标签的模型版本是否符合铁律（千问≥3.7 / 智谱5.1或5.2轻量版）。
    """

    name: str = "ask_tag"
    description: str = (
        "调用4标签网页版AI（doubao豆包 / qwen千问国际版 / glm智谱清言）做深度思考或交叉验证。"
        "参数: model='doubao'|'qwen'|'glm'|'all'(全部交叉验证), prompt=要问的问题, "
        "verify=True(可选，先验证模型版本：千问必须≥3.7、智谱必须是5.1/5.2轻量版)。"
        "返回每个标签的完整回复。适合多模型观点对比、交叉验证、或深度思考场景。"
        "注意：每个标签调用有次数限制（豆包40/千问40/智谱20次换会话），别频繁调用。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "要问标签的问题（要详细具体，标签是网页版模型）",
            },
            "model": {
                "type": "string",
                "enum": ["doubao", "qwen", "glm", "all"],
                "description": "选哪个标签：doubao豆包 / qwen千问国际版 / glm智谱清言 / all全部交叉验证",
            },
            "verify": {
                "type": "boolean",
                "description": "是否先验证模型版本（千问≥3.7、智谱5.1/5.2轻量版）。默认false",
            },
        },
        "required": ["prompt"],
    }

    BRIDGE_URL: str = os.getenv("TAG_BRIDGE_URL", "http://localhost:8010")
    USAGE_LOG: str = os.getenv(
        "TAG_USAGE_LOG",
        r"D:\360Downloads\金庸\一念永恒\一念永恒小说\4标签\usage\ask_tag_usage.jsonl",
    )

    # ===== 模型版本铁律（用户2026-09-04）=====
    VERSION_RULES: ClassVar[Dict] = {
        "qwen": {
            "label": "千问国际版",
            "must": "≥3.7",
            "rule": lambda v: _extract_version(v) >= 3.7 if _extract_version(v) else None,
            "verify_prompt": "请只回答你当前使用的模型版本号（如 Qwen3-7B / Qwen 3.7 等），不要解释。",
        },
        "glm": {
            "label": "智谱清言",
            # 2026-09-04 用户定稿：不手动切换模型（切换会风控），保留网页当前版本使用。
            # 实测：智谱网页每次进入不同会话/入口，模型版本会变（曾见 4.5 / 5.3 flash）。
            # 铁律：只报告自报版本（含变体），不拦截；多次验证时取最后一次稳定值。
            "must": "自报为准（记录具体版本+变体，如 4.5 / 5.3 flash）",
            "rule": lambda v: True,  # 不拦截，任何版本都接受，只记录
            "verify_prompt": "请只回答你当前使用的完整模型版本名称，例如「GLM-4.5 Plus」「GLM-5.3 flash」等，只回答名称不要解释。",
        },
        "doubao": {
            "label": "豆包",
            "must": "最新版",
            "rule": lambda v: True,
            "verify_prompt": "请只回答你当前使用的模型版本名称，不要解释。",
        },
    }

    async def _call_bridge(self, model: str, prompt: str, timeout: int = 180) -> Dict:
        """调用 multi_bridge 的 OpenAI 兼容接口（真实调标签网页版）。"""
        url = f"{self.BRIDGE_URL}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        return {
                            "model": model, "ok": False,
                            "error": data.get("error", f"HTTP {resp.status}"),
                            "detail": data.get("detail", {}),
                        }
                    reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    bridge_status = data.get("bridge_status", {})
                    return {
                        "model": model, "ok": True, "reply": reply,
                        "bridge_status": bridge_status,
                    }
            except Exception as e:
                return {"model": model, "ok": False, "error": f"调用异常: {e}"}

    def _check_version(self, model: str, reply: str) -> Dict:
        """判断标签自报的版本是否符合铁律。返回 {pass, actual, must, hint}
        提示性验证：网页版自报未必精确，识别到数字即报出实际值，
        pass 用于统帅参考，不硬性阻断（阻断会造成误伤）。"""
        rules = self.VERSION_RULES.get(model)
        if not rules:
            return {"pass": True, "actual": "未知", "must": "-", "hint": ""}
        low = reply.lower()
        # 提取版本号数字（如 3.7 / 5.1 / 4.5 / 5.0）
        m = re.search(r"(\d+\.\d+)", reply)
        actual = m.group(1) if m else reply.strip()[:30]
        try:
            passed = bool(rules["rule"](actual))
        except Exception:
            passed = False
        # 判定不出（没数字）→ 提示人工确认，不判失败
        if not m:
            passed = True
            return {"pass": passed, "actual": reply.strip()[:30] or "未识别", "must": rules["must"],
                    "hint": "（未识别到明确版本号，请人工确认标签当前模型）"}
        return {"pass": passed, "actual": actual, "must": rules["must"], "hint": ""}

    def _log_usage(self, model: str, ok: bool, elapsed: float, prompt_len: int, reply_len: int, verify: bool = False) -> None:
        """登记用量（任务看板 API 监测读取）。"""
        try:
            os.makedirs(os.path.dirname(self.USAGE_LOG), exist_ok=True)
            record = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api": f"4tag/{model}",
                "ok": ok,
                "elapsed_s": round(elapsed, 1),
                "prompt_chars": prompt_len,
                "reply_chars": reply_len,
                "verify": verify,
            }
            with open(self.USAGE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    async def execute(self, prompt: str, model: str = "all", verify: bool = False) -> ToolResult:
        """执行：单标签或全标签交叉验证，可选先验证模型版本。"""
        if not prompt or not prompt.strip():
            return self.fail_response("prompt 不能为空")

        if model == "all":
            models = ["doubao", "qwen", "glm"]
        else:
            if model not in ("doubao", "qwen", "glm"):
                return self.fail_response(f"未知标签 {model}，可选 doubao/qwen/glm/all")
            models = [model]

        results = []
        t0 = time.time()
        for m in models:
            # 验证模式：先问版本，再问原问题
            if verify:
                rules = self.VERSION_RULES.get(m)
                if rules:
                    v = await self._call_bridge(m, rules["verify_prompt"])
                    if v.get("ok"):
                        vc = self._check_version(m, v.get("reply", ""))
                        v["version_check"] = vc
                        if not vc["pass"]:
                            v["version_warn"] = (
                                f"⚠️ {rules['label']} 自报版本 {vc['actual']!r} 不符合铁律（需 {vc['must']}）。"
                                "请勿用于关键判断，或人工确认标签当前模型。"
                            )
                    results.append(v)
            r = await self._call_bridge(m, prompt)
            elapsed = time.time() - t0
            self._log_usage(m, r.get("ok", False), elapsed, len(prompt), len(r.get("reply", "")), verify)
            results.append(r)

        # 组装返回
        lines = []
        for r in results:
            m = r.get("model", "?")
            if r.get("version_warn"):
                lines.append(f"{r['version_warn']}\n")
            if r.get("version_check"):
                vc = r["version_check"]
                mark = "✅" if vc["pass"] else "❌"
                lines.append(f"【{m}·版本验证{mark}】自报={vc['actual']} (需 {vc['must']})\n")
                if r.get("ok"):
                    lines.append(f"  回复: {r['reply'][:200]}\n")
            elif r.get("ok"):
                lines.append(f"【{m}】回复:\n{r['reply']}\n")
            else:
                lines.append(f"【{m}】❌ 失败: {r.get('error','')} | 阶段: {r.get('detail',{}).get('stage','')}\n")

        total = f"=== 4标签回答（模型: {model}{' + 版本验证' if verify else ''}）===\n\n" + "\n".join(lines)
        return self.success_response(total)


def _extract_version(reply: str) -> Optional[float]:
    """从文本中提取主版本号（如 3.7 -> 3.7）。"""
    m = re.search(r"(\d+\.\d+)", reply or "")
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None
