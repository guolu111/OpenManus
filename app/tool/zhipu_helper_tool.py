"""
zhipu_helper_tool.py — OpenManus 工具：调用智谱 GLM API（官方直连，OpenAI 兼容）。

设计（2026-09-05 · 多模型分工 · 用户铁律）：
1. 复用项目已有 中转API/configs/zhipu_config.json 的 key + base_url，不重复配置。
2. 支持两个模型（同一个 base_url，只是 model 名不同）：
   - glm-4-flash（免费主力，底层执行器：JSON/搬运/去重/简单整理）
   - glm-4.5-air（收费，中层主力：翻译/格式整理/监督/初稿）
3. 用法：model='free'|'air'（默认 free），prompt=要干的话。
4. 每次调用登记用量（供任务看板 API 监测读取）。
5. 本工具只"问"，不做决策——决策永远留给谷歌大脑。
"""

import asyncio
import io
import json
import os
import time
from typing import ClassVar, Dict, Optional

from app.tool.base import BaseTool, ToolResult


class ZhipuHelper(BaseTool):
    """调用智谱 GLM API（glm-4-flash 免费 / glm-4.5-air 收费）做粗活外包。

    适合翻译、格式整理、监督、初稿、批量搬运、JSON 生成等中低频粗活；
    决策、规划、最终验收永远由谷歌大脑完成，本工具只是"手脚"。
    """

    name: str = "zhipu_helper"
    description: str = (
        "调用智谱GLM API做粗活外包。model='free'=glm-4-flash(免费,底层:JSON/搬运/去重/简单整理)，"
        "model='air'=glm-4.5-air(收费,中层:翻译/格式整理/监督/初稿)。"
        "参数: prompt=要处理的内容(详细具体), model='free'|'air'(默认free)。"
        "返回该模型对 prompt 的处理结果。注意：它只干粗活，不做复杂决策。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "要交给智谱处理的内容（翻译/整理/监督/初稿/JSON等）",
            },
            "model": {
                "type": "string",
                "enum": ["free", "air"],
                "description": "free=glm-4-flash(免费) / air=glm-4.5-air(收费中层主力)",
            },
        },
        "required": ["prompt"],
    }

    # 项目已有智谱配置（key/base_url 都在里面，不重复写）
    CFG_PATH: ClassVar[str] = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\中转API\configs\zhipu_config.json"
    USAGE_LOG: ClassVar[str] = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\4标签\usage\zhipu_helper_usage.jsonl"
    MODEL_MAP: ClassVar[Dict[str, str]] = {
        "free": "glm-4-flash",   # 免费主力（底层执行器）
        "air": "glm-4.5-air",    # 收费中层主力
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = None
        self._load_config()

    def _load_config(self) -> None:
        """从项目已有配置读取 key/base_url（不重复配置）。"""
        try:
            with io.open(self.CFG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            self._base_url = cfg.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
            self._api_key = cfg.get("api_key", "")
        except Exception:
            self._base_url = "https://open.bigmodel.cn/api/paas/v4"
            self._api_key = ""

    def _get_client(self):
        """懒加载 openai client（尽量复用连接）。"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self._base_url, api_key=self._api_key, timeout=300)
        return self._client

    def _log_usage(self, model: str, ok: bool, elapsed: float, prompt_len: int, reply_len: int) -> None:
        """登记用量（任务看板 API 监测读取）。"""
        try:
            os.makedirs(os.path.dirname(self.USAGE_LOG), exist_ok=True)
            record = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api": f"zhipu/{model}",
                "ok": ok,
                "elapsed_s": round(elapsed, 1),
                "prompt_chars": prompt_len,
                "reply_chars": reply_len,
            }
            with open(self.USAGE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    async def execute(self, prompt: str, model: str = "free") -> ToolResult:
        """执行：调智谱 GLM API 处理 prompt。"""
        if not prompt or not prompt.strip():
            return self.fail_response("prompt 不能为空")

        if model not in self.MODEL_MAP:
            return self.fail_response(f"未知模型 {model}，可选 free/air")

        m = self.MODEL_MAP[model]
        messages = [{"role": "user", "content": prompt}]
        t0 = time.time()
        try:
            # 在事件循环里跑同步 openai 调用（避免阻塞，用 to_thread）
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._call_sync, m, messages
            )
        except Exception as e:
            self._log_usage(model, False, time.time() - t0, len(prompt), 0)
            return self.fail_response(f"智谱调用异常: {e}")

        elapsed = time.time() - t0
        self._log_usage(model, True, elapsed, len(prompt), len(result))
        return self.success_response(f"=== 智谱GLM({m}) 处理结果 ===\n{result}")

    def _call_sync(self, model: str, messages: list) -> str:
        """同步调用（在 executor 线程里跑），带流式采集 + 非流式兜底。"""
        client = self._get_client()
        last_err = None
        for mt in (8000, 4000):
            try:
                parts = []
                stream = client.chat.completions.create(
                    model=model, messages=messages, temperature=0.1,
                    max_tokens=mt, stream=True)
                for ch in stream:
                    d = ch.choices[0].delta if ch.choices else None
                    if d and getattr(d, "content", None):
                        parts.append(d.content)
                if parts:
                    return "".join(parts)
            except Exception as e:
                last_err = e
                time.sleep(2)
        try:
            r = client.chat.completions.create(
                model=model, messages=messages, temperature=0.1,
                max_tokens=4000, stream=False)
            return r.choices[0].message.content or ""
        except Exception as e:
            return f"[智谱API错误] {last_err or e}"
