# -*- coding: utf-8 -*-
"""
test_p0_core.py · P0核心稳定性模块集成测试
================================================
测试Phase 5.1的5个P0核心模块：
1. 全局网络超时控制 (setup_global_timeout)
2. 全局资源锁 ResourceManager
3. 轻量事件总线 EventBus
4. 全局统一状态中心 StateStore
5. 统一门面 Commander

运行方式：
    python test_p0_core.py
"""
import asyncio
import sys
import os
import time
import json

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_global_timeout():
    """测试1：全局网络超时控制"""
    print("\n" + "=" * 60)
    print("测试1：全局网络超时控制")
    print("=" * 60)
    
    from app.resource_manager import setup_global_timeout
    import socket
    
    # 测试设置超时
    setup_global_timeout(180)
    current_timeout = socket.getdefaulttimeout()
    assert current_timeout == 180, f"超时设置错误，期望180，实际{current_timeout}"
    print(f"  ✅ 全局网络超时已设置: {current_timeout}秒")
    
    # 测试恢复
    socket.setdefaulttimeout(None)
    print("  ✅ 测试通过")
    return True


async def test_resource_manager():
    """测试2：全局资源锁ResourceManager"""
    print("\n" + "=" * 60)
    print("测试2：全局资源锁ResourceManager")
    print("=" * 60)
    
    from app.resource_manager import ResourceManager, init_resource_manager
    
    # 初始化
    rm = init_resource_manager(max_concurrent_browsers=1)
    assert rm is not None, "ResourceManager初始化失败"
    print(f"  ✅ ResourceManager初始化完成，最大并发浏览器: {rm.max_concurrent_browsers}")
    
    # 测试获取浏览器资源
    async with rm.acquire_browser("测试用途") as res:
        assert res["resource_id"] is not None, "资源ID为空"
        assert res["purpose"] == "测试用途", "用途不匹配"
        print(f"  ✅ 获取浏览器资源成功: {res['resource_id']}")
        
        # 测试获取统计信息
        stats = await rm.get_stats()
        assert stats["active_browsers"] == 1, f"活跃浏览器数错误，期望1，实际{stats['active_browsers']}"
        print(f"  ✅ 资源统计正确: 活跃浏览器={stats['active_browsers']}")
    
    # 测试释放后统计
    stats = await rm.get_stats()
    assert stats["active_browsers"] == 0, f"释放后活跃浏览器数错误，期望0，实际{stats['active_browsers']}"
    print(f"  ✅ 资源释放正确: 活跃浏览器={stats['active_browsers']}")
    
    # 测试Profile锁
    async with rm.acquire_profile("/tmp/test_profile"):
        print("  ✅ Profile锁获取/释放成功")
    
    # 测试端口锁
    async with rm.acquire_port(8080):
        print("  ✅ 端口锁获取/释放成功")
    
    print("  ✅ 测试通过")
    return True


async def test_event_bus():
    """测试3：轻量事件总线EventBus"""
    print("\n" + "=" * 60)
    print("测试3：轻量事件总线EventBus")
    print("=" * 60)
    
    from app.event_bus import EventBus, EventType, Event, init_event_bus
    
    # 初始化（同步模式）
    bus = init_event_bus(async_mode=False)
    assert bus is not None, "EventBus初始化失败"
    print(f"  ✅ EventBus初始化完成，模式: 同步")
    
    # 测试订阅和发布
    received_events = []
    
    async def test_handler(event: Event):
        received_events.append(event)
        print(f"  📨 收到事件: {event.event_type.value} - {event.message}")
    
    bus.subscribe("task_start", test_handler)
    bus.subscribe("task_*", test_handler)  # 通配符订阅
    
    # 发布事件
    await bus.publish_simple(EventType.TASK_START, message="测试任务开始", task_id="test_001")
    await bus.publish_simple(EventType.TASK_DONE, message="测试任务完成", task_id="test_001")
    
    # 等待事件分发
    await asyncio.sleep(0.1)
    
    assert len(received_events) >= 2, f"收到事件数错误，期望>=2，实际{len(received_events)}"
    print(f"  ✅ 事件订阅/发布成功，收到{len(received_events)}个事件")
    
    # 测试事件历史
    history = bus.get_event_history(limit=10)
    assert len(history) >= 2, f"事件历史数错误，期望>=2，实际{len(history)}"
    print(f"  ✅ 事件历史记录正确: {len(history)}条")
    
    # 测试统计信息
    stats = bus.get_stats()
    assert stats["event_history_count"] >= 2, f"事件历史统计错误"
    print(f"  ✅ 统计信息正确: 事件历史={stats['event_history_count']}")
    
    print("  ✅ 测试通过")
    return True


