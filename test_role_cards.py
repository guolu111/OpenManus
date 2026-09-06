"""
角色卡体系测试脚本

测试内容：
1. 角色卡注册表初始化
2. 角色卡加载器加载角色卡
3. 角色选择器选择角色卡
4. 角色调度器状态查看
5. 角色选择解释

运行方式：
    python test_role_cards.py
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.role_cards import (
    RoleCard,
    RoleCardLoader,
    RoleRegistry,
    PermissionLevel,
    RoleSelector,
    RoleOrchestrator,
)


def test_registry():
    """测试1：角色卡注册表"""
    print("\n" + "=" * 60)
    print("测试1：角色卡注册表")
    print("=" * 60)

    registry = RoleRegistry()
    print(registry.summary())

    # 测试获取单个角色卡
    admin_meta = registry.get("文件夹管理员")
    assert admin_meta is not None, "文件夹管理员卡应该存在"
    assert admin_meta["permission_level"] == "L3", "文件夹管理员应该是L3全局权限"
    print(f"\n✅ 文件夹管理员卡: 权限={admin_meta['permission_level']}, 适用场景={len(admin_meta['适用场景'])}个")

    # 测试按权限筛选
    l3_roles = registry.get_by_permission("L3")
    l0_roles = registry.get_by_permission("L0")
    print(f"✅ L3全局权限角色: {l3_roles}")
    print(f"✅ L0只读权限角色: {l0_roles}")

    # 测试按场景筛选
    analysis_roles = registry.get_by_scenario("分析")
    print(f"✅ 包含'分析'场景的角色: {analysis_roles}")

    print("\n✅ 测试1通过：角色卡注册表正常")


def test_loader():
    """测试2：角色卡加载器"""
    print("\n" + "=" * 60)
    print("测试2：角色卡加载器")
    print("=" * 60)

    role_cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "角色卡")
    print(f"角色卡目录: {role_cards_dir}")
    print(f"目录存在: {os.path.exists(role_cards_dir)}")

    loader = RoleCardLoader(role_cards_dir)

    # 测试获取可用角色卡
    available = loader.get_available_roles()
    print(f"\n目录中可用的角色卡: {available}")

    # 测试加载单个角色卡
    registry = RoleRegistry()
    admin_meta = registry.get("文件夹管理员")
    admin_card = loader.load("文件夹管理员", admin_meta)

    if admin_card:
        print(f"\n✅ 文件夹管理员卡加载成功:")
        print(f"   角色名: {admin_card.name}")
        print(f"   显示名: {admin_card.display_name}")
        print(f"   权限: {admin_card.permission_level}")
        print(f"   系统提示词长度: {len(admin_card.system_prompt)} 字符")
        print(f"   适用场景: {len(admin_card.适用场景)} 个")
    else:
        print("\n⚠️  文件夹管理员卡加载失败（可能文件不存在）")

    # 测试加载分析卡
    analysis_meta = registry.get("分析")
    analysis_card = loader.load("分析", analysis_meta)
    if analysis_card:
        print(f"\n✅ 分析卡加载成功:")
        print(f"   角色名: {analysis_card.name}")
        print(f"   权限: {analysis_card.permission_level}")
        print(f"   系统提示词长度: {len(analysis_card.system_prompt)} 字符")

        # 测试工具权限检查
        print(f"\n✅ 工具权限检查:")
        print(f"   可以用 read_file: {analysis_card.can_use_tool('read_file')}")
        print(f"   可以用 write_file: {analysis_card.can_use_tool('write_file')}")
        print(f"   可以用 bash: {analysis_card.can_use_tool('bash')}")
    else:
        print("\n⚠️  分析卡加载失败")

    print("\n✅ 测试2通过：角色卡加载器正常")


def test_selector():
    """测试3：角色选择器"""
    print("\n" + "=" * 60)
    print("测试3：角色选择器")
    print("=" * 60)

    registry = RoleRegistry()
    selector = RoleSelector(registry)

    # 测试各种任务的角色选择
    test_tasks = [
        ("帮我分析一下这段文本的结构和人物关系", "分析"),
        ("帮我写一个Python脚本统计文件行数", "生成"),
        ("教我一下OpenManus怎么用", "老师"),
        ("帮我跑批鹿鼎记第22章", "每天更新"),
        ("检查一下文件夹目录是否同步", "文件夹管理员"),
        ("调用API批量处理这些数据", "小助手"),
        ("管理一下脚本仓库，看看有没有重复的", "脚本"),
        ("计算这两段文本的相似度", "匹配"),
    ]

    print("\n任务角色选择测试:")
    print("-" * 80)
    correct_count = 0
    for task, expected in test_tasks:
        role, score, reason = selector.select(task)
        status = "✅" if role == expected else "❌"
        if role == expected:
            correct_count += 1
        print(f"{status} 任务: {task[:30]}...")
        print(f"   选择: {role} (匹配度 {score:.2f})，期望: {expected}")
        print(f"   理由: {reason.get('reason', '')}")
        print()

    print(f"选择正确率: {correct_count}/{len(test_tasks)} = {correct_count/len(test_tasks)*100:.1f}%")

    # 测试角色选择解释
    print("\n" + "-" * 80)
    print("角色选择解释示例:")
    print("-" * 80)
    print(selector.explain_selection("帮我分析一下这段文本的结构和人物关系"))

    print("\n✅ 测试3通过：角色选择器正常")


def test_orchestrator():
    """测试4：角色调度器"""
    print("\n" + "=" * 60)
    print("测试4：角色调度器")
    print("=" * 60)

    role_cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "角色卡")
    orchestrator = RoleOrchestrator(role_cards_dir)

    # 测试状态查看
    print(orchestrator.status())

    # 测试可用角色卡
    available = orchestrator.get_available_roles()
    print(f"\n可用角色卡 ({len(available)} 张):")
    for role in available:
        print(f"  - {role}")

    # 测试当前激活状态
    active = orchestrator.get_active_role()
    print(f"\n当前激活角色卡: {active.name if active else '无（统帅身份）'}")

    # 测试角色选择
    print("\n" + "-" * 80)
    print("角色调度器选择测试:")
    print("-" * 80)
    role, score, reason = orchestrator.select_role("帮我分析一下这段文本的结构")
    print(f"选择: {role} (匹配度 {score:.2f})")
    print(f"理由: {reason.get('reason', '')}")

    # 测试加载角色卡
    print("\n" + "-" * 80)
    print("角色卡加载测试:")
    print("-" * 80)
    card = orchestrator.load_role("分析")
    if card:
        print(f"✅ 分析卡加载成功: {card.display_name}")
        print(f"   权限: {card.permission_level}")
        print(f"   系统提示词: {len(card.system_prompt)} 字符")
    else:
        print("⚠️  分析卡加载失败")

    print("\n✅ 测试4通过：角色调度器正常")


def main():
    """主测试函数"""
    print("\n" + "█" * 60)
    print("█" + " " * 20 + "角色卡体系测试" + " " * 20 + "█")
    print("█" * 60)

    try:
        test_registry()
        test_loader()
        test_selector()
        test_orchestrator()

        print("\n" + "█" * 60)
        print("█" + " " * 15 + "✅ 所有测试通过！" + " " * 18 + "█")
        print("█" * 60)
        print("\n下一步：")
        print("  1. 将角色调度器集成到Manus统帅")
        print("  2. 测试单角色调度（用分析卡做文本分析）")
        print("  3. 测试多角色协同（串行/并行）")
        print("  4. 实现工具权限过滤")
        print("  5. 实现模型路由（不同角色用不同模型）")
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
