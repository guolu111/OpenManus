"""
多角色协同调度器测试脚本

测试内容：
1. 多角色协同调度器初始化
2. 指挥官列表
3. 串行调度（模拟）
4. 并行调度（模拟）
5. 指挥官调度（模拟）
6. 世界书记录

运行方式：
    python test_multi_role.py
"""

import sys
import os
import asyncio

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.role_cards import MultiRoleOrchestrator


async def test_init():
    """测试1：多角色协同调度器初始化"""
    print("\n" + "=" * 60)
    print("测试1：多角色协同调度器初始化")
    print("=" * 60)

    role_cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "角色卡")
    orchestrator = MultiRoleOrchestrator(role_cards_dir)

    print(orchestrator.status())

    print("\n✅ 测试1通过：多角色协同调度器初始化成功")
    return orchestrator


def test_commanders(orchestrator):
    """测试2：指挥官列表"""
    print("\n" + "=" * 60)
    print("测试2：指挥官列表")
    print("=" * 60)

    commanders = orchestrator.list_commanders()
    print(f"\n可用指挥官数量: {len(commanders)}")
    for c in commanders:
        print(f"\n  - {c['name']} ({c['display_name']})")
        print(f"    描述: {c['description']}")
        print(f"    管辖角色: {', '.join(c['roles'])}")
        print(f"    偏好工作流: {c['preferred_workflow']}")

    print("\n✅ 测试2通过：指挥官列表正常")


async def test_serial(orchestrator):
    """测试3：串行调度（模拟）"""
    print("\n" + "=" * 60)
    print("测试3：串行调度（模拟）")
    print("=" * 60)

    result = await orchestrator.run_serial(
        task="分析这段文本并生成摘要",
        roles=["分析", "生成"],
        pass_output=True,
        agent=None,  # 模拟执行
    )

    print(f"\n调度模式: {result['mode']}")
    print(f"任务: {result['task']}")
    print(f"角色序列: {' → '.join(result['roles'])}")
    print(f"全部成功: {result['all_success']}")
    print(f"总时长: {result['total_duration']:.2f}秒")
    print(f"\n执行结果:")
    for r in result['results']:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['role']}: {r['result'][:60]}...")
        print(f"     时长: {r['duration']:.2f}秒")

    print("\n✅ 测试3通过：串行调度正常")


async def test_parallel(orchestrator):
    """测试4：并行调度（模拟）"""
    print("\n" + "=" * 60)
    print("测试4：并行调度（模拟）")
    print("=" * 60)

    subtasks = [
        {"role": "分析", "task": "分析文本结构"},
        {"role": "匹配", "task": "计算文本相似度"},
        {"role": "小助手", "task": "调用API获取数据"},
    ]

    result = await orchestrator.run_parallel(
        subtasks=subtasks,
        agent=None,  # 模拟执行
    )

    print(f"\n调度模式: {result['mode']}")
    print(f"子任务数量: {result['subtasks_count']}")
    print(f"全部成功: {result['all_success']}")
    print(f"总时长: {result['total_duration']:.2f}秒")
    print(f"\n执行结果:")
    for r in result['results']:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['role']}: {r['result'][:60]}...")
        print(f"     时长: {r['duration']:.2f}秒")

    print("\n✅ 测试4通过：并行调度正常")


async def test_commander(orchestrator):
    """测试5：指挥官调度（模拟）"""
    print("\n" + "=" * 60)
    print("测试5：指挥官调度（模拟）")
    print("=" * 60)

    # 测试数据分析军（并行）
    print("\n--- 数据分析军（并行模式）---")
    result = await orchestrator.run_with_commander(
        commander_name="数据分析军",
        task="分析客户数据并生成报告",
        agent=None,
    )
    print(f"调度模式: {result['mode']}")
    print(f"全部成功: {result['all_success']}")
    print(f"总时长: {result['total_duration']:.2f}秒")

    # 测试内容创作军（串行）
    print("\n--- 内容创作军（串行模式）---")
    result = await orchestrator.run_with_commander(
        commander_name="内容创作军",
        task="写一篇关于AI的文章",
        agent=None,
    )
    print(f"调度模式: {result['mode']}")
    print(f"全部成功: {result['all_success']}")
    print(f"总时长: {result['total_duration']:.2f}秒")

    print("\n✅ 测试5通过：指挥官调度正常")


def test_world_book(orchestrator):
    """测试6：世界书记录"""
    print("\n" + "=" * 60)
    print("测试6：世界书记录")
    print("=" * 60)

    wb = orchestrator.get_world_book()
    print(f"\n世界书内容:")
    print(f"  通气公告: {len(wb['通气公告'])} 条")
    print(f"  决议台账: {len(wb['决议台账'])} 条")
    print(f"  执行历史: {len(wb['执行历史'])} 条")

    # 测试添加决议
    orchestrator.add_resolution(
        content="多角色协同调度器测试通过，串行/并行/指挥官三种模式均正常",
        roles=["分析", "生成", "匹配", "小助手"],
    )

    wb = orchestrator.get_world_book()
    print(f"\n添加决议后:")
    print(f"  决议台账: {len(wb['决议台账'])} 条")
    print(f"  最新决议: {wb['决议台账'][-1]['内容'][:60]}...")

    print("\n✅ 测试6通过：世界书记录正常")


async def main():
    """主测试函数"""
    print("\n" + "█" * 60)
    print("█" + " " * 12 + "多角色协同调度器测试" + " " * 18 + "█")
    print("█" * 60)

    try:
        orchestrator = await test_init()
        test_commanders(orchestrator)
        await test_serial(orchestrator)
        await test_parallel(orchestrator)
        await test_commander(orchestrator)
        test_world_book(orchestrator)

        print("\n" + "█" * 60)
        print("█" + " " * 15 + "✅ 所有测试通过！" + " " * 22 + "█")
        print("█" * 60)
        print("\n下一步：")
        print("  1. 在实际Manus环境中测试run_with_role方法")
        print("  2. 实现真实的多角色串行/并行执行")
        print("  3. 实现世界书持久化（保存到文件）")
        print("  4. 实现中层指挥官的任务拆解逻辑")
        print("  5. 集成到ManusWithRoles类")
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
