# -*- coding: utf-8 -*-
"""
test_e2e_commander.py · 统帅端到端测试
==========================================
测试OpenManus统帅体系的完整工作流程：
1. Commander接收任务，自动判断单角色/多角色
2. 事件总线驱动状态更新（TaskSubmitted → TaskStart → TaskProgress → TaskDone）
3. 状态中心记录完整过程（任务/角色/告警/日志/快照）
4. 资源锁控制并发
5. 任务完成后自动归档到经验包

这个测试不依赖真实的ManusWithRoles，而是模拟其行为，
验证Commander的调度逻辑、事件驱动、状态管理是否正常工作。
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入P0核心模块
from app.commander import Commander, TaskType, RunMode, CommanderResult, get_commander
from app.event_bus import EventBus, EventType, Event, get_event_bus, publish_event
from app.state_store import (
    StateStore, TaskStatus, RoleStatus, AlertStatus,
    get_state_store, TaskState, RoleState
)
from app.resource_manager import ResourceManager, get_resource_manager, setup_global_timeout


class MockManusWithRoles:
    """模拟ManusWithRoles，用于测试Commander调度逻辑"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.current_role = None
        self.call_count = 0
    
    async def run_with_role(self, role_name: str, command: str) -> dict:
        """模拟用指定角色执行任务"""
        self.current_role = role_name
        self.call_count += 1
        
        # 模拟执行时间
        await asyncio.sleep(0.1)
        
        # 模拟不同角色的输出
        role_outputs = {
            "分析": f"【分析角色】已分析: {command[:30]}... 主要观点: 测试通过",
            "生成": f"【生成角色】已生成: {command[:30]}... 生成内容: 测试文本",
            "匹配": f"【匹配角色】已匹配: {command[:30]}... 匹配结果: 3个匹配项",
            "老师": f"【老师角色】已讲解: {command[:30]}... 讲解完成",
            "学生": f"【学生角色】已学习: {command[:30]}... 学习完成",
            "每天更新": f"【每天更新角色】已更新: {command[:30]}... 更新完成",
            "小助手": f"【小助手角色】已处理: {command[:30]}... 处理完成",
            "脚本": f"【脚本角色】已执行: {command[:30]}... 执行完成",
            "文件夹管理员": f"【管理员角色】已管理: {command[:30]}... 管理完成",
        }
        
        output = role_outputs.get(role_name, f"【{role_name}】已处理: {command[:30]}")
        
        return {
            "output": output,
            "role": role_name,
            "call_count": self.call_count,
            "success": True,
        }
    
    async def run_with_auto_role(self, command: str) -> dict:
        """模拟自动选择角色执行任务"""
        # 简单的角色选择逻辑
        if "分析" in command or "总结" in command:
            role = "分析"
        elif "生成" in command or "写" in command:
            role = "生成"
        elif "匹配" in command:
            role = "匹配"
        else:
            role = "分析"
        
        return await self.run_with_role(role, command)
    
    def list_available_roles(self) -> list:
        """列出可用角色"""
        return ["文件夹管理员", "每天更新", "老师", "分析", "生成", "学生", "匹配", "小助手", "脚本"]
    
    def explain_role_selection(self, command: str) -> dict:
        """解释角色选择"""
        return {
            "selected": "分析",
            "reason": f"命令包含分析相关关键词: {command[:20]}",
            "confidence": 0.85,
        }