async def test_state_store():
    """测试4：全局统一状态中心StateStore"""
    print("\n" + "=" * 60)
    print("测试4：全局统一状态中心StateStore")
    print("=" * 60)
    
    from app.state_store import StateStore, TaskStatus, RoleStatus, AlertStatus, init_state_store
    
    # 使用临时持久化目录
    import tempfile
    tmp_dir = tempfile.mkdtemp()
    
    # 初始化
    store = init_state_store(persist_dir=tmp_dir)
    assert store is not None, "StateStore初始化失败"
    print(f"  ✅ StateStore初始化完成，持久化目录: {tmp_dir}")
    
    # 测试任务创建
    task = await store.create_task(
        task_id="test_task_001",
        command="测试命令",
        priority=1,
        role_name="测试角色",
        metadata={"test": True},
    )
    assert task.task_id == "test_task_001", "任务ID错误"
    assert task.status == TaskStatus.PENDING, "任务状态错误"
    print(f"  ✅ 任务创建成功: {task.task_id}")
    
    # 测试任务状态更新
    task = await store.update_task_status("test_task_001", TaskStatus.RUNNING, progress=0.5)
    assert task.status == TaskStatus.RUNNING, "任务状态更新错误"
    assert task.progress == 0.5, "任务进度错误"
    assert task.started_at is not None, "任务开始时间为空"
    print(f"  ✅ 任务状态更新成功: {task.status.value}, 进度={task.progress}")
    
    # 测试任务完成
    task = await store.update_task_status(
        "test_task_001", TaskStatus.COMPLETED, progress=1.0,
        result={"output": "测试结果"}
    )
    assert task.status == TaskStatus.COMPLETED, "任务完成状态错误"
    assert task.completed_at is not None, "任务完成时间为空"
    print(f"  ✅ 任务完成: {task.status.value}")
    
    # 测试角色激活
    role = await store.activate_role("测试角色", permission_level=2, task_id="test_task_001")
    assert role.status == RoleStatus.ACTIVE, "角色激活状态错误"
    assert role.permission_level == 2, "角色权限级别错误"
    print(f"  ✅ 角色激活成功: {role.role_name}, 权限={role.permission_level}")
    
    # 测试获取活跃角色
    active_roles = await store.get_active_roles()
    assert len(active_roles) == 1, f"活跃角色数错误，期望1，实际{len(active_roles)}"
    print(f"  ✅ 活跃角色查询正确: {len(active_roles)}个")
    
    # 测试角色取消激活
    role = await store.deactivate_role("测试角色")
    assert role.status == RoleStatus.INACTIVE, "角色取消激活状态错误"
    print(f"  ✅ 角色取消激活成功")
    
    # 测试告警创建
    alert = await store.create_alert(
        alert_id="test_alert_001",
        alert_type="error",
        message="测试告警",
        task_id="test_task_001",
    )
    assert alert.status == AlertStatus.ACTIVE, "告警状态错误"
    print(f"  ✅ 告警创建成功: {alert.alert_id}")
    
    # 测试告警确认
    alert = await store.acknowledge_alert("test_alert_001")
    assert alert.status == AlertStatus.ACKNOWLEDGED, "告警确认状态错误"
    print(f"  ✅ 告警确认成功")
    
    # 测试告警解决
    alert = await store.resolve_alert("test_alert_001")
    assert alert.status == AlertStatus.RESOLVED, "告警解决状态错误"
    print(f"  ✅ 告警解决成功")
    
    # 测试添加日志
    await store.add_log("test_task_001", {"level": "info", "message": "测试日志"})
    logs = await store.get_task_logs("test_task_001")
    assert len(logs) == 1, f"日志数错误，期望1，实际{len(logs)}"
    print(f"  ✅ 日志添加/查询成功: {len(logs)}条")
    
    # 测试创建快照
    snapshot = await store.create_snapshot(
        task_id="test_task_001",
        description="测试快照",
        state={"test": True},
    )
    assert snapshot.snapshot_id is not None, "快照ID为空"
    print(f"  ✅ 快照创建成功: {snapshot.snapshot_id}")
    
    # 测试任务完整汇总
    summary = await store.get_task_summary("test_task_001")
    assert summary["task"] is not None, "任务汇总中任务为空"
    assert summary["logs"] is not None, "任务汇总中日志为空"
    assert "summary" in summary, "任务汇总中缺少summary"
    print(f"  ✅ 任务完整汇总成功: 日志={len(summary['logs'])}条, 快照={len(summary['snapshots'])}个")
    
    # 测试统计信息
    stats = await store.get_stats()
    assert stats["tasks_total"] >= 1, "任务总数错误"
    assert stats["tasks_completed"] >= 1, "已完成任务数错误"
    print(f"  ✅ 统计信息正确: 任务总数={stats['tasks_total']}, 已完成={stats['tasks_completed']}")
    
    # 测试持久化（重新加载）
    store2 = StateStore(persist_dir=tmp_dir)
    task2 = await store2.get_task("test_task_001")
    assert task2 is not None, "持久化加载后任务为空"
    assert task2.task_id == "test_task_001", "持久化加载后任务ID错误"
    print(f"  ✅ 持久化/加载成功: 任务{task2.task_id}已恢复")
    
    print("  ✅ 测试通过")
    return True


