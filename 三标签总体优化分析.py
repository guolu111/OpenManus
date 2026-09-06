# -*- coding: utf-8 -*-
"""
三标签总体优化分析
调用三个标签（豆包/千问/智谱）分别分析总体优化的不同方面
"""
import json
import time
import urllib.request
import socket
from datetime import datetime

BRIDGE = "http://127.0.0.1:8010/v1/chat/completions"
OUTPUT_DIR = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus\docs\三标签总体优化分析"

# 确保输出目录存在
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 我们的整体架构现状
OUR_CONTEXT = """
【OpenManus统帅体系 - 整体架构现状】

四个阶段已完成：
1. Phase 1 基础框架：角色卡模块（role_card/role_registry/role_selector/role_orchestrator），9张角色卡，4级权限，五维评分选择器
2. Phase 2 角色卡深度集成：ManusWithRoles集成类，继承Manus，添加角色卡支持（角色选择/激活取消激活/run_with_role/工具权限过滤框架/模型路由框架）
3. Phase 3 多角色协同：MultiRoleOrchestrator调度器，串行/并行/混合三种模式，3个中层指挥官（内容创作军/数据分析军/系统运维军），世界书动态更新（通气公告/决议台账/执行历史）
4. Phase 4 飞书远程操控：FeishuHandler飞书消息处理器（消息解析/指令解析/消息发送/签名验证），TaskDashboard任务看板（优先级队列/状态追踪/重试机制/统计报告），LogMonitor日志监督器（实时扫描/错误模式识别/告警聚合/统计分析）

模块依赖关系：
- ManusWithRoles 继承 Manus，使用 RoleOrchestrator
- MultiRoleOrchestrator 使用 RoleOrchestrator，调度多个角色卡串行/并行执行
- FeishuHandler 接收消息 → Command解析 → 调用ManusWithRoles/MultiRoleOrchestrator → TaskDashboard监控状态 → LogMonitor监控日志

待优化问题：
架构层面：
1. 缺少统一的统帅入口（Commander类），ManusWithRoles和MultiRoleOrchestrator需要分别调用
2. 事件驱动机制缺失，目前是同步调用
3. 状态管理分散，任务状态在TaskDashboard，角色状态在RoleOrchestrator，日志状态在LogMonitor

功能层面：
1. 飞书长连接未真正实现，目前FeishuHandler只是模拟
2. 任务看板Web UI未实现，目前只有数据结构和API
3. 告警通知未实现，目前只是记录告警，没有发送通知
4. 多角色协同未端到端测试，目前只是模拟执行
5. API路由未实际实现，目前只是框架

工程层面：
1. 配置管理分散，API配置在config.toml，角色卡配置在txt文件
2. 错误处理不够完善
3. 缺少集成测试

经验包（已打包）：
- 运行记录：54个文件，282.7KB（三标签/四标签跑批经验、bug修复、验收记录）
- 蒸馏文档：6个文件，71.71KB（项目记忆蒸馏版、聊天记录蒸馏版）
- 世界书：3个文件，20.55KB（通用世界书v3.9、Command_Log）
- 小助手说明：3个文件，36.74KB
- 文档：1个文件，11.03KB

关键经验：
1. 实时日志驱动调试法：只看日志、根据日志改代码、不手动干预、让统帅自己跑、卡住才介入
2. 模型轮转的正确实现方式：不能放在[llm.model_rotation]下，必须单独解析
3. bridge与Chrome的关系：bridge使用launch_persistent_context启动自己的Chrome实例，不能与提问机器同时使用同一个profile
4. 长回复处理的关键：超时时间要足够长（至少180秒），找不到"重新回答"按钮时不能死循环
5. 超时设置的正确方式：必须同时设置socket.setdefaulttimeout(timeout)
"""