class MockMultiRoleOrchestrator:
    """模拟MultiRoleOrchestrator，用于测试多角色协同"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.call_count = 0
    
    async def run_pipeline(self, role_names: list, initial_input: str) -> dict:
        """模拟串行流水线执行"""
        self.call_count += 1
        results = []
        current_input = initial_input
        
        for i, role_name in enumerate(role_names):
            await asyncio.sleep(0.05)
            result = {
                "role": role_name,
                "step": i + 1,
                "input": current_input[:30],
                "output": f"【{role_name}】步骤{i+1}处理完成",
                "success": True,
            }
            results.append(result)
            current_input = result["output"]
        
        return {
            "mode": "pipeline",
            "roles": role_names,
            "results": results,
            "final_output": results[-1]["output"] if results else "",
            "success": True,
        }
    
    async def run_parallel(self, role_names: list, tasks: list) -> dict:
        """模拟并行执行"""
        self.call_count += 1
        
        async def run_one(role_name, task):
            await asyncio.sleep(0.05)
            return {
                "role": role_name,
                "task": task[:30],
                "output": f"【{role_name}】并行处理完成",
                "success": True,
            }
        
        results = await asyncio.gather(*[
            run_one(role, task) for role, task in zip(role_names, tasks)
        ])
        
        return {
            "mode": "parallel",
            "roles": role_names,
            "results": results,
            "success": True,
        }


async def test_e2e_single_role():
    """测试1：单角色端到端流程"""
    print("\n" + "=" * 70)
    print("测试1：单角色端到端流程")
    print("=" * 70)
    
    # 获取组件
    commander = get_commander()
    bus = get_event_bus()
    store = get_state_store()
    rm = get_resource_manager()
    
    # 注入Mock组件
    commander._manus_with_roles = MockManusWithRoles()
    
    # 记录收到的事件
    received_events = []
    
    async def event_logger(event: Event):
        received_events.append({
            "type": event.event_type.value,
            "task_id": event.task_id,
            "message": event.message,
            "timestamp": datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S.%f")[:-3],
        })
        print(f"  📨 [{event.event_type.value}] {event.message}")
    
    # 订阅所有任务事件
    bus.subscribe("task_*", event_logger)
    bus.subscribe("role_*", event_logger)
    
    # 提交单角色任务（同步模式）
    print("\n  🚀 提交单角色任务...")
    result = await commander.submit_task(
        command="请分析这段文本的主要观点和核心论点",
        task_type=TaskType.SINGLE_ROLE,
        run_mode=RunMode.SYNC,
        role_name="分析",
    )
    
    # 验证结果
    assert isinstance(result, CommanderResult), "返回类型错误"
    assert result.status == TaskStatus.COMPLETED, f"任务状态错误: {result.status}"
    assert result.task_type == TaskType.SINGLE_ROLE, "任务类型错误"
    assert result.role_used == "分析", f"使用角色错误: {result.role_used}"
    assert result.error is None, f"任务有错误: {result.error}"
    assert "output" in result.result, "结果中缺少output"
    
    print(f"\n  ✅ 任务完成")
    print(f"     任务ID: {result.task_id}")
    print(f"     状态: {result.status.value}")
    print(f"     使用角色: {result.role_used}")
    print(f"     耗时: {result.duration:.2f}秒")
    output = result.result.get('output', '')
    if isinstance(output, str):
        print(f"     输出: {output[:50]}...")
    else:
        print(f"     输出: {str(output)[:50]}...")
    
    # 验证事件
    event_types = [e["type"] for e in received_events]
    assert "task_submitted" in event_types, "缺少task_submitted事件"
    assert "task_start" in event_types, "缺少task_start事件"
    assert "task_done" in event_types, "缺少task_done事件"
    assert "role_activate" in event_types, "缺少role_activate事件"
    assert "role_deactivate" in event_types, "缺少role_deactivate事件"
    
    print(f"\n  ✅ 事件驱动验证通过")
    print(f"     收到事件数: {len(received_events)}")
    print(f"     事件类型: {', '.join(set(event_types))}")
    
    # 验证状态中心
    task = await store.get_task(result.task_id)
    assert task is not None, "状态中心中没有任务记录"
    assert task.status == TaskStatus.COMPLETED, "状态中心中任务状态错误"
    
    print(f"\n  ✅ 状态中心验证通过")
    print(f"     任务状态: {task.status.value}")
    print(f"     任务进度: {task.progress}")
    print(f"     创建时间: {datetime.fromtimestamp(task.created_at).strftime('%H:%M:%S')}")
    
    # 验证资源锁
    stats = await rm.get_stats()
    assert stats["active_browsers"] == 0, "资源锁没有正确释放"
    
    print(f"\n  ✅ 资源锁验证通过")
    print(f"     活跃浏览器: {stats['active_browsers']}")
    print(f"     最大并发: {stats['max_concurrent_browsers']}")
    
    print("\n  🎉 单角色端到端测试通过！")
    return True


async def test_e2e_multi_role():
    """测试2：多角色协同端到端流程"""
    print("\n" + "=" * 70)
    print("测试2：多角色协同端到端流程")
    print("=" * 70)
    
    commander = get_commander()
    bus = get_event_bus()
    store = get_state_store()
    
    # 注入Mock组件
    commander._multi_role_orchestrator = MockMultiRoleOrchestrator()
    
    # 记录事件
    received_events = []
    
    async def event_logger(event: Event):
        received_events.append(event.event_type.value)
        print(f"  📨 [{event.event_type.value}] {event.message}")
    
    bus.subscribe("task_*", event_logger)
    
    # 提交多角色任务（流水线模式）
    print("\n  🚀 提交多角色流水线任务...")
    result = await commander.submit_task(
        command="请协同完成：先分析文本，再生成摘要，最后匹配相关内容",
        task_type=TaskType.MULTI_ROLE,
        run_mode=RunMode.SYNC,
        role_names=["分析", "生成", "匹配"],
    )
    
    # 验证结果
    assert result.status == TaskStatus.COMPLETED, f"任务状态错误: {result.status}"
    assert result.task_type == TaskType.MULTI_ROLE, "任务类型错误"
    assert len(result.roles_used) == 3, f"使用角色数错误: {len(result.roles_used)}"
    assert "output" in result.result, "结果中缺少output"
    
    print(f"\n  ✅ 多角色任务完成")
    print(f"     任务ID: {result.task_id}")
    print(f"     使用角色: {', '.join(result.roles_used)}")
    print(f"     耗时: {result.duration:.2f}秒")
    
    # 验证事件
    assert "task_submitted" in received_events
    assert "task_start" in received_events
    assert "task_done" in received_events
    
    print(f"\n  ✅ 事件驱动验证通过，收到{len(received_events)}个事件")
    
    # 验证状态中心
    task = await store.get_task(result.task_id)
    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    
    print(f"  ✅ 状态中心验证通过")
    
    print("\n  🎉 多角色协同端到端测试通过！")
    return True


async def test_e2e_async_task():
    """测试3：异步后台任务端到端流程"""
    print("\n" + "=" * 70)
    print("测试3：异步后台任务端到端流程")
    print("=" * 70)
    
    commander = get_commander()
    store = get_state_store()
    
    # 注入Mock组件
    commander._manus_with_roles = MockManusWithRoles()
    
    # 提交异步任务
    print("\n  🚀 提交异步后台任务...")
    task_id = await commander.submit_task(
        command="这是一个异步任务，请处理",
        task_type=TaskType.SINGLE_ROLE,
        run_mode=RunMode.ASYNC,
        role_name="小助手",
    )
    
    assert isinstance(task_id, str), "异步模式应返回task_id字符串"
    assert task_id.startswith("task_"), "task_id格式错误"
    
    print(f"  ✅ 异步任务已提交，task_id: {task_id}")
    
    # 查询任务状态（应该是running或pending）
    await asyncio.sleep(0.05)
    status = await commander.get_task_status(task_id)
    assert status is not None, "无法查询任务状态"
    
    print(f"  📊 任务状态: {status.status.value}")
    
    # 等待任务完成
    print("  ⏳ 等待任务完成...")
    for i in range(20):
        await asyncio.sleep(0.1)
        status = await commander.get_task_status(task_id)
        if status.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            break
    
    assert status.status == TaskStatus.COMPLETED, f"异步任务未完成: {status.status}"
    
    print(f"  ✅ 异步任务完成")
    print(f"     最终状态: {status.status.value}")
    print(f"     使用角色: {status.role_used}")
    
    # 验证状态中心
    task = await store.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    
    print(f"  ✅ 状态中心验证通过")
    
    print("\n  🎉 异步后台任务端到端测试通过！")
    return True


async def test_e2e_auto_role_detection():
    """测试4：自动角色判断端到端流程"""
    print("\n" + "=" * 70)
    print("测试4：自动角色判断端到端流程")
    print("=" * 70)
    
    commander = get_commander()
    
    # 测试各种命令的自动判断
    test_cases = [
        ("请分析这段文本的主要观点", TaskType.SINGLE_ROLE, "单角色（分析）"),
        ("请生成一篇关于AI的文章", TaskType.SINGLE_ROLE, "单角色（生成）"),
        ("请协同完成分析和生成", TaskType.MULTI_ROLE, "多角色（关键词检测）"),
        ("请并行处理这三个任务", TaskType.MULTI_ROLE, "多角色（关键词检测）"),
    ]
    
    print("\n  🧪 测试自动角色判断...")
    for command, expected_type, description in test_cases:
        detected_type = commander._detect_task_type(command)
        status = "✅" if detected_type == expected_type else "❌"
        print(f"  {status} [{description}] 命令: {command[:25]}... → 检测: {detected_type.value}")
        assert detected_type == expected_type, f"判断错误: {command}"
    
    print("\n  🎉 自动角色判断端到端测试通过！")
    return True


async def test_e2e_state_persistence():
    """测试5：状态持久化端到端流程"""
    print("\n" + "=" * 70)
    print("测试5：状态持久化端到端流程")
    print("=" * 70)
    
    import tempfile
    
    # 创建临时持久化目录
    tmp_dir = tempfile.mkdtemp()
    print(f"\n  📁 持久化目录: {tmp_dir}")
    
    # 创建新的状态中心（带持久化）
    store1 = StateStore(persist_dir=tmp_dir)
    
    # 创建一些测试数据
    await store1.create_task("persist_test_001", "测试持久化", role_name="分析")
    await store1.update_task_status("persist_test_001", TaskStatus.COMPLETED, progress=1.0)
    await store1.activate_role("测试角色", permission_level=1)
    await store1.create_alert("alert_001", "error", "测试告警")
    await store1.add_log("persist_test_001", {"level": "info", "message": "测试日志"})
    await store1.create_snapshot("persist_test_001", "测试快照", {"test": True})
    
    print("  ✅ 测试数据已创建")
    
    # 创建新的状态中心实例，验证数据已持久化
    store2 = StateStore(persist_dir=tmp_dir)
    
    # 验证任务
    task = await store2.get_task("persist_test_001")
    assert task is not None, "持久化后任务丢失"
    assert task.status == TaskStatus.COMPLETED, "持久化后任务状态错误"
    print(f"  ✅ 任务持久化验证通过: {task.task_id}, 状态: {task.status.value}")
    
    # 验证角色
    active_roles = await store2.get_active_roles()
    assert len(active_roles) >= 1, "持久化后角色丢失"
    print(f"  ✅ 角色持久化验证通过: {len(active_roles)}个活跃角色")
    
    # 验证告警
    active_alerts = await store2.get_active_alerts()
    assert len(active_alerts) >= 1, "持久化后告警丢失"
    print(f"  ✅ 告警持久化验证通过: {len(active_alerts)}个活跃告警")
    
    # 验证日志
    logs = await store2.get_task_logs("persist_test_001")
    assert len(logs) >= 1, "持久化后日志丢失"
    print(f"  ✅ 日志持久化验证通过: {len(logs)}条日志")
    
    # 验证统计
    stats = await store2.get_stats()
    print(f"  📊 统计信息: 任务={stats['tasks_total']}, 角色={stats['roles_active']}, 告警={stats['alerts_active']}")
    
    print("\n  🎉 状态持久化端到端测试通过！")
    return True


async def test_e2e_concurrent_resource():
    """测试6：并发资源锁端到端流程"""
    print("\n" + "=" * 70)
    print("测试6：并发资源锁端到端流程")
    print("=" * 70)
    
    rm = get_resource_manager()
    
    # 测试并发获取资源（最大并发=1，所以应该串行执行）
    print("\n  🔄 测试并发资源锁（最大并发=1）...")
    
    concurrent_count = 0
    max_concurrent = 0
    execution_order = []
    
    async def task_with_resource(task_id):
        nonlocal concurrent_count, max_concurrent
        async with rm.acquire_browser(f"并发任务_{task_id}"):
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            execution_order.append(task_id)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
    
    # 同时启动3个任务
    tasks = [task_with_resource(i) for i in range(3)]
    await asyncio.gather(*tasks)
    
    # 验证：最大并发应该是1（因为max_concurrent_browsers=1）
    assert max_concurrent == 1, f"最大并发错误，期望1，实际{max_concurrent}"
    assert len(execution_order) == 3, "执行次数错误"
    
    print(f"  ✅ 并发资源锁验证通过")
    print(f"     最大并发数: {max_concurrent}（期望1）")
    print(f"     执行顺序: {execution_order}")
    print(f"     总执行次数: {len(execution_order)}")
    
    # 测试资源统计
    stats = await rm.get_stats()
    assert stats["active_browsers"] == 0, "所有资源应已释放"
    print(f"  ✅ 资源释放验证通过: 活跃浏览器={stats['active_browsers']}")
    
    print("\n  🎉 并发资源锁端到端测试通过！")
    return True


async def main():
    """主测试函数"""
    print("=" * 70)
    print("OpenManus统帅体系 - 端到端测试")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 初始化全局组件
    print("\n" + "=" * 70)
    print("初始化全局组件")
    print("=" * 70)
    
    setup_global_timeout(180)
    print("  ✅ 全局网络超时已设置: 180秒")
    
    rm = get_resource_manager()
    print(f"  ✅ 资源管理器已初始化: 最大并发={rm.max_concurrent_browsers}")
    
    bus = get_event_bus()
    print(f"  ✅ 事件总线已初始化: 模式={'异步' if bus.async_mode else '同步'}")
    
    store = get_state_store()
    print(f"  ✅ 状态中心已初始化: 持久化={'是' if store.persist_dir else '否'}")
    
    commander = get_commander()
    print(f"  ✅ 统帅Commander已初始化")
    
    # 运行所有测试
    results = {}
    
    tests = [
        ("单角色端到端流程", test_e2e_single_role),
        ("多角色协同端到端流程", test_e2e_multi_role),
        ("异步后台任务端到端流程", test_e2e_async_task),
        ("自动角色判断端到端流程", test_e2e_auto_role_detection),
        ("状态持久化端到端流程", test_e2e_state_persistence),
        ("并发资源锁端到端流程", test_e2e_concurrent_resource),
    ]
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = "✅ 通过"
        except Exception as e:
            results[name] = f"❌ 失败: {str(e)[:80]}"
            import traceback
            traceback.print_exc()
    
    # 输出测试结果汇总
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = 0
    failed = 0
    for name, result in results.items():
        print(f"  {name}: {result}")
        if "通过" in result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)}个测试, {passed}个通过, {failed}个失败")
    
    # 输出最终状态
    print("\n" + "=" * 70)
    print("最终系统状态")
    print("=" * 70)
    
    stats = await store.get_stats()
    print(f"  状态中心: 任务={stats['tasks_total']}, 已完成={stats['tasks_completed']}, 活跃角色={stats['roles_active']}")
    
    rm_stats = await rm.get_stats()
    print(f"  资源管理: 活跃浏览器={rm_stats['active_browsers']}, 最大并发={rm_stats['max_concurrent_browsers']}")
    
    bus_stats = bus.get_stats()
    print(f"  事件总线: 事件历史={bus_stats['event_history_count']}, 订阅者={sum(bus_stats['subscribers_count'].values())}")
    
    if failed == 0:
        print("\n" + "🎉" * 20)
        print("🎉 所有端到端测试通过！统帅体系可以正常工作！")
        print("🎉" * 20)
        return 0
    else:
        print(f"\n⚠️  有{failed}个测试失败，需要修复后再打包")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