async def test_commander():
    """测试5：统一门面Commander"""
    print("\n" + "=" * 60)
    print("测试5：统一门面Commander")
    print("=" * 60)
    
    from app.commander import Commander, TaskType, RunMode, CommanderResult, init_commander
    
    # 初始化
    commander = init_commander(config={"test": True})
    assert commander is not None, "Commander初始化失败"
    print(f"  ✅ Commander初始化完成")
    
    # 测试任务ID生成
    task_id = commander._generate_task_id()
    assert task_id.startswith("task_"), "任务ID格式错误"
    print(f"  ✅ 任务ID生成成功: {task_id}")
    
    # 测试任务类型自动判断
    # 单角色
    task_type = commander._detect_task_type("简单命令", role_name="分析")
    assert task_type == TaskType.SINGLE_ROLE, f"单角色判断错误: {task_type}"
    print(f"  ✅ 单角色判断正确")
    
    # 多角色（指定多个角色）
    task_type = commander._detect_task_type("协同任务", role_names=["分析", "生成"])
    assert task_type == TaskType.MULTI_ROLE, f"多角色判断错误: {task_type}"
    print(f"  ✅ 多角色判断正确（指定多个角色）")
    
    # 多角色（关键词）
    task_type = commander._detect_task_type("请并行处理这个任务")
    assert task_type == TaskType.MULTI_ROLE, f"关键词判断错误: {task_type}"
    print(f"  ✅ 多角色判断正确（关键词检测）")
    
    # 测试统计信息
    stats = await commander.get_stats()
    assert "async_tasks_running" in stats, "统计信息缺少async_tasks_running"
    print(f"  ✅ 统计信息正确: 异步任务={stats['async_tasks_running']}")
    
    # 注意：完整的submit_task测试需要ManusWithRoles和MultiRoleOrchestrator，
    # 这里只测试Commander的基础功能，完整集成测试在后续阶段进行
    print("  ℹ️  完整的submit_task集成测试将在后续阶段进行（需要ManusWithRoles）")
    
    print("  ✅ 测试通过")
    return True


