"""
远程控制模块测试脚本

测试内容：
1. 飞书消息处理器（消息解析、指令解析、消息发送）
2. 任务看板（任务添加、状态更新、状态报告）
3. 日志监督器（日志解析、告警检测、统计报告）

运行方式：
    python test_remote_control.py
"""

import sys
import os
import asyncio
import tempfile

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.remote_control import (
    FeishuHandler, FeishuMessage, Command, MessageType, CommandType,
    TaskDashboard, Task, TaskStatus, TaskPriority,
    LogMonitor, LogEntry, Alert, LogLevel,
)


def test_feishu_handler():
    """测试1：飞书消息处理器"""
    print("\n" + "=" * 60)
    print("测试1：飞书消息处理器")
    print("=" * 60)

    handler = FeishuHandler(
        app_id="cli_test",
        app_secret="test_secret",
        verification_token="test_token",
    )

    # 测试消息解析
    print("\n--- 测试消息解析 ---")
    event_data = {
        "event": {
            "message": {
                "message_id": "om_test123",
                "chat_id": "oc_test456",
                "chat_type": "p2p",
                "message_type": "text",
                "content": '{"text": "/task 分析这段文本的情感倾向", "mentions": []}',
            },
            "sender": {
                "sender_id": {"open_id": "ou_test789", "name": "测试用户"},
            },
        }
    }

    message = handler.parse_message(event_data)
    assert message is not None, "消息解析失败"
    assert message.message_id == "om_test123"
    assert message.chat_id == "oc_test456"
    assert message.sender_name == "测试用户"
    assert message.message_type == MessageType.TEXT
    assert "/task 分析这段文本的情感倾向" in message.content
    print(f"  ✅ 消息解析成功: {message.sender_name}: {message.content[:30]}...")

    # 测试指令解析
    print("\n--- 测试指令解析 ---")
    command = handler.parse_command(message)
    assert command.command_type == CommandType.TASK
    assert command.task_description == "分析这段文本的情感倾向"
    print(f"  ✅ 指令解析成功: {command.command_type.value}, 任务: {command.task_description}")

    # 测试其他指令类型
    test_cases = [
        ("/status", CommandType.STATUS),
        ("/help", CommandType.HELP),
        ("/role 分析", CommandType.ROLE),
        ("/chat 你好", CommandType.CHAT),
        ("普通消息", CommandType.CHAT),
    ]

    for text, expected_type in test_cases:
        msg = FeishuMessage(
            message_id=f"test_{text[:10]}",
            chat_id="oc_test",
            chat_type="p2p",
            sender_id="ou_test",
            sender_name="测试",
            message_type=MessageType.TEXT,
            content=text,
        )
        cmd = handler.parse_command(msg)
        assert cmd.command_type == expected_type, f"期望 {expected_type}, 实际 {cmd.command_type}"
        print(f"  ✅ 指令 '{text[:15]}...' -> {cmd.command_type.value}")

    # 测试帮助文本
    print("\n--- 测试帮助文本 ---")
    help_text = handler._get_help_text()
    assert "OpenManus统帅" in help_text
    assert "/task" in help_text
    assert "/status" in help_text
    print(f"  ✅ 帮助文本生成成功 ({len(help_text)} 字符)")

    # 测试状态文本
    print("\n--- 测试状态文本 ---")
    status_text = handler._get_status_text()
    assert "系统状态" in status_text
    print(f"  ✅ 状态文本生成成功 ({len(status_text)} 字符)")

    # 测试发送消息（模拟）
    print("\n--- 测试发送消息（模拟） ---")
    result = asyncio.run(handler.send_message(
        chat_id="oc_test",
        text="测试消息",
    ))
    assert result["status"] == "success"
    assert result["chat_id"] == "oc_test"
    print(f"  ✅ 消息发送成功（模拟）")

    print("\n✅ 测试1通过：飞书消息处理器功能正常")