def call_bridge(model: str, prompt: str, timeout: int = 180) -> str:
    """调用bridge服务"""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096,
        }).encode("utf-8")

        req = urllib.request.Request(
            BRIDGE,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"【调用失败】{model}: {str(e)}"
    finally:
        socket.setdefaulttimeout(old_timeout)


def analyze_architecture():
    """标签1：豆包 - 架构分析"""
    print("\n" + "=" * 60)
    print("标签1（豆包）：架构分析")
    print("=" * 60)

    prompt = f"""你是一位资深的AI架构师，请分析OpenManus统帅体系的整体架构，提出架构优化建议。

{OUR_CONTEXT}

请重点分析：
1. 整体架构的优缺点（至少各3条）
2. 架构优化建议（至少5条，按优先级排序）
3. 推荐的目标架构（用文字描述架构图，包括各模块的职责和交互关系）
4. 统一统帅入口（Commander类）应该如何设计
5. 事件驱动机制应该如何实现
6. 统一状态管理应该如何设计

要求：
- 只做加法，不做减法（保留现有架构的优点）
- 优先考虑可扩展性和可维护性
- 结合我们的经验包（三标签跑批经验、实时日志驱动调试法等）
- 给出具体的实施建议，不要泛泛而谈
"""

    result = call_bridge("doubao", prompt)
    print(f"豆包回复长度: {len(result)} 字符")

    # 保存结果
    with open(os.path.join(OUTPUT_DIR, "01_豆包_架构分析.md"), "w", encoding="utf-8") as f:
        f.write(f"# 标签1（豆包）：架构分析\n\n")
        f.write(f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"> 标签：豆包（doubao）\n\n")
        f.write(result)

    return result


def analyze_function():
    """标签2：千问 - 功能优化"""
    print("\n" + "=" * 60)
    print("标签2（千问国际版）：功能优化")
    print("=" * 60)

    prompt = f"""你是一位资深的AI产品经理和全栈工程师，请分析OpenManus统帅体系的功能层面不足，提出功能优化建议。

{OUR_CONTEXT}

请重点分析：
1. 功能层面的不足（至少5条）
2. 功能优化建议（至少5条，按优先级排序）
3. 飞书长连接应该如何真正实现（参考飞书开放平台的WebSocket长连接模式）
4. 任务看板Web UI应该如何设计（参考AgentsRoom、Agent Board等成熟方案）
5. 告警通知应该如何实现（飞书消息/邮件/桌面通知）
6. 多角色协同如何进行端到端测试
7. API路由如何实际实现（根据角色和任务类型选择最合适的API模型）

要求：
- 只做加法，不做减法（保留现有功能的优点）
- 优先考虑用户体验和实用性
- 结合我们的经验包（三标签跑批经验、飞书机器人调试经验等）
- 给出具体的实现方案，包括技术选型和关键代码思路
"""

    result = call_bridge("qwen", prompt)
    print(f"千问回复长度: {len(result)} 字符")

    # 保存结果
    with open(os.path.join(OUTPUT_DIR, "02_千问_功能优化.md"), "w", encoding="utf-8") as f:
        f.write(f"# 标签2（千问国际版）：功能优化\n\n")
        f.write(f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"> 标签：千问国际版（qwen）\n\n")
        f.write(result)

    return result


def analyze_engineering():
    """标签3：智谱 - 工程优化和验证"""
    print("\n" + "=" * 60)
    print("标签3（智谱清言）：工程优化和验证")
    print("=" * 60)

    prompt = f"""你是一位资深的DevOps工程师和架构师，请分析OpenManus统帅体系的工程层面问题，验证架构优化和功能优化方案的可行性，提出工程优化建议。

{OUR_CONTEXT}

请重点分析：
1. 工程层面的问题（至少5条）
2. 工程优化建议（至少5条，按优先级排序）
3. 统一配置管理应该如何设计（ConfigManager类）
4. 错误处理和重试机制应该如何完善
5. 集成测试应该如何设计（端到端测试方案）
6. 验证架构优化方案的可行性（统一统帅入口、事件驱动、统一状态管理）
7. 验证功能优化方案的可行性（飞书长连接、任务看板Web UI、告警通知）
8. 实施风险和注意事项
9. 最终的优化实施计划（分阶段，每个阶段的目标和交付物）

要求：
- 只做加法，不做减法（保留现有工程的优点）
- 优先考虑稳定性和可维护性
- 结合我们的经验包（模型轮转bug修复、单实例锁、bridge与Chrome冲突等经验）
- 给出具体的工程实施方案，包括目录结构、关键类设计、测试方案
- 可行性验证要客观，指出可能的风险和挑战
"""

    result = call_bridge("glm", prompt)
    print(f"智谱回复长度: {len(result)} 字符")

    # 保存结果
    with open(os.path.join(OUTPUT_DIR, "03_智谱_工程优化和验证.md"), "w", encoding="utf-8") as f:
        f.write(f"# 标签3（智谱清言）：工程优化和验证\n\n")
        f.write(f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"> 标签：智谱清言（glm）\n\n")
        f.write(result)

    return result


def main():
    print("=" * 60)
    print("OpenManus统帅体系 - 三标签总体优化分析")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出目录: {OUTPUT_DIR}")

    start_time = time.time()

    # 并行调用三个标签（实际上bridge是串行的，但我们顺序调用）
    try:
        result1 = analyze_architecture()
    except Exception as e:
        result1 = f"【豆包调用异常】{str(e)}"
        print(result1)

    try:
        result2 = analyze_function()
    except Exception as e:
        result2 = f"【千问调用异常】{str(e)}"
        print(result2)

    try:
        result3 = analyze_engineering()
    except Exception as e:
        result3 = f"【智谱调用异常】{str(e)}"
        print(result3)

    # 生成汇总报告
    print("\n" + "=" * 60)
    print("生成汇总报告")
    print("=" * 60)

    summary = f"""# OpenManus统帅体系 - 三标签总体优化分析汇总报告

> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 分析标签：豆包（架构分析）、千问国际版（功能优化）、智谱清言（工程优化和验证）
> 总耗时：{time.time() - start_time:.1f} 秒

---

## 一、分析概述

本次三标签总体优化分析调用了三个网页版AI标签，分别从不同角度分析OpenManus统帅体系的优化方向：

| 标签 | 分析角度 | 回复长度 |
|------|---------|---------|
| 豆包（doubao） | 架构分析 | {len(result1)} 字符 |
| 千问国际版（qwen） | 功能优化 | {len(result2)} 字符 |
| 智谱清言（glm） | 工程优化和验证 | {len(result3)} 字符 |

---

## 二、详细分析报告

### 2.1 豆包：架构分析

详见：[01_豆包_架构分析.md](./01_豆包_架构分析.md)

### 2.2 千问：功能优化

详见：[02_千问_功能优化.md](./02_千问_功能优化.md)

### 2.3 智谱：工程优化和验证

详见：[03_智谱_工程优化和验证.md](./03_智谱_工程优化和验证.md)

---

## 三、后续步骤

1. 阅读三个标签的详细分析报告
2. 汇总三个标签的建议，形成最终的优化实施计划
3. 按照实施计划分阶段执行优化
4. 每个阶段完成后进行验证和总结
"""

    with open(os.path.join(OUTPUT_DIR, "00_汇总报告.md"), "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"\n汇总报告已生成: {os.path.join(OUTPUT_DIR, '00_汇总报告.md')}")
    print(f"总耗时: {time.time() - start_time:.1f} 秒")
    print("\n✅ 三标签总体优化分析完成！")


if __name__ == "__main__":
    main()