async def test_integration():
    """测试6：P0核心模块集成测试"""
    print("\n" + "=" * 60)
    print("测试6：P0核心模块集成测试")
    print("=" * 60)
    
    from app.event_bus import get_event_bus, EventType
    from app.state_store import get_state_store, TaskStatus
    from app.resource_manager import get_resource_manager
    from app.commander import get_commander
    
    # 获取所有单例实例
    bus = get_event_bus()
    store = get_state_store()
    rm = get_resource_manager()
    commander = get_commander()
    
    print(f"  ✅ 所有单例实例获取成功")
    print(f"    - EventBus: {bus is not None}")
    print(f"    - StateStore: {store is not None}")
    print(f"    - ResourceManager: {rm is not None}")
    print(f"    - Commander: {commander is not None}")
    
    # 测试事件驱动状态更新
    # 模拟：任务提交事件 → 状态中心创建任务
    test_task_id = "integration_test_001"
    
    # 订阅任务提交事件
    event_received = asyncio.Event()
    
    async def on_task_submitted(event):
        # 事件触发后，在状态中心创建任务
        await store.create_task(
            task_id=event.task_id,
            command=event.message,
            role_name=event.role_name,
        )
        event_received.set()
    
    bus.subscribe("task_submitted", on_task_submitted)
    
    # 发布事件
    await bus.publish_simple(
        EventType.TASK_SUBMITTED,
        message="集成测试任务",
        task_id=test_task_id,
        role_name="测试角色",
    )
    
    # 等待事件处理
    await asyncio.wait_for(event_received.wait(), timeout=5.0)
    
    # 验证状态中心已创建任务
    task = await store.get_task(test_task_id)
    assert task is not None, "事件驱动后任务未创建"
    assert task.task_id == test_task_id, "事件驱动后任务ID错误"
    print(f"  ✅ 事件驱动状态更新成功: 任务{task.task_id}已创建")
    
    # 测试资源锁与事件联动
    resource_acquired = asyncio.Event()
    
    async def on_task_start(event):
        # 任务开始时获取资源
        async with rm.acquire_browser(f"任务_{event.task_id}"):
            resource_acquired.set()
            await asyncio.sleep(0.1)
    
    bus.subscribe("task_start", on_task_start)
    
    await bus.publish_simple(
        EventType.TASK_START,
        message="集成测试任务开始",
        task_id=test_task_id,
    )
    
    await asyncio.wait_for(resource_acquired.wait(), timeout=5.0)
    print(f"  ✅ 资源锁与事件联动成功")
    
    # 测试任务完成事件
    task_completed = asyncio.Event()
    
    async def on_task_done(event):
        await store.update_task_status(event.task_id, TaskStatus.COMPLETED, progress=1.0)
        task_completed.set()
    
    bus.subscribe("task_done", on_task_done)
    
    await bus.publish_simple(
        EventType.TASK_DONE,
        message="集成测试任务完成",
        task_id=test_task_id,
    )
    
    await asyncio.wait_for(task_completed.wait(), timeout=5.0)
    
    task = await store.get_task(test_task_id)
    assert task.status == TaskStatus.COMPLETED, "事件驱动后任务状态未更新为完成"
    print(f"  ✅ 任务完成事件驱动状态更新成功")
    
    print("  ✅ 集成测试通过")
    return True


async def main():
    """主测试函数"""
    print("=" * 60)
    print("P0核心稳定性模块集成测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version}")
    
    results = {}
    
    tests = [
        ("全局网络超时控制", test_global_timeout),
        ("全局资源锁ResourceManager", test_resource_manager),
        ("轻量事件总线EventBus", test_event_bus),
        ("全局统一状态中心StateStore", test_state_store),
        ("统一门面Commander", test_commander),
        ("P0核心模块集成测试", test_integration),
    ]
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = "✅ 通过"
        except Exception as e:
            results[name] = f"❌ 失败: {str(e)[:100]}"
            import traceback
            traceback.print_exc()
    
    # 输出测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results.items():
        print(f"  {name}: {result}")
        if "通过" in result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)}个测试, {passed}个通过, {failed}个失败")
    
    if failed == 0:
        print("\n🎉 所有P0核心模块测试通过！")
        return 0
    else:
        print(f"\n⚠️  有{failed}个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
