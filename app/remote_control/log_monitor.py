"""
LogMonitor - 日志监督脚本

功能：
1. 实时扫描日志文件
2. 发现错误和异常
3. 告警通知
4. 日志统计分析
5. 错误模式识别

使用方式：
    from app.remote_control import LogMonitor

    monitor = LogMonitor(log_dir="logs")

    # 启动监控
    monitor.start()

    # 检查最新错误
    errors = monitor.get_recent_errors(limit=10)

    # 获取统计报告
    report = monitor.get_statistics_report()
"""

import os
import re
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from app.logger import logger


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime                    # 时间戳
    level: LogLevel                        # 级别
    message: str                           # 消息
    source: str = ""                       # 来源（模块/文件）
    raw_line: str = ""                     # 原始行
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class Alert:
    """告警"""
    alert_id: str                          # 告警ID
    level: LogLevel                        # 级别
    title: str                             # 标题
    message: str                           # 消息
    timestamp: datetime = field(default_factory=datetime.now)  # 时间
    acknowledged: bool = False             # 是否已确认
    count: int = 1                         # 出现次数
    related_logs: List[str] = field(default_factory=list)  # 相关日志


class LogMonitor:
    """
    日志监督器

    实时扫描日志，发现错误和异常，发送告警。
    """

    def __init__(
        self,
        log_dir: str = "logs",
        scan_interval: int = 30,  # 扫描间隔（秒）
        alert_on_error: bool = True,
        alert_on_critical: bool = True,
        alert_on_warning: bool = False,
    ):
        """
        初始化日志监督器

        Args:
            log_dir: 日志目录
            scan_interval: 扫描间隔（秒）
            alert_on_error: 发现ERROR时告警
            alert_on_critical: 发现CRITICAL时告警
            alert_on_warning: 发现WARNING时告警
        """
        self.log_dir = log_dir
        self.scan_interval = scan_interval
        self.alert_on_error = alert_on_error
        self.alert_on_critical = alert_on_critical
        self.alert_on_warning = alert_on_warning

        self.log_entries: List[LogEntry] = []
        self.alerts: List[Alert] = []
        self.file_positions: Dict[str, int] = {}  # 记录每个文件的读取位置

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 错误模式（用于识别常见错误）
        self.error_patterns = {
            "connection_error": [
                r"Connection refused",
                r"Connection timed out",
                r"Network is unreachable",
                r"Failed to establish a new connection",
            ],
            "auth_error": [
                r"Authentication failed",
                r"Invalid token",
                r"Permission denied",
                r"401 Unauthorized",
                r"403 Forbidden",
            ],
            "rate_limit": [
                r"Rate limit exceeded",
                r"Too many requests",
                r"429 Too Many Requests",
            ],
            "timeout": [
                r"Read timed out",
                r"Connect timed out",
                r"Operation timed out",
            ],
            "api_error": [
                r"API error",
                r"Bad gateway",
                r"502 Bad Gateway",
                r"503 Service Unavailable",
            ],
        }

        logger.info("日志监督器初始化完成")

    def start(self):
        """启动监控"""
        if self._running:
            logger.warning("日志监督器已经在运行")
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"日志监督器已启动，扫描间隔: {self.scan_interval}秒")

    def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("日志监督器已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self.scan_logs()
            except Exception as e:
                logger.error(f"日志扫描失败: {e}")
            time.sleep(self.scan_interval)

    def scan_logs(self) -> int:
        """
        扫描日志文件

        Returns:
            新发现的日志条目数
        """
        if not os.path.exists(self.log_dir):
            return 0

        new_entries = 0

        # 扫描所有.log文件
        for filename in os.listdir(self.log_dir):
            if not filename.endswith(".log"):
                continue

            filepath = os.path.join(self.log_dir, filename)
            new_entries += self._scan_file(filepath)

        return new_entries

    def _scan_file(self, filepath: str) -> int:
        """扫描单个文件"""
        try:
            file_size = os.path.getsize(filepath)
            last_position = self.file_positions.get(filepath, 0)

            # 如果文件被截断（如日志轮转），从头开始
            if file_size < last_position:
                last_position = 0

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(last_position)
                new_lines = f.readlines()
                self.file_positions[filepath] = f.tell()

            new_entries = 0
            for line in new_lines:
                entry = self._parse_log_line(line, filepath)
                if entry:
                    with self._lock:
                        self.log_entries.append(entry)
                    new_entries += 1

                    # 检查是否需要告警
                    self._check_alert(entry)

            return new_entries

        except Exception as e:
            logger.error(f"扫描文件失败 {filepath}: {e}")
            return 0

    def _parse_log_line(self, line: str, source: str) -> Optional[LogEntry]:
        """解析日志行"""
        line = line.strip()
        if not line:
            return None

        # 尝试解析标准日志格式：2026-09-06 11:39:41.750 | INFO | module:message
        pattern = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*\|\s*(\w+)\s*\|\s*(.+)"
        match = re.match(pattern, line)

        if match:
            timestamp_str = match.group(1)
            level_str = match.group(2).upper()
            message = match.group(3)

            try:
                timestamp = datetime.strptime(timestamp_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                timestamp = datetime.now()

            try:
                level = LogLevel(level_str)
            except ValueError:
                level = LogLevel.INFO

            # 提取来源模块
            source_module = ""
            if ":" in message:
                parts = message.split(":", 1)
                if len(parts[0]) < 50:  # 假设模块名不会太长
                    source_module = parts[0]
                    message = parts[1]

            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=source_module or source,
                raw_line=line,
            )

        # 如果无法解析，作为INFO处理
        return LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message=line,
            source=source,
            raw_line=line,
        )

    def _check_alert(self, entry: LogEntry):
        """检查是否需要告警"""
        should_alert = False

        if entry.level == LogLevel.ERROR and self.alert_on_error:
            should_alert = True
        elif entry.level == LogLevel.CRITICAL and self.alert_on_critical:
            should_alert = True
        elif entry.level == LogLevel.WARNING and self.alert_on_warning:
            should_alert = True

        if not should_alert:
            return

        # 识别错误模式
        error_type = "unknown"
        for etype, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, entry.message, re.IGNORECASE):
                    error_type = etype
                    break
            if error_type != "unknown":
                break

        # 创建或更新告警
        with self._lock:
            # 检查是否已有相同类型的告警（最近5分钟内）
            recent_alert = None
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            for alert in reversed(self.alerts):
                if alert.title == error_type and alert.timestamp > five_minutes_ago:
                    recent_alert = alert
                    break

            if recent_alert:
                recent_alert.count += 1
                recent_alert.related_logs.append(entry.raw_line[:200])
            else:
                alert = Alert(
                    alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.alerts)}",
                    level=entry.level,
                    title=error_type,
                    message=entry.message[:200],
                    related_logs=[entry.raw_line[:200]],
                )
                self.alerts.append(alert)
                logger.warning(f"新告警: [{entry.level.value}] {error_type} - {entry.message[:50]}...")

    def get_recent_errors(self, limit: int = 10, minutes: int = 60) -> List[LogEntry]:
        """获取最近的错误日志"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        errors = [
            e for e in self.log_entries
            if e.level in (LogLevel.ERROR, LogLevel.CRITICAL) and e.timestamp > cutoff
        ]
        return sorted(errors, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_active_alerts(self) -> List[Alert]:
        """获取未确认的告警"""
        return [a for a in self.alerts if not a.acknowledged]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"告警已确认: {alert_id}")
                return True
        return False

    def get_statistics_report(self, hours: int = 24) -> Dict[str, Any]:
        """获取统计报告"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_entries = [e for e in self.log_entries if e.timestamp > cutoff]

        # 按级别统计
        level_counts = {level.value: 0 for level in LogLevel}
        for entry in recent_entries:
            level_counts[entry.level.value] += 1

        # 按来源统计
        source_counts: Dict[str, int] = {}
        for entry in recent_entries:
            source_counts[entry.source] = source_counts.get(entry.source, 0) + 1

        # 错误率
        total = len(recent_entries)
        errors = level_counts.get("ERROR", 0) + level_counts.get("CRITICAL", 0)
        error_rate = errors / total * 100 if total > 0 else 0

        # 告警统计
        active_alerts = len(self.get_active_alerts())
        total_alerts = len(self.alerts)

        return {
            "time_range": f"最近{hours}小时",
            "total_logs": total,
            "level_counts": level_counts,
            "error_rate": round(error_rate, 2),
            "top_sources": sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "alerts": {
                "total": total_alerts,
                "active": active_alerts,
            },
        }

    def get_status_text(self) -> str:
        """获取状态文本（用于飞书消息）"""
        report = self.get_statistics_report()
        lc = report["level_counts"]

        # 活跃告警
        active = self.get_active_alerts()
        alert_text = ""
        if active:
            alert_text = "\n\n🚨 活跃告警:"
            for a in active[:3]:
                alert_text += f"\n  - [{a.level.value}] {a.title} (x{a.count})"

        return f"""📋 日志监督状态

时间范围: {report['time_range']}
总日志: {report['total_logs']} 条
DEBUG: {lc['DEBUG']}
INFO: {lc['INFO']}
WARNING: {lc['WARNING']}
ERROR: {lc['ERROR']}
CRITICAL: {lc['CRITICAL']}

错误率: {report['error_rate']}%
告警总数: {report['alerts']['total']}
活跃告警: {report['alerts']['active']}
{alert_text}
"""

    def clear_old_logs(self, hours: int = 168) -> int:
        """清理旧日志（默认7天）"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            original_count = len(self.log_entries)
            self.log_entries = [e for e in self.log_entries if e.timestamp > cutoff]
            removed = original_count - len(self.log_entries)
        logger.info(f"清理了 {removed} 条旧日志")
        return removed

    def status(self) -> str:
        """获取监督器状态"""
        report = self.get_statistics_report()
        return f"""=== 日志监督器状态 ===
运行状态: {'运行中' if self._running else '已停止'}
扫描间隔: {self.scan_interval}秒
日志目录: {self.log_dir}
已扫描日志: {len(self.log_entries)} 条
告警总数: {len(self.alerts)}
活跃告警: {len(self.get_active_alerts())}
错误率: {report['error_rate']}%
"""
