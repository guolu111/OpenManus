"""
batch_run_tool.py — OpenManus 自定义跑批工具：金庸连载章节四API+4标签分析。

设计原则（用户铁律 · 2026-09-05）：
1. 最强大脑一句话"跑第N章"就调用本工具，不需要自己一步步操作。
2. 内置bridge自愈：遇到标签500/连接拒绝/TargetClosed时，自动调 BridgeHealth 恢复后重试。
3. 纯数据搬运模式（默认）：标签输出直接存，不调用air润色（省收费额度）。
4. 断点续跑：已完成的天自动跳过。
5. 全记账：gcli/智谱free/智谱air/硅基/4标签 全部写 usage jsonl。
6. 防火墙铁律：绝不 kill Chrome / 任务看板 / 守护进程，只处理 bridge 自身。

依赖：run_chN_4api.py（执行层脚本）、BridgeHealth（自愈工具）。
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from typing import ClassVar, Dict, List, Optional

from app.tool.base import BaseTool, ToolResult
from app.tool.bridge_health_tool import BridgeHealth

# 项目常量
PROJECT_ROOT = r"D:\360Downloads\金庸\一念永恒"
LOG_DIR = os.path.join(PROJECT_ROOT, "一念永恒小说", "开源拉取", "OpenManus", "logs")
RUN_SCRIPT = os.path.join(
    PROJECT_ROOT, "一念永恒小说", "三个标签", "半个智能体代码库", "执行层", "run_chN_4api.py"
)
OPENMANUS_PY = os.path.join(
    PROJECT_ROOT, "一念永恒小说", "开源拉取", "OpenManus", ".venv", "Scripts", "python.exe"
)
RESULT_DIR = os.path.join(PROJECT_ROOT, "一念永恒小说", "中转API")
USAGE_DIR = os.path.join(PROJECT_ROOT, "一念永恒小说", "三个标签", "usage")

# 标签错误关键词（触发自愈）
BRIDGE_ERROR_KEYS = [
    "WinError 10061", "WinError 10054", "TargetClosed",
    "HTTP Error 500", "Connection refused", "拒绝连接",
    "远程主机强迫关闭", "bridge",
]


class BatchRun(BaseTool):
    """金庸连载章节跑批工具：四API(gcli/智谱free/智谱air/硅基)+4标签(豆包/千问/智谱)协同分析。

    当用户要求"跑第N章""分析第N章""继续跑批"时使用本工具。
    自动检查bridge健康，异常则自愈后重试；断点续跑已完成的天。
    默认纯数据搬运（不调用air润色），需要深度润色时传 use_air=true。
    返回跑批结果摘要（成功天数/失败天数/API消耗）。
    """

    name: str = "batch_run"
    description: str = (
        "金庸小说连载章节跑批工具。调用四API(谷歌gcli指挥官+智谱free补齐+智谱air润色+硅基检查)"
        "+4标签网页版(豆包/千问/智谱深度分析)协同完成章节分析。"
        "内置bridge自愈（标签500/连接拒绝时自动恢复重试）和断点续跑。"
        "参数: chapter=章节号(必填,如29); day=只跑某天(可选,0=全部); "
        "use_air=是否开启智谱4.5-air深度润色(可选,默认false纯数据搬运省额度)。"
        "返回成功/失败天数和API消耗摘要。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "chapter": {
                "type": "integer",
                "description": "章节号，如 29 表示第29章",
            },
            "day": {
                "type": "integer",
                "description": "只跑某一天（1-N），0或不传=跑全部天",
                "default": 0,
            },
            "use_air": {
                "type": "boolean",
                "description": "是否开启智谱4.5-air收费模型深度润色，默认false（纯数据搬运）",
                "default": False,
            },
        },
        "required": ["chapter"],
    }

    # ===== 工具函数 =====

    def _bridge_healthy(self) -> bool:
        """快速检查bridge 8010是否在线。"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                return s.connect_ex(("127.0.0.1", 8010)) == 0
        except Exception:
            return False

    async def _heal_bridge(self) -> bool:
        """调用 BridgeHealth 自愈工具恢复bridge。"""
        healer = BridgeHealth()
        result = await healer.execute(action="restart")
        output = str(result)
        return "✅" in output and "已恢复" in output or "全部标签已恢复" in output or "bridge 正常" in output

    async def _read_stream(self, stream, log_file, output_list, label):
        """异步逐行读取流，实时写入日志文件。"""
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace").rstrip()
            output_list.append(decoded)
            # 实时写入日志文件
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] [{label}] {decoded}\n")
            log_file.flush()

    async def _heartbeat(self, proc, log_file, stop_event):
        """心跳机制：每30秒更新一次状态，防止看起来像卡住了。"""
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass
            if proc.returncode is None:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"[{timestamp}] [HEARTBEAT] 跑批脚本运行中，PID={proc.pid}\n")
                log_file.flush()

    async def _run_script(self, chapter: int, day: int, use_air: bool) -> Dict:
        """启动跑批脚本（异步非阻塞+实时日志+心跳），立即返回不等待完成。
        
        重要：启动子进程后立即返回，让子进程在后台运行。
        OpenManus可以通过实时日志文件查看进度，不需要等待子进程完成。
        这样可以避免toolcall.py的60秒工具执行超时。
        """
        # 使用python -u禁用缓冲，确保实时输出
        cmd = [OPENMANUS_PY, "-u", RUN_SCRIPT, "--chapter", str(chapter)]
        if day and day > 0:
            cmd += ["--day", str(day)]
        if use_air:
            cmd += ["--use-air"]

        # 创建实时日志文件
        os.makedirs(LOG_DIR, exist_ok=True)
        log_filename = f"batch_run_ch{chapter}_{time.strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(LOG_DIR, log_filename)

        try:
            # 使用异步子进程，不阻塞事件循环
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 打开日志文件（不关闭，让后台任务持续写入）
            log_file = open(log_path, "w", encoding="utf-8")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] [START] 跑批脚本启动，PID={proc.pid}\n")
            log_file.write(f"[{timestamp}] [CMD] {' '.join(cmd)}\n")
            log_file.flush()

            # 启动后台任务：实时读取stdout和stderr + 心跳
            # 这些任务在后台运行，不会阻塞当前方法返回
            stdout_lines = []
            stderr_lines = []
            stop_event = asyncio.Event()
            
            # 创建后台监控任务
            async def _monitor():
                try:
                    # 同时读取两个流
                    await asyncio.gather(
                        self._read_stream(proc.stdout, log_file, stdout_lines, "STDOUT"),
                        self._read_stream(proc.stderr, log_file, stderr_lines, "STDERR"),
                    )
                    # 等待进程退出
                    await proc.wait()
                except Exception as e:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_file.write(f"[{timestamp}] [ERROR] 监控任务异常: {e}\n")
                    log_file.flush()
                finally:
                    stop_event.set()
                    # 记录退出码
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_file.write(f"[{timestamp}] [END] 跑批脚本结束，退出码={proc.returncode}\n")
                    log_file.flush()
                    log_file.close()
            
            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self._heartbeat(proc, log_file, stop_event))
            # 启动监控任务
            monitor_task = asyncio.create_task(_monitor())
            
            # 立即返回，不等待子进程完成
            return {
                "ok": True, 
                "started": True,
                "pid": proc.pid,
                "log_file": log_path,
                "message": "跑批已启动，正在后台运行。请通过实时日志查看进度。"
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "summary": None, "log_file": log_path}
    
    def _get_progress(self, log_path: str) -> Dict:
        """读取实时日志的最后几行，获取跑批进度。"""
        try:
            if not os.path.exists(log_path):
                return {"running": False, "last_lines": [], "error": "日志文件不存在"}
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # 检查是否已结束
            ended = any("[END]" in line for line in lines)
            # 获取最后10行
            last_lines = [line.strip() for line in lines[-10:] if line.strip()]
            return {
                "running": not ended,
                "ended": ended,
                "last_lines": last_lines,
                "total_lines": len(lines)
            }
        except Exception as e:
            return {"running": False, "error": str(e)}

    def _extract_summary(self, output: str) -> Optional[Dict]:
        """从脚本输出中提取最后的 JSON summary。"""
        try:
            # 找最后一个 { ... } 块
            lines = output.splitlines()
            json_lines = []
            in_json = False
            brace_count = 0
            for line in reversed(lines):
                if "}" in line:
                    in_json = True
                if in_json:
                    json_lines.insert(0, line)
                    brace_count += line.count("{") - line.count("}")
                    if brace_count == 0 and "{" in line:
                        break
            if json_lines:
                text = "\n".join(json_lines)
                # 清理可能的前缀
                start = text.find("{")
                if start >= 0:
                    return json.loads(text[start:])
        except Exception:
            pass
        return None

    def _has_bridge_error(self, output: str) -> bool:
        """检测输出中是否有bridge错误关键词。"""
        return any(k in output for k in BRIDGE_ERROR_KEYS)

    def _count_results(self, chapter: int) -> Dict:
        """统计该章已完成的结果。"""
        p = os.path.join(RESULT_DIR, f"batch_ldj_ch{chapter}", "results_4api.jsonl")
        if not os.path.exists(p):
            return {"total": 0, "days": []}
        try:
            days = []
            for line in open(p, encoding="utf-8"):
                try:
                    j = json.loads(line)
                    if j.get("content") and len(j.get("content", "")) > 10:
                        days.append(j.get("day"))
                except Exception:
                    pass
            return {"total": len(days), "days": sorted(days)}
        except Exception:
            return {"total": 0, "days": []}

    # ===== 主入口 =====

    async def execute(self, chapter: int, day: int = 0, use_air: bool = False) -> ToolResult:
        """执行章节跑批，内置自愈+重试。"""
        if not chapter or chapter < 1:
            return self.error_response("chapter 参数无效，必须是正整数")

        lines = []
        lines.append(f"=== 跑批第{chapter}章 ===")
        lines.append(f"模式: {'air深度润色' if use_air else '纯数据搬运(无air)'}")
        lines.append(f"范围: {'第'+str(day)+'天' if day else '全部天'}")

        # 第1步：检查bridge健康
        if not self._bridge_healthy():
            lines.append("⚠️ bridge未在线，执行自愈...")
            healed = await self._heal_bridge()
            lines.append(f"  自愈结果: {'✅成功' if healed else '❌失败'}")
            if not healed:
                lines.append("❌ bridge自愈失败，无法跑批，请人工检查浏览器登录态")
                return self.success_response("\n".join(lines))

        # 第2步：执行跑批（最多重试2次，每次失败先自愈）
        max_retries = 2
        for attempt in range(max_retries + 1):
            if attempt > 0:
                lines.append(f"🔄 第{attempt}次重试（先自愈bridge）...")
                await self._heal_bridge()
                await asyncio.sleep(5)

            result = await self._run_script(chapter, day, use_air)

            if not result["ok"]:
                lines.append(f"❌ 执行失败: {result.get('error','未知')}")
                if attempt < max_retries:
                    continue
                break

            # 新格式：启动后立即返回，不等待完成
            if result.get("started"):
                lines.append(f"\n✅ 跑批已启动，正在后台运行")
                lines.append(f"  进程PID: {result.get('pid')}")
                lines.append(f"  实时日志: {result.get('log_file')}")
                lines.append(f"  提示: 跑批可能需要10-20分钟完成，请通过实时日志查看进度")
                return self.success_response("\n".join(lines))

            summary = result.get("summary")
            if summary:
                fail_days = summary.get("days_fail", [])
                # 如果有失败天且是bridge错误，重试
                if fail_days and self._has_bridge_error(result.get("output_tail", "")):
                    lines.append(f"  本次失败天: {fail_days}（疑似bridge错误，将重试）")
                    if attempt < max_retries:
                        continue
                # 成功或非bridge错误，结束
                lines.append(f"\n✅ 跑批完成")
                lines.append(f"  成功天数: {summary.get('days_ok', [])}")
                lines.append(f"  失败天数: {summary.get('days_fail', [])}")
                lines.append(f"  跳过天数: {summary.get('days_skipped', [])}")
                lines.append(f"  gcli今日已用: {summary.get('gcli_used_today', '?')}/950")
                if summary.get("air_quota_tokens", 0) > 0:
                    lines.append(f"  air消耗: {summary['air_quota_tokens']} token")
                # 统计已完成结果
                done = self._count_results(chapter)
                lines.append(f"  该章累计完成: {done['total']}天 {done['days']}")
                if result.get("log_file"):
                    lines.append(f"  实时日志: {result['log_file']}")
                return self.success_response("\n".join(lines))
            else:
                lines.append("⚠️ 未提取到summary，输出尾部:")
                lines.append(result.get("output_tail", "")[:500])
                if attempt < max_retries:
                    continue
                break

        lines.append("\n❌ 跑批未能完成（重试已用尽），请检查bridge和浏览器状态")
        return self.success_response("\n".join(lines))


if __name__ == "__main__":
    async def _main():
        tool = BatchRun()
        r = await tool.execute(chapter=29, day=0, use_air=False)
        print(str(r))
    asyncio.run(_main())
