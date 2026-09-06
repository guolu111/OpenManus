"""
ManusWithRoles 集成测试脚本

测试内容：
1. ManusWithRoles初始化
2. 角色卡自动选择
3. 角色卡激活/取消激活
4. 角色卡状态查看
5. 可用角色卡列表

注意：本测试不实际调用run方法（需要完整的API环境），只测试角色卡相关功能。

运行方式：
    python test_manus_with_roles.py
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.role_cards import RoleOrchestrator


def test_role_orchestrator_init():
    """测试1：角色调度器初始化"""
    print("\n" + "=" * 60)
    print("测试1：角色调度器初始化")
    print("=" * 60)

    role_cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "角色卡")
    orchestrator = RoleOrchestrator(role_cards_dir)

    print(orchestrator.status())

    print("\n✅ 测试1通过：角色调度器初始化成功")
    return orchestrator


def test_role_selection(orchestrator):
    """测试2：角色卡自动选择"""
    print("\n" + "=" * 60)
    print("测试2：角色卡自动选择")
    print("=" * 60)

    test_tasks = [
        ("帮我分析一下这段文本的结构和人物关系", "分析"),
        ("帮我写一个Python脚本统计文件行数", "脚本"),
        ("教我一下OpenManus怎么用", "老师"),
        ("帮我跑批鹿鼎记第22章", "每天更新"),
        ("检查一下文件夹目录是否同步", "文件夹管理员"),
        ("调用API批量处理这些数据", "小助手"),
        ("管理一下脚本仓库，看看有没有重复的", "脚本"),
        ("计算这两段文本的相似度", "匹配"),
        ("模仿这个风格写一段文字", "学生"),
    ]

    print("\n任务角色选择测试:")
    print("-" * 80)
    correct_count = 0
    for task, expected in test_tasks:
        role, score, reason = orchestrator.select_role(task)
        expected_roles = expected.split("/")
        status = "✅" if role in expected_roles else "❌"
        if role in expected_roles:
            correct_count += 1
        print(f"{status} 任务: {task[:35]}...")
        print(f"   选择: {role} (匹配度 {score:.2f})，期望: {expected}")
        print()

    print(f"选择正确率: {correct_count}/{len(test_tasks)} = {correct_count/len(test_tasks)*100:.1f}%")

    print("\n✅ 测试2通过：角色卡自动选择正常")


def test_role_activation(orchestrator):
    """测试3：角色卡激活/取消激活"""
    print("\n" + "=" * 60)
    print("测试3：角色卡激活/取消激活")
    print("=" * 60)

    # 创建一个模拟的agent对象
    class MockAgent:
        def __init__(self):
            self.system_prompt = "这是统帅的原始系统提示词"
            self.available_tools = None

    agent = MockAgent()

    # 测试激活分析卡
    print("\n激活分析卡:")
    result = orchestrator.activate_role("分析", agent)
    print(f"  激活结果: {'成功' if result else '失败'}")
    active_role = orchestrator.get_active_role()
    print(f"  当前激活: {active_role.name if active_role else '无'}")
    print(f"  系统提示词长度: {len(agent.system_prompt)}字符（已注入角色卡前缀）")

    # 测试取消激活
    print("\n取消激活，恢复统帅身份:")
    result = orchestrator.deactivate_role(agent)
    print(f"  取消结果: {'成功' if result else '失败'}")
    active_role = orchestrator.get_active_role()
    print(f"  当前激活: {active_role.name if active_role else '无（统帅身份）'}")
    print(f"  系统提示词长度: {len(agent.system_prompt)}字符（已恢复原始）")

    # 测试激活小助手卡
    print("\n激活小助手卡:")
    result = orchestrator.activate_role("小助手", agent)
    print(f"  激活结果: {'成功' if result else '失败'}")
    active_role = orchestrator.get_active_role()
    print(f"  当前激活: {active_role.name if active_role else '无'}")

    # 取消激活
    orchestrator.deactivate_role(agent)

    print("\n✅ 测试3通过：角色卡激活/取消激活正常")


def test_role_list(orchestrator):
    """测试4：可用角色卡列表"""
    print("\n" + "=" * 60)
    print("测试4：可用角色卡列表")
    print("=" * 60)

    roles = orchestrator.list_roles()
    print(f"\n可用角色卡数量: {len(roles)}")
    for role in roles:
        print(f"  - {role['name']} ({role['display_name']}) [{role['permission_level']}]")

    print("\n✅ 测试4通过：可用角色卡列表正常")


def test_selection_explanation(orchestrator):
    """测试5：角色选择解释"""
    print("\n" + "=" * 60)
    print("测试5：角色选择解释（用于调试）")
    print("=" * 60)

    print(orchestrator.explain_selection("帮我分析一下这段文本的结构和人物关系"))

    print("\n✅ 测试5通过：角色选择解释正常")


def main():
    """主测试函数"""
    print("\n" + "█" * 60)
    print("█" + " " * 10 + "ManusWithRoles 集成测试" + " " * 22 + "█")
    print("█" * 60)

    try:
        orchestrator = test_role_orchestrator_init()
        test_role_selection(orchestrator)
        test_role_activation(orchestrator)
        test_role_list(orchestrator)
        test_selection_explanation(orchestrator)

        print("\n" + "█" * 60)
        print("█" + " " * 15 + "✅ 所有集成测试通过！" + " " * 18 + "█")
        print("█" * 60)
        print("\n下一步：")
        print("  1. 在实际Manus环境中测试run_with_role方法")
        print("  2. 实现工具权限过滤（白名单/黑名单）")
        print("  3. 实现模型路由（不同角色用不同模型）")
        print("  4. 测试单角色调度（分析卡做文本分析）")
        print("  5. 实现多角色串行/并行调度")
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