def test_task_dashboard():
    """测试2：任务看板"""
    print("\n" + "=" * 60)
    print("测试2：任务看板")
    print("=" * 60)

    # 使用临时文件
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_file = f.name

    try:
        dashboard = TaskDashboard(state_file=state_file)

        # 测试添加任务
        print("\n--- 测试添加任务 ---")
        task1_id = dashboard.add_task(
            name="分析文本情感",
            role="分析",
            description="分析这段文本的情感倾向",
            priority=TaskPriority.HIGH,
        )
        task2_id = dashboard.add_task(
            name="生成摘要",
            role="生成",
            description="生成文本摘要",
            priority=TaskPriority.MEDIUM,
        )
        task3_id = dashboard.add_task(
            name="计算相似度",
            role="匹配",
            description="计算两段文本的相似度",
            priority=TaskPriority.LOW,
        )

        assert task1_id in dashboard.tasks
        assert task2_id in dashboard.tasks
        assert task3_id in dashboard.tasks
        print(f"  ✅ 添加3个任务成功")

        # 测试任务队列顺序（按优先级）
        print("\n--- 测试任务队列优先级 ---")
        next_task = dashboard.get_next_task()
        assert next_task is not None
        assert next_task.priority == TaskPriority.HIGH
        print(f"  ✅ 下一个任务是高优先级: {next_task.name}")

        # 测试更新任务状态
        print("\n--- 测试更新任务状态 ---")
        dashboard.update_task(task1_id, status=TaskStatus.RUNNING, progress=30)
        task1 = dashboard.get_task(task1_id)
        assert task1.status == TaskStatus.RUNNING
        assert task1.progress == 30
        assert task1.started_at is not None
        print(f"  ✅ 任务状态更新: {task1.name} -> {task1.status.value}, 进度: {task1.progress}%")

        # 测试完成任务
        print("\n--- 测试完成任务 ---")
        dashboard.complete_task(task1_id, result="情感分析完成：正面")
        task1 = dashboard.get_task(task1_id)
        assert task1.status == TaskStatus.COMPLETED
        assert task1.progress == 100
        assert task1.completed_at is not None
        assert task1.duration > 0
        print(f"  ✅ 任务完成: {task1.name}, 时长: {task1.duration:.2f}秒")

        # 测试任务失败
        print("\n--- 测试任务失败 ---")
        dashboard.fail_task(task2_id, error="API调用超时")
        task2 = dashboard.get_task(task2_id)
        assert task2.status == TaskStatus.FAILED
        assert task2.error == "API调用超时"
        print(f"  ✅ 任务失败: {task2.name}, 错误: {task2.error}")

        # 测试重试任务
        print("\n--- 测试重试任务 ---")
        dashboard.retry_task(task2_id)
        task2 = dashboard.get_task(task2_id)
        assert task2.status == TaskStatus.PENDING
        assert task2.retries == 1
        print(f"  ✅ 任务重试: {task2.name}, 重试次数: {task2.retries}")

        # 测试状态报告
        print("\n--- 测试状态报告 ---")
        report = dashboard.get_status_report()
        assert report["summary"]["total"] == 3
        assert report["summary"]["completed"] == 1
        assert report["summary"]["failed"] == 0  # 重试后变成pending
        assert report["summary"]["pending"] == 2
        print(f"  ✅ 状态报告: 总计{report['summary']['total']}, "
              f"完成{report['summary']['completed']}, "
              f"待执行{report['summary']['pending']}")

        # 测试状态文本
        print("\n--- 测试状态文本 ---")
        status_text = dashboard.get_status_text()
        assert "任务看板状态" in status_text
        assert "成功率" in status_text
        print(f"  ✅ 状态文本生成成功 ({len(status_text)} 字符)")

        # 测试按角色获取任务
        print("\n--- 测试按角色获取任务 ---")
        analysis_tasks = dashboard.get_tasks_by_role("分析")
        assert len(analysis_tasks) == 1
        print(f"  ✅ 分析角色任务: {len(analysis_tasks)} 个")

        # 测试最近任务
        print("\n--- 测试最近任务 ---")
        recent = dashboard.get_recent_tasks(limit=2)
        assert len(recent) == 2
        print(f"  ✅ 最近任务: {len(recent)} 个")

        print("\n✅ 测试2通过：任务看板功能正常")

    finally:
        # 清理临时文件
        if os.path.exists(state_file):
            os.unlink(state_file)


