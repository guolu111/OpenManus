# -*- coding: utf-8 -*-
"""
三标签总体优化分析 - 重试千问和智谱
简化prompt，增加超时时间
"""
import json
import time
import urllib.request
import socket
import os
from datetime import datetime

BRIDGE = "http://127.0.0.1:8010/v1/chat/completions"
OUTPUT_DIR = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus\docs\三标签总体优化分析"

# 简化的整体架构现状（减少长度）
OUR_CONTEXT_SHORT = """
【OpenManus统帅体系 - 整体架构现状】

已完成四个阶段：
1. Phase1基础框架：角色卡模块（9张卡，4级权限，五维评分选择器）
2. Phase2角色卡深度集成：ManusWithRoles集成类（继承Manus，角色选择/激活/run_with_role）
3. Phase3多角色协同：MultiRoleOrchestrator（串行/并行/混合，3个中层指挥官，世界书动态更新）
4. Phase4飞书远程操控：FeishuHandler消息处理器 + TaskDashboard任务看板 + LogMonitor日志监督器

待优化问题：
架构：缺少统一统帅入口（Commander类）、事件驱动机制缺失、状态管理分散
功能：飞书长连接未实现、任务看板Web UI未实现、告警通知未实现、多角色协同未端到端测试
工程：配置管理分散、错误处理不完善、缺少集成测试

关键经验：
- 实时日志驱动调试法：只看日志、根据日志改代码、不手动干预
- 模型轮转必须单独解析，不能放在llm配置块下
- bridge独占Chrome profile，不能与其他浏览器实例冲突
- 长回复超时至少180秒，必须同时设置socket.setdefaulttimeout
"""

def call_bridge(model: str, prompt: str, timeout: int = 300) -> str:
    """调用bridge服务，增加超时时间"""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 8192,
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


def retry_qwen():
    """重试千问 - 功能优化"""
    print("\n" + "=" * 60)
    print("重试千问国际版：功能优化")
    print("=" * 60)

    prompt = f"""你是资深AI产品经理和全栈工程师，请分析OpenManus统帅体系的功能优化方向。

{OUR_CONTEXT_SHORT}

请分析：
1. 功能层面的不足（至少3条）
2. 功能优化建议（至少5条，按优先级P0/P1/P2排序）
3. 飞书长连接如何真正实现（WebSocket模式，不需要公网IP）
4. 任务看板Web UI如何设计（参考AgentsRoom拖拽即运行、Agent Board六列看板）
5. 告警通知如何实现（飞书消息/桌面通知）
6. 多角色协同如何端到端测试
7. API路由如何实现（根据角色和任务选模型）

要求：只做加法不做减法，给出具体实现方案，结合我们的经验包。"""

    result = call_bridge("qwen", prompt, timeout=300)
    print(f"千问回复长度: {len(result)} 字符")

    with open(os.path.join(OUTPUT_DIR, "02_千问_功能优化.md"), "w", encoding="utf-8") as f:
        f.write(f"# 标签2（千问国际版）：功能优化\n\n")
        f.write(f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"> 标签：千问国际版（qwen）\n")
        f.write(f"> 重试版本（简化prompt，增加超时）\n\n")
        f.write(result)

    return result


def retry_glm():
    """重试智谱 - 工程优化和验证"""
    print("\n" + "=" * 60)
    print("重试智谱清言：工程优化和验证")
    print("=" * 60)

    prompt = f"""你是资深DevOps工程师和架构师，请分析OpenManus统帅体系的工程优化方向，验证优化方案可行性。

{OUR_CONTEXT_SHORT}

请分析：
1. 工程层面的问题（至少3条）
2. 工程优化建议（至少5条，按优先级排序）
3. 统一配置管理ConfigHub如何设计（聚合toml/txt/世界书，支持环境区分）
4. 错误处理和重试机制如何完善
5. 集成测试如何设计（端到端测试方案）
6. 验证架构优化可行性：统一统帅入口Commander、事件总线EventBus、全局状态中心StateStore
7. 实施风险和注意事项
8. 最终优化实施计划（分阶段，每阶段目标和交付物）

要求：只做加法不做减法，给出具体工程方案，结合我们的经验包（模型轮转bug、单实例锁、bridge与Chrome冲突等）。"""

    result = call_bridge("glm", prompt, timeout=300)
    print(f"智谱回复长度: {len(result)} 字符")

    with open(os.path.join(OUTPUT_DIR, "03_智谱_工程优化和验证.md"), "w", encoding="utf-8") as f:
        f.write(f"# 标签3（智谱清言）：工程优化和验证\n\n")
        f.write(f"> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"> 标签：智谱清言（glm）\n")
        f.write(f"> 重试版本（简化prompt，增加超时）\n\n")
        f.write(result)

    return result


def main():
    print("=" * 60)
    print("三标签总体优化分析 - 重试千问和智谱")
    print("=" * 60)

    start_time = time.time()

    result2 = retry_qwen()
    result3 = retry_glm()

    # 更新汇总报告
    print("\n" + "=" * 60)
    print("更新汇总报告")
    print("=" * 60)

    summary = f"""# OpenManus统帅体系 - 三标签总体优化分析汇总报告

> 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 分析标签：豆包（架构分析）、千问国际版（功能优化）、智谱清言（工程优化和验证）
> 总耗时：{time.time() - start_time:.1f} 秒（重试版本）

---

## 一、分析概述

本次三标签总体优化分析调用了三个网页版AI标签，分别从不同角度分析OpenManus统帅体系的优化方向：

| 标签 | 分析角度 | 回复长度 |
|------|---------|---------|
| 豆包（doubao） | 架构分析 | 5970 字符 |
| 千问国际版（qwen） | 功能优化 | {len(result2)} 字符 |
| 智谱清言（glm） | 工程优化和验证 | {len(result3)} 字符 |

---

## 二、详细分析报告

### 2.1 豆包：架构分析

详见：[01_豆包_架构分析.md](./01_豆包_架构分析.md)

**核心建议**：
- P0：新增统一门面Commander统帅入口，封装两套执行器
- P0：引入轻量事件总线EventBus，改造为事件驱动架构
- P0：构建全局统一状态中心StateStore，消除状态孤岛
- P1：重构统一配置管理层ConfigHub
- P1：完善异步Worker任务队列，落地真实飞书长连接
- P2：增加标准化集成测试流水线 + 自动化经验包蒸馏

**目标架构**：五层架构（接入网关层 → 统一统帅门面层 → 调度编排层 → 执行内核层 → 持久化&观测底座）

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

    print(f"\n汇总报告已更新")
    print(f"总耗时: {time.time() - start_time:.1f} 秒")
    print("\n✅ 三标签总体优化分析重试完成！")


if __name__ == "__main__":
    main()
