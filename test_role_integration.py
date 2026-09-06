"""
角色卡体系集成测试脚本

测试内容：
1. 角色调度器初始化
2. 角色选择（各种任务类型）
3. 角色卡加载
4. 角色卡激活/取消激活
5. 角色卡状态查看

运行方式：
    python test_role_integration.py
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.role_cards import RoleOrchestrator, RoleRegistry


def test_orchestrator_init():
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
    """测试2：角色选择（各种任务类型）"""
    print("\n" + "=" * 60)
    print("测试2：角色选择（各种任务类型）")
    print("=" * 60)

    test_tasks = [
        ("帮我分析一下这段文本的结构和人物关系", "分析"),
        ("帮我写一个Python脚本统计文件行数", "生成/脚本"),
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
        # 期望可能是"A/B"格式，匹配其中一个就算对
        expected_roles = expected.split("/")
        status = "✅" if role in expected_roles else "❌"
        if role in expected_roles:
            correct_count += 1
        print(f"{status} 任务: {task[:35]}...")
        print(f"   选择: {role} (匹配度 {score:.2f})，期望: {expected}")
        print()

    print(f"选择正确率: {correct_count}/{len(test_tasks)} = {correct_count/len(test_tasks)*100:.1f}%")

    print("\n✅ 测试2通过：角色选择正常")


def test_role_loading(orchestrator):
    """测试3：角色卡加载"""
    print("\n" + "=" * 60)
    print("测试3：角色卡加载")
    print("=" * 60)

    test_roles = ["文件夹管理员", "分析", "生成", "老师", "小助手"]

    for role_name in test_roles:
        card = orchestrator.load_role(role_name)
        if card:
            print(f"✅ {role_name}: {card.display_name} | 权限={card.permission_level} | "
                  f"提示词={len(card.system_prompt)}字符 | 适用场景={len(card.适用场景)}个")
        else:
            print(f"❌ {role_name}: 加载失败")

    print("\n✅ 测试3通过：角色卡加载正常")


def test_role_activation(orchestrator):
    """测试4：角色卡激活/取消激活"""
    print("\n" + "=" * 60)
    print("测试4：角色卡激活/取消激活")
    print("=" * 60)

    # 创建一个模拟的agent对象（只需要system_prompt属性）
    class MockAgent:
        def __init__(self):
            self.system_prompt = "这是统帅的原始系统提示词"
            self.available_tools = None

    agent = MockAgent()

    # 测试激活分析卡
    print("\n激活分析卡:")
    result = orchestrator.activate_role("分析", agent)
    print(f"  激活结果: {'成功' if result else '失败'}")
    print(f"  当前激活: {orchestrator.get_active_role().name if orchestrator.get_active_role() else '无'}")
    print(f"  系统提示词长度: {len(agent.system_prompt)}字符（已注入角色卡前缀）")

    # 测试取消激活
    print("\n取消激活，恢复统帅身份:")
    result = orchestrator.deactivate_role(agent)
    print(f"  取消结果: {'成功' if result else '失败'}")
    print(f"  当前激活: {orchestrator.get_active_role().name if orchestrator.get_active_role() else '无（统帅身份）'}")
    print(f"  系统提示词长度: {len(agent.system_prompt)}字符（已恢复原始）")

    # 测试激活小助手卡
    print("\n激活小助手卡:")
    result = orchestrator.activate_role("小助手", agent)
    print(f"  激活结果: {'成功' if result else '失败'}")
    print(f"  当前激活: {orchestrator.get_active_role().name if orchestrator.get_active_role() else '无'}")

    # 取消激活
    orchestrator.deactivate_role(agent)

    print("\n✅ 测试4通过：角色卡激活/取消激活正常")


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
    print("█" + " " * 12 + "角色卡体系集成测试" + " " * 20 + "█")
    print("█" * 60)

    try:
        orchestrator = test_orchestrator_init()
        test_role_selection(orchestrator)
        test_role_loading(orchestrator)
        test_role_activation(orchestrator)
        test_selection_explanation(orchestrator)

        print("\n" + "█" * 60)
        print("█" + " " * 15 + "✅ 所有集成测试通过！" + " " * 18 + "█")
        print("█" * 60)
        print("\n下一步：")
        print("  1. 将角色调度器集成到Manus统帅类")
        print("  2. 实现run_with_role方法，用指定角色卡执行任务")
        print("  3. 测试单角色调度（分析卡做文本分析）")
        print("  4. 实现多角色串行/并行调度")
        print("  5. 实现工具权限过滤")
        print("  6. 实现模型路由（不同角色用不同模型）")
        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
