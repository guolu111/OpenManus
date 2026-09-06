"""
siliconflow_helper_tool.py — OpenManus 工具：调用硅基流动 API（GLM-4-9B 免费）。

设计（2026-09-05 · 多模型分工 · 用户铁律）：
1. 复用项目已有 中转API/configs/siliconflow_config.json 的 key + base_url。
2. 模型：THUDM/GLM-4-9B-0414（9B 免费，底层执行器：纯 JSON/搬运/去重/简单分类）。
3. 只"问"，不做决策——决策永远留给谷歌大脑。
4. 每次调用登记用量（供任务看板 API 监测读取）。
"""

import asyncio
import io
import json
import os
import time
from typing import ClassVar, Dict

from app.tool.base import BaseTool, ToolResult


class SiliconflowHelper(BaseTool):
    """调用硅基流动 API（GLM-4-9B 免费）做底层粗活。

    适合纯 JSON 生成、数据搬运、去重、简单分类、状态流转这类秒回级简单活；
    决策、规划、最终验收永远由谷歌大脑完成，本工具只是"手脚"。
    """

    name: str = "siliconflow_helper"
    description: str = (
        "调用硅基流动GLM-4-9B免费API做底层粗活(JSON生成/数据搬运/去重/简单分类)。"
        "参数: prompt=要处理的内容(详细具体)。返回该模型的处理结果。"
        "注意：它是最轻量级的免费模型，只能干简单活，复杂任务不要用它。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "要交给硅基处理的简单内容（JSON/搬运/去重/分类）",
            },
        },
        "required": ["prompt"],
    }

    # 项目已有硅基配置（key/base_url 都在里面，不重复写）
    CFG_PATH: ClassVar[str] = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\中转API\configs\siliconflow_config.json"
    USAGE_LOG: ClassVar[str] = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\4标签\usage\siliconflow_helper_usage.jsonl"
    DEFAULT_MODEL: ClassVar[str] = "THUDM/GLM-4-9B-0414"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = None
        self._load_config()

    def _load_config(self) -> None:
        """从项目已有配置读取 key/base_url（不重复配置）。"""
        try:
            with io.open(self.CFG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            self._base_url = cfg.get("base_url", "https://api.siliconflow.cn/v1")
            self._api_key = cfg.get("api_key", "")
        except Exception:
            self._base_url = "https://api.siliconflow.cn/v1"
            self._api_key = ""

    def _get_client(self):
        """懒加载 openai client（尽量复用连接）。"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self._base_url, api_key=self._api_key, timeout=300)
        return self._client

    def _log_usage(self, ok: bool, elapsed: float, prompt_len: int, reply_len: int) -> None:
        """登记用量（任务看板 API 监测读取）。"""
        try:
            os.makedirs(os.path.dirname(self.USAGE_LOG), exist_ok=True)
            record = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api": "siliconflow/glm-4-9b",
                "ok": ok,
                "elapsed_s": round(elapsed, 1),
                "prompt_chars": prompt_len,
                "reply_chars": reply_len,
            }
            with open(self.USAGE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    async def execute(self, prompt: str) -> ToolResult:
        """执行：调硅基 GLM-4-9B 处理 prompt。"""
        if not prompt or not prompt.strip():
            return self.fail_response("prompt 不能为空")

        messages = [{"role": "user", "content": prompt}]
        t0 = time.time()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._call_sync, self.DEFAULT_MODEL, messages
            )
        except Exception as e:
            self._log_usage(False, time.time() - t0, len(prompt), 0)
            return self.fail_response(f"硅基调用异常: {e}")

        elapsed = time.time() - t0
        self._log_usage(True, elapsed, len(prompt), len(result))
        return self.success_response(f"=== 硅基GLM-4-9B 处理结果 ===\n{result}")

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
                time.sleep(3)
        try:
            r = client.chat.completions.create(
                model=model, messages=messages, temperature=0.1,
                max_tokens=4000, stream=False)
            return r.choices[0].message.content or ""
        except Exception as e:
            return f"[硅基API错误] {last_err or e}"
