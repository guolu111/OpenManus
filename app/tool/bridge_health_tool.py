"""
bridge_health_tool.py — OpenManus 自定义自愈工具：4标签桥接(multi_bridge)健康诊断与自动恢复。

设计原则（用户铁律 · 2026-09-05）：
1. 最强大脑遇到标签异常（HTTP 500 / 超时 / TargetClosed / 连接拒绝）时，
   【不再傻等或报错】，而是调用本工具自己诊断、自己恢复。
2. 诊断：检查 8010 是否监听 + 3标签(doubao/qwen/glm)连通性测试。
3. 恢复：确认 bridge 异常后，杀掉 bridge 进程（不碰 Chrome，浏览器由 _browser.py 独立管理）
   → 等待守护(_bridge_guard.py)自动拉起 或 手动拉起 multi_bridge。
4. 记录：每次自愈动作写 health 日志（供任务看板 API 监测读取）。
5. 防火墙铁律：绝不 kill Chrome 进程、绝不 kill 任务看板/守护进程，只处理 bridge 自身。
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from typing import ClassVar, Dict, List, Optional

import aiohttp

from app.tool.base import BaseTool, ToolResult

# 项目常量（用户路径铁律：不变更）
BRIDGES_DIR = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\中转API\bridges"
MULTI_BRIDGE = os.path.join(BRIDGES_DIR, "multi_bridge.py")
HEALTH_LOG = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\4标签\usage\bridge_health.jsonl"
PORT = 8010
# 学习机制（2026-09-05 网友方案）：自愈后自动沉淀经验到 .learnings
LEARN_DIR = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus\.learnings"
ERRORS_FILE = os.path.join(LEARN_DIR, "ERRORS.md")
LEARNINGS_FILE = os.path.join(LEARN_DIR, "LEARNINGS.md")

# 平台标签
TAG_MODELS: List[str] = ["doubao", "qwen", "glm"]
TAG_NAMES: Dict[str, str] = {"doubao": "豆包", "qwen": "千问国际版", "glm": "智谱清言"}

# 测试超时（秒）——标签网页回复慢，给足时间
PROBE_TIMEOUT: int = 90


def _log_health(action: str, detail: Dict) -> None:
    """登记自愈动作到 health 日志（任务看板 API 监测读取）。"""
    try:
        os.makedirs(os.path.dirname(HEALTH_LOG), exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            **detail,
        }
        with open(HEALTH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _record_learning(recovered: bool, diag: Dict) -> None:
    """自愈闭环后自动沉淀经验到 .learnings（网友方案·OpenClaw ERRORS/LEARNINGS）。"""
    try:
        os.makedirs(LEARN_DIR, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        status = {m: ("ok" if t.get("ok") else t.get("status")) for m, t in diag.get("tags", {}).items()}
        if recovered:
            entry = (
                f"\n## {ts} #{len(open(LEARNINGS_FILE, encoding='utf-8').read().split('## ')) - 2} · 4标签桥接自动恢复成功\n"
                f"- **时间**: {ts}\n"
                f"- **问题**: 4标签桥接异常自动恢复（端口/标签状态: {status}）\n"
                f"- **修正方法**: 调用 bridge_health restart → 重启 multi_bridge 进程 → 复用 doubao_profile 登录态重开标签\n"
                f"- **可复用规则**: 标签异常→check诊断→restart恢复→验证→重试；绝不碰Chrome/看板。\n"
            )
            with open(LEARNINGS_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
        else:
            entry = (
                f"\n## {ts} · 4标签桥接自动恢复失败（需人工介入）\n"
                f"- **时间**: {ts}\n"
                f"- **症状**: 自动重启 bridge 后标签仍异常（状态: {status}）\n"
                f"- **处置**: 自动恢复未成功，需人工检查 multi_bridge_health.log 或浏览器登录态。\n"
            )
            with open(ERRORS_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
    except Exception:
        pass


class BridgeHealth(BaseTool):
    """4标签桥接(multi_bridge)健康诊断与自动恢复。

    当调用 ask_tag / 跑批时发现标签通道报错（HTTP 500、超时、TargetClosed、连接拒绝），
    使用本工具诊断 bridge 是否正常；若异常则自动重启 bridge 恢复。
    操作：action='check' 只诊断；action='restart' 诊断+异常则自动重启恢复。
    """

    name: str = "bridge_health"
    description: str = (
        "诊断并自动恢复4标签网页版桥接服务(multi_bridge, 端口8010)。"
        "当 ask_tag 或跑批调用豆包/千问/智谱标签失败(HTTP 500/超时/TargetClosed/连接拒绝)时使用。"
        "参数: action='check'=只诊断3标签连通性+bridge进程状态(不重启)；"
        "action='restart'=诊断后若发现异常自动重启bridge恢复(不碰Chrome浏览器/任务看板)。"
        "返回诊断结果与恢复动作。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check", "restart"],
                "description": "check=只诊断；restart=诊断+异常时自动恢复(默认)",
            },
        },
        "required": [],
    }

    # ===== 工具函数 =====

    def _port_listening(self, port: int = PORT) -> bool:
        """检查 8010 端口是否有监听。"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex(("127.0.0.1", port)) == 0
        except Exception:
            return False

    def _find_bridge_pids(self) -> List[int]:
        """找到 multi_bridge 相关进程 PID（不含 guard）。"""
        pids: List[int] = []
        try:
            cmd = (
                'powershell -NoProfile -Command '
                '"Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | '
                'Where-Object { $_.CommandLine -match \'multi_bridge\' } | '
                'Select-Object -ExpandProperty ProcessId"'
            )
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            for line in out.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
        except Exception:
            pass
        return pids

    def _kill_bridge(self) -> Dict:
        """杀掉 bridge 进程（只杀 multi_bridge，绝不碰 Chrome/看板）。"""
        killed: List[int] = []
        try:
            pids = self._find_bridge_pids()
            for pid in pids:
                try:
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                   capture_output=True, timeout=15)
                    killed.append(pid)
                except Exception:
                    pass
        except Exception:
            pass
        return {"killed_pids": killed}

    def _start_bridge(self) -> Dict:
        """启动 multi_bridge（后台，日志重定向到 multi_bridge_health.log）。"""
        py = sys.executable
        log = os.path.join(BRIDGES_DIR, "multi_bridge_health.log")
        try:
            proc = subprocess.Popen(
                [py, MULTI_BRIDGE],
                stdout=open(log, "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
            return {"started_pid": proc.pid, "log": log}
        except Exception as e:
            return {"start_error": str(e)}

    async def _probe_tag(self, model: str, prompt: str = "请只回复：连通测试OK") -> Dict:
        """探测单个标签连通性。"""
        url = f"http://127.0.0.1:{PORT}/v1/chat/completions"
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        t0 = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, timeout=aiohttp.ClientTimeout(total=PROBE_TIMEOUT)
                ) as resp:
                    elapsed = round(time.time() - t0, 1)
                    data = await resp.json()
                    if resp.status == 200:
                        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return {"ok": True, "status": 200, "elapsed_s": elapsed,
                                "reply_head": reply[:40]}
                    return {"ok": False, "status": resp.status, "elapsed_s": elapsed,
                            "error": data.get("error", "")}
        except asyncio.TimeoutError:
            return {"ok": False, "status": "timeout",
                    "elapsed_s": round(time.time() - t0, 1), "error": "超时"}
        except Exception as e:
            return {"ok": False, "status": "conn_error",
                    "elapsed_s": round(time.time() - t0, 1), "error": str(e)[:80]}

    async def _diagnose(self) -> Dict:
        """诊断 bridge：端口 + 进程 + 3标签连通性。"""
        listening = self._port_listening()
        pids = self._find_bridge_pids()
        result = {
            "port_8010_listening": listening,
            "bridge_pids": pids,
            "tags": {},
        }
        # 只有端口在监听才探测标签（避免长时间等待无意义）
        if listening:
            for m in TAG_MODELS:
                r = await self._probe_tag(m)
                result["tags"][m] = r
                result["tags"][m]["name"] = TAG_NAMES.get(m, m)
        else:
            for m in TAG_MODELS:
                result["tags"][m] = {"ok": False, "status": "port_down",
                                     "name": TAG_NAMES.get(m, m), "error": "bridge端口未监听"}
        return result

    # ===== 主入口 =====

    async def execute(self, action: str = "restart") -> ToolResult:
        """执行诊断与自愈。"""
        if action not in ("check", "restart"):
            action = "restart"

        diag = await self._diagnose()
        _log_health("check", {"port": diag["port_8010_listening"],
                              "pids": diag["bridge_pids"],
                              "tag_status": {m: ("ok" if t.get("ok") else t.get("status"))
                                             for m, t in diag["tags"].items()}})

        # 判定是否异常
        port_ok = diag["port_8010_listening"]
        tags_ok = all(diag["tags"][m].get("ok") for m in TAG_MODELS)
        abnormal = not port_ok or not tags_ok

        lines = []
        lines.append("=== 4标签桥接健康诊断 ===")
        lines.append(f"端口8010监听: {'✅' if port_ok else '❌'}")
        lines.append(f"bridge进程PID: {diag['bridge_pids'] or '未找到'}")
        for m in TAG_MODELS:
            t = diag["tags"][m]
            mark = "✅" if t.get("ok") else "❌"
            extra = f" ({t.get('elapsed_s','')}s)" if t.get("ok") else f" - {t.get('error','')}"
            lines.append(f"  {t.get('name')}: {mark}{extra}")

        if not abnormal:
            lines.append("\n✅ bridge 正常，无需恢复。")
            _log_health("result", {"abnormal": False})
            return self.success_response("\n".join(lines))

        # 异常 → 视 action 决定是否恢复
        if action == "check":
            lines.append("\n⚠️ 检测到异常，但 action=check 未执行恢复。")
            _log_health("result", {"abnormal": True, "action": "check_no_recover"})
            return self.success_response("\n".join(lines))

        # restart：执行恢复
        lines.append("\n🔄 检测到异常，执行自动恢复...")
        kill = self._kill_bridge()
        lines.append(f"  已停 bridge: {kill.get('killed_pids') or '无'}")
        _log_health("restart", {"killed_pids": kill.get("killed_pids", [])})

        # 等待守护拉起或手动启动
        await asyncio.sleep(3)
        if not self._port_listening():
            start = self._start_bridge()
            lines.append(f"  守护未拉起，手动启动: PID={start.get('started_pid','?')}")
            _log_health("restart", {"manual_start": start})
        else:
            lines.append("  守护已自动拉起 bridge，等待就绪...")

        # 等待 bridge 完全就绪（最多等 60s）
        ready = False
        for _ in range(12):
            await asyncio.sleep(5)
            if self._port_listening():
                ready = True
                break

        if not ready:
            lines.append("\n❌ bridge 恢复失败（端口仍未监听），请人工检查 multi_bridge_health.log")
            _log_health("result", {"abnormal": True, "recovered": False})
            return self.success_response("\n".join(lines))

        # 就绪后再探测一遍标签
        lines.append("✅ bridge 已就绪，重新验证标签...")
        recheck = await self._diagnose()
        for m in TAG_MODELS:
            t = recheck["tags"][m]
            mark = "✅" if t.get("ok") else "❌"
            extra = f" ({t.get('elapsed_s','')}s)" if t.get("ok") else f" - {t.get('error','')}"
            lines.append(f"  {t.get('name')}: {mark}{extra}")
        recovered = all(recheck["tags"][m].get("ok") for m in TAG_MODELS)
        lines.append(f"\n{'✅ 全部标签已恢复，可继续跑批。' if recovered else '⚠️ 部分标签仍异常，请重试或人工介入。'}")
        _log_health("result", {"abnormal": True, "recovered": recovered})
        # 自愈闭环后沉淀学习记录（网友方案）
        _record_learning(recovered, recheck)
        return self.success_response("\n".join(lines))


if __name__ == "__main__":
    async def _main():
        tool = BridgeHealth()
        r = await tool.execute(action="check")
        print(str(r))
    asyncio.run(_main())