def test_log_monitor():
    """测试3：日志监督器"""
    print("\n" + "=" * 60)
    print("测试3：日志监督器")
    print("=" * 60)

    # 创建临时日志目录
    with tempfile.TemporaryDirectory() as log_dir:
        monitor = LogMonitor(log_dir=log_dir, scan_interval=1)

        # 测试日志解析
        print("\n--- 测试日志解析 ---")
        test_logs = [
            "2026-09-06 11:39:41.750 | INFO | app.module: 系统启动成功",
            "2026-09-06 11:39:42.100 | DEBUG | app.module: 调试信息",
            "2026-09-06 11:39:43.200 | WARNING | app.module: 警告信息",
            "2026-09-06 11:39:44.300 | ERROR | app.module: Connection refused - 连接失败",
            "2026-09-06 11:39:45.400 | CRITICAL | app.module: 系统严重错误",
            "无法解析的日志行",
        ]

        for line in test_logs:
            entry = monitor._parse_log_line(line, "test.log")
            assert entry is not None, f"日志解析失败: {line}"

        print(f"  ✅ 解析 {len(test_logs)} 条日志成功")

        # 测试日志级别识别
        print("\n--- 测试日志级别识别 ---")
        info_entry = monitor._parse_log_line(test_logs[0], "test.log")
        error_entry = monitor._parse_log_line(test_logs[3], "test.log")
        assert info_entry.level == LogLevel.INFO
        assert error_entry.level == LogLevel.ERROR
        print(f"  ✅ INFO级别识别: {info_entry.level.value}")
        print(f"  ✅ ERROR级别识别: {error_entry.level.value}")

        # 测试错误模式识别
        print("\n--- 测试错误模式识别 ---")
        # 手动添加错误日志触发告警
        error_line = "2026-09-06 11:40:00.000 | ERROR | api: Connection refused - 连接被拒绝"
        entry = monitor._parse_log_line(error_line, "api.log")
        monitor.log_entries.append(entry)
        monitor._check_alert(entry)

        assert len(monitor.alerts) > 0, "应该触发告警"
        alert = monitor.alerts[-1]
        assert alert.title == "connection_error"
        print(f"  ✅ 错误模式识别: {alert.title}")

        # 测试活跃告警
        print("\n--- 测试活跃告警 ---")
        active = monitor.get_active_alerts()
        assert len(active) > 0
        print(f"  ✅ 活跃告警: {len(active)} 个")

        # 测试确认告警
        print("\n--- 测试确认告警 ---")
        alert_id = active[0].alert_id
        result = monitor.acknowledge_alert(alert_id)
        assert result is True
        active_after = monitor.get_active_alerts()
        print(f"  ✅ 告警确认成功，剩余活跃告警: {len(active_after)} 个")

        # 测试统计报告
        print("\n--- 测试统计报告 ---")
        report = monitor.get_statistics_report(hours=24)
        assert report["total_logs"] > 0
        assert "level_counts" in report
        assert "error_rate" in report
        print(f"  ✅ 统计报告: 总日志{report['total_logs']}, "
              f"错误率{report['error_rate']}%")

        # 测试状态文本
        print("\n--- 测试状态文本 ---")
        status_text = monitor.get_status_text()
        assert "日志监督状态" in status_text
        assert "错误率" in status_text
        print(f"  ✅ 状态文本生成成功 ({len(status_text)} 字符)")

        # 测试最近错误
        print("\n--- 测试最近错误 ---")
        recent_errors = monitor.get_recent_errors(limit=5)
        assert len(recent_errors) > 0
        print(f"  ✅ 最近错误: {len(recent_errors)} 条")

        print("\n✅ 测试3通过：日志监督器功能正常")


def main():
    """主测试函数"""
    print("\n" + "█" * 60)
    print("█" + " " * 12 + "远程控制模块测试" + " " * 22 + "█")
    print("█" * 60)

    try:
        test_feishu_handler()
        test_task_dashboard()
        test_log_monitor()

        print("\n" + "█" * 60)
        print("█" + " " * 15 + "✅ 所有测试通过！" + " " * 22 + "█")
        print("█" * 60)
        print("\n下一步：")
        print("  1. 连接真实飞书API进行端到端测试")
        print("  2. 集成Manus统帅到飞书消息处理器")
        print("  3. 实现任务看板Web UI")
        print("  4. 实现日志监督告警通知（飞书/邮件）")
        print("  5. 三个模块协同工作，形成完整的远程操控闭环")
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
