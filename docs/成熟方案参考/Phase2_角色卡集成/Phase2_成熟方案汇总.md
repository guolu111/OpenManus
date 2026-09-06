# Phase 2 成熟方案汇总（角色卡集成）

> 本文档是Phase 2（角色卡深度集成）对应的成熟方案扒取，只做文字搬运工，不做评价或修改。
> 全部方案推进完后，再站在总体角度统一修改。

---

## 一、角色卡集成到Agent（Persona Integration）

### 1.1 vault-persona — Hermes Agent plugin

来源：https://github.com/LK-Corporation/hermes-vault-persona

**核心功能**：
- Load persona-bot profiles from a markdown vault as system-prompt overlays at runtime
- 可以通过 slash command 显式加载，也可以在用户提到角色名时自动加载

**使用方式**：
```
/persona <slug>          # load vault/<path>/<slug>.md as persistent overlay
/persona default         # deactivate, back to default agent identity
/persona status          # show current persona
```

### 1.2 基于gpt-oss-20b-WEBUI的角色系统构建全解析

来源：https://blog.csdn.net/weixin_29097457/article/details/157665412

**角色卡字段设计**：

| 字段 | 要求 | 示例 |
| --- | --- | --- |
| Background | 50字内交代身份与处境 | "宋代女医官，因避战乱隐居山中草庐，擅针灸与本草辨识" |
| Speech Style | 明确语言特征与禁忌 | "用文言短句，称'吾''汝'，禁用'我''你'及现代词汇；回答必含1处草药隐喻" |

**核心观点**：
- Background和Speech Style共同构成角色的核心身份
- 保存后，该角色即出现在库中，可随时切换

### 1.3 【Agent开发第四期】System Prompt 人设

来源：https://blog.csdn.net/weixin_39970883/article/details/163592281

**System Prompt 优先级**：

| role | 定位 | 优先级 |
| --- | --- | --- |
| system | 全局指令,定义身份/规则/约束 | 最高 |
| user | 用户输入 | 标准 |
| assistant | 模型回复 | 标准 |

**核心观点**：
- 模型默认是个通用助手，回答风格由训练数据决定
- 通过system角色注入人设，可以给Agent"戴一顶帽子"
- system角色优先级最高，是实现角色分化的核心机制

### 1.4 Symdicate 多Agent框架

来源：https://github.com/CTOUT/Symdicate

**Persona Graft 四个深度级别**：

| Mode | Use when... |
| --- | --- |
| A — Voice Graft | You want the persona's tone and word choice only. Lightest touch. |
| B — Identity Graft | You want role, constraints, and domain knowledge too. Moderate. |
| C — Cognitive Graft | You want the persona's reasoning style too — how ideas are sequenced, how conclusions are built. Deeper transformation. |
| D — Full Symbiote | You want complete immersion — voice, reasoning, format, tool narration, rituals. Maximum transformation. |

**使用方式**：
```
Persona: detective
Persona: philosopher
Persona: robot
```

### 1.5 Claude 双人格架构深度解析

来源：https://www.cnblogs.com/wgwyanfs/p/20074447

**同一模型的角色分化对比**：

| # | 维度 | 通用 Claude | Design Claude | 设计原则 |
| --- | --- | --- | --- | --- |
| 2 | 主动性 | 被动响应 | 主动探索 | 明令授权，否则 LLM 保守 |
| 3 | 提问 | 最多 1 问 | 最少 10 问 | 密度 = 任务模糊度函数 |
| 4 | 格式 | 禁 bullet | 无约束 | 按输出物本质评判 |
| 5 | 变体 | 无 | 强制 3+ | 创造=搜索，不是优化 |

**核心观点**：
- 通过System Prompt可以实现同一模型的角色分化
- 不同角色有不同的主动性、提问密度、格式要求、变体要求
- 角色分化的关键是"明令授权"，否则LLM会保守

### 1.6 【LangChain】System Prompt工程化实践

来源：https://juejin.cn/post/7621773386785423400

**多角色Prompt管理器设计**：
```python
"""多角色Prompt管理器"""
def __init__(self):
    self.roles: Dict[AgentRole, RoleProfile] = {
        AgentRole.ANALYZER: RoleProfile(
            name="数据分析师",
            system_prompt="""你是数据分析师Dr.Data。你的特点是：
            - 只说确定的事实，不确定时明确标注"推测"
            - 使用数据支撑观点，提供统计显著性
            - 回答结构：结论->依据->置信...
            """
        ),
        # ... 其他角色
    }
```

**核心观点**：
- 多角色Prompt管理器是工程化实践的核心
- 每个角色有独立的name和system_prompt
- 通过Dict管理，便于扩展和切换

### 1.7 Agent Identity & Persona Stability

来源：https://www.max-gherman.dev/design/anatomy-of-ai-agent/agent-identity-and-persona-stability/

**两种角色切换方式**：

**Hard Persona Switching**：
- 每个角色有独立的session和context
- 优点：完全隔离，不会互相污染
- 缺点：切换后新角色没有之前的记忆，需要handoff summary

**Soft Persona Switching**：
- 在同一个session内切换角色
- 通过注入persona transition directive（系统消息）来重置行为预期
- 优点：成本低，不需要独立session
- 缺点：可能有上下文残留

**核心代码**：
```python
def build_persona_transition(...):
    # 构建角色切换指令
    pass
```

### 1.8 Personas plugin — canonical persona store

来源：https://github.com/Interstellar-code/hermes-agent/issues/143

**核心功能**：
- Migrate the 16 curated persona templates out of the SwitchUI frontend into the plugin as the single source of truth
- Provide runtime tools (`persona_list`, `persona_get`, `persona_apply`) so any agent on any platform (CLI, Telegram, Discord, gateway) can invoke personas on demand

**核心观点**：
- 角色卡应该作为single source of truth，统一管理
- 提供运行时工具，让任何平台的agent都可以按需调用角色卡
- 角色卡模板应该从前端迁移到插件中，作为统一数据源

---

## 二、工具权限过滤（Tool Permission Filtering）

### 2.1 从 Demo 到生产：AI Agent 工具调用的安全控制

来源：https://blog.csdn.net/u014158743/article/details/161489584

**RBAC（基于角色的访问控制）是基石**：
- 在企业里，绝不会让所有的 Agent 拥有调用所有工具的权限
- 这就好比公司里，实习生不能随便进 CEO 办公室，财务也不能随意修改代码库

**场景举例**：
- 医生 Agent：只能查询 LIS（实验室信息系统），不能查看财务数据
- 客服 Agent：只能查询订单状态，绝对不能执行删除操作

### 2.2 OpenClaw SubAgent 三层安全约束

来源：https://blog.csdn.net/Rainsirius/article/details/162834978

**三大核心防护体系**：
1. **子代理黑白名单权限收缩**
2. **递归委派阻断**（防无限循环/资源雪崩）
3. **全链路上下文/数据隔离**（防污染）

**核心观点**：
- 子代理的权限必须比父代理更严格，不能越权
- 递归委派必须阻断，防止无限循环和资源雪崩
- 上下文和数据必须隔离，防止不同子代理之间互相污染

### 2.3 Tool调用白名单：一场「门没锁」引发的安全事故

来源：https://www.cnblogs.com/aimagician/p/20134953

**白名单核心哲学**：
- Tool白名单是Agent安全设计的核心机制
- 其核心不是「列出哪些工具能用」，而是「默认拒绝所有未注册工具」
- 从注册-校验-拒绝三阶段讲清原理

**白名单 vs 黑名单的安全哲学差异**：
- 白名单：默认拒绝，只允许明确列出的工具（更安全）
- 黑名单：默认允许，只拒绝明确列出的工具（更宽松）

**核心观点**：
- 生产环境必须用白名单，不能用黑名单
- 白名单的核心是"默认拒绝"，而不是"列出能用的"

### 2.4 agent-rbac 项目

来源：https://github.com/d-wwei/agent-rbac

**核心功能**：
- Role-based access control and memory isolation framework for multi-user AI agents
- 包含：host contract types、file-backed audit storage、adaptive policy copilot

**设计文档**：
- Design Index
- Product Architecture
- Policy Model Design
- Host Contract & Adapter Architecture
- Audit & Explainability
- Adaptive Policy Copilot
- Data, Storage & Privacy
- Implementation Roadmap

### 2.5 AgentScope Java 工具分组

来源：https://developer.aliyun.com/article/1743830

**工具过滤配置**：
```json
{
    "tools": [
        {"name": "query_order", "class": "demo.tools.QueryTool"},
        {"name": "refund_order", "class": "demo.tools.RefundTool"}
    ],
    "toolFilter": {
        "allow": ["query_order", "query_logistics"],
        "deny":  ["refund_order"]
    }
}
```

**行为**：
- `allow` 白名单模式：只放行名字精确匹配的工具；其他一律不可见
- `deny` 黑名单模式：拒绝名字精确匹配的工具；其他都可见

### 2.6 MCP Access Control: How to Enforce Least Privilege

来源：https://appsentinels.ai/blog/mcp-access-control-how-to-enforce-least-privilege-across-ai-agent-tool-chains/

**Tool Allowlisting**：
- Tool allowlisting applies a default-deny posture to MCP tool access
- instead of granting an agent access to every tool an MCP server exposes, you define an explicit, narrowly-scoped list of permitted tools for each agent identity or role
- Any tool invocation not on the list is blocked at the gateway layer before it reaches the server

**核心观点**：
- Effective least privilege for MCP requires a layered stack of complementary controls, none of which is sufficient alone
- 最小权限原则需要多层控制，单一控制不够

### 2.7 三层越权场景

来源：https://www.iesdouyin.com/share/video/7679816409261690154

**越权的范围和失效场景**：
1. **工具级越权**：agent直接调用了自身角色无权访问的工具接口
2. **参数级越权**：工具在白名单内，但传入的操作参数超出权限范围（比如查询他人数据、修改高权限配置）
3. **操作级越权**：工具和参数都合法，但组合起来形成了越权操作

**核心观点**：
- 越权不是简单调用了不在白名单的工具
- 任何形式的超出权限范围的操作都能被拦截
- 必须吃透三层核心逻辑才能通过面试

### 2.8 kimi-code 权限与安全：三层审批模型

来源：https://cloud.tencent.cn/developer/article/2722553?policyId=1004

**白名单/黑名单机制**：
- 路径权限使用 glob 模式匹配，基于 minimatch 库实现
- 双重检查：路径先过白名单，再过黑名单。只有在白名单中且不在黑名单中的路径才被允许
- 操作隔离：读取、写入、执行分别有独立的权限控制

**配置示例**：
```json
{
    "readAllow": ["./**"]
}
```

### 2.9 AI Agent时代，传统权限模型为什么失效?

来源：https://juejin.cn/post/7626197125011111946

**任务级权限新模型**：
- 传统模型：权限 = 这个人（角色）能做什么
- 新模型：权限 = 这个任务需要什么

**任务级权限意味着**：
- 同一个Agent，处理不同任务时拥有完全不同的权限集合
- 权限随任务启动而颁发，随任务结束而撤销——不是长期持有
- 权限的边界由任务的声明决定，而不是由角色的配置决定

**架构设计核心原则**：
1. 以任务为中心，而不是以角色为中心
2. 权限动态颁发和撤销
3. 最小权限原则
4. 审计和可解释性

### 2.10 OpenClaw 工具权限机制：从沙箱到 RBAC

来源：https://blog.csdn.net/m0_67391870/article/details/161851930

**RBAC 角色模型**：
通过定义不同角色，实现用户与 Agent 权限的映射：
- `admin`：管理员角色，拥有所有工具的管理与使用权限
- `developer`：开发者角色，拥有代码相关工具的权限
- `viewer`：查看者角色，只有只读工具的权限

**核心观点**：
- 企业级部署中，OpenClaw 支持 RBAC（基于角色的访问控制）和操作审计
- 实现多用户、多 Agent 的权限管理
- 从沙箱到 RBAC 是全链路安全设计的演进

---

## 三、模型路由（Model Routing per Role）

### 3.1 per-role model routing via --models, config, and adapter options

来源：https://github.com/aguil/agents/pull/188

**核心功能**：
- `models` map (`roleId → model`) on the opencode/claude/cursor adapter options
- resolved by a shared `resolveModelForRole` helper in each command builder
- a role's entry wins, other roles fall back to the global `model`, then to the default

**核心观点**：
- 每个角色可以配置独立的模型
- 角色的配置优先于全局配置
- 没有配置的角色回退到全局模型，再回退到默认模型

### 3.2 RFC: Intelligent Model Routing — Tier-Based Dispatch

来源：https://github.com/steveyegge/gastown/discussions/2531

**分层模型配置**：
```yaml
medium:
    - provider: anthropic
      model: claude-sonnet-4-6
    - provider: openai
      model: gpt-4.1
large:
    - provider: anthropic
      model: claude-opus-4-6

role_defaults:
  mayor: large
  crew: large
  polecat: medium
  witness: small
  deacon: small
  dogs: small
```

**核心观点**：
- 按层级（small/medium/large）配置模型
- 每个角色有默认的层级配置
- 不同角色用不同层级的模型，实现成本和效果的平衡

### 3.3 多模型多 Agent 混合部署系统设计

来源：https://blog.csdn.net/sinat_28461591/article/details/147402865

**Task Router（任务路由器）核心职责**：
1. 识别任务类型（文本生成 / 结构化 JSON / 工具调用 / 多模态）
2. 识别 Agent 角色（Executor？Planner？Critic？）
3. 识别任务紧急程度 / token 长度 / response SLA 要求

**代码示例（FastAPI）**：
```python
@app.post("/agent/request")
def route(request: AgentRequest):
    # 提取任务特征
    # 转发给策略中心
    # 选择合适的模型
    pass
```

### 3.4 MasRouter: Learning to Route LLMs for Multi-Agent Systems

来源：https://arxiv.org/pdf/2502.11133

**核心观点**：
- Each LLMs have its own strengths and drawbacks
- The goal of LLM routing is to leverage their unique capabilities
- For example, for mathematical problems, we would opt for an LLM that is particularly proficient in mathematics or one that has been specifically fine-tuned
- Assigning an LLM to a specific agent primarily depends on the task's domain and difficulty, as well as their corresponding role

**Routing 建模**：
```
P(M1, M2, ..., Mk | Q, T, R)
```
- Q: 任务/问题
- T: 任务类型
- R: 角色
- 这是一个多变量联合分布，作者采用 Multinomial 建模

### 3.5 Use model router with Foundry agents

来源：https://learn.microsoft.com/en-gb/AZURE/foundry/openai/how-to/model-router-agents

**Tailor model subsets per agent**：
- You can create multiple model router deployments, each with its own routing mode and model subset
- Assign each agent the deployment that matches its workload
- This pattern is useful when your agents have distinct cost, compliance, or capability requirements

**配置示例**：

| Deployment name | Routing mode | Model subset | Agent use case |
| --- | --- | --- | --- |
| router-frontier | Quality | gpt-5.6-sol, gpt-5, o4-mini | Research agent — complex reasoning and synthesis |
| router-balanced | Balanced | gpt-5-mini, gpt-4.1, gpt-4.1-mini | Assistant général — conversations de complexité mixte |

### 3.6 Beyond Tier Labels: Role- and Deployment-Dependent Model Substitution

来源：https://arxiv.org/pdf/2608.09155

**核心观点**：
- All policies share the same solve–merge–verify runner, task instances, retry logic, and accounting code within each ladder–task–scale–seed condition
- Their differences arise from allocation rather than execution
- Fixed policies assign one tier globally
- graph-local combines role with graph position
- graph-only isolates structural features

**核心结论**：
- 模型替换不能只看层级标签
- 必须结合角色和部署位置来决定
- 不同的角色在不同的图位置应该用不同的模型

### 3.7 NVIDIA NeMo Switchyard

来源：https://developer.nvidia.com/blog/route-ai-agent-workloads-across-models-with-nvidia-nemo-switchyard?nvid=nv-csfg-468349

**核心功能**：
- AI agents benefit from routing tasks across specialized and frontier models rather than relying on a single model for every step
- NVIDIA NeMo Switchyard provides an open-source orchestration layer that separates routing logic from provider endpoints
- Enabling model-neutral routing decisions

**支持的路由器**：
- tuning-free routers: LLM classifier, stage router, escalation router
- tunable prefill routers: learn from workload data to predict model success likelihood

**核心观点**：
- 将路由逻辑与提供者端点分离
- 实现模型中立的路由决策
- 支持无调优路由器和可学习路由器

---

## 四、单角色调度（Single Role Orchestration）

### 4.1 Orchestrator-Worker 模式

来源：https://codefully.ai/blog/multi-agent-orchestration

**核心观点**：
- The most widely deployed pattern in production systems
- A central orchestrator receives the top-level task, decomposes it into sub-tasks, and delegates each to a specialised worker agent
- Worker agents execute and return results to the orchestrator, which synthesises them into a final output and handles any failure or retry logic
- This pattern excels at complex, multi-domain workflows where a coherent final output must be assembled from diverse inputs

**单角色调度的核心流程**：
1. Orchestrator接收任务
2. 分解为子任务
3. 委派给专门的Worker Agent
4. Worker执行并返回结果
5. Orchestrator汇总成最终输出
6. 处理失败和重试逻辑

### 4.2 Selector 调度策略

来源：https://blog.csdn.net/sjsi13/article/details/164231010

**调度策略对比**：

| 策略 | 说明 | 适用场景 |
| --- | --- | --- |
| RoundRobin | 轮流发言 | 简单循环、人人都能发言 |
| **Selector** | **由 LLM 选择最合适的下一个发言者** | **角色分工明确，需要动态调度** |
| Mention | 由当前发言者显式 @ 下一位 | 需要精确控制流程 |
| Random | 随机选择 | 探索式对话、创意生成 |

**核心结论**：
- Selector 策略最适合角色分工明确的场景
- 由LLM根据当前上下文选择最合适的角色
- 动态调度，比固定流程更灵活

### 4.3 SpecialistAgent 设计

来源：https://m.nowcoder.com/discuss/916430150495895552

**核心设计**：
- 给单体 Agent、子 Agent、主 Agent 一个统一的壳子
- `SpecialistAgent`，给 `ReActAgent` 套上一份领域人设和一个身份，就成了一个有明确领域身份的子 Agent
- 它自己没有循环，循环全借 `ReActAgent` 的

**核心观点**：
- 子Agent不需要自己的循环，复用主Agent的循环即可
- 通过套上领域人设和身份来实现角色分化
- 统一的壳子便于管理和扩展

---

## 五、参考资源汇总

### 角色卡集成到Agent
1. https://github.com/LK-Corporation/hermes-vault-persona
2. https://blog.csdn.net/weixin_29097457/article/details/157665412
3. https://blog.csdn.net/weixin_39970883/article/details/163592281
4. https://github.com/CTOUT/Symdicate
5. https://www.cnblogs.com/wgwyanfs/p/20074447
6. https://juejin.cn/post/7621773386785423400
7. https://www.max-gherman.dev/design/anatomy-of-ai-agent/agent-identity-and-persona-stability/
8. https://github.com/Interstellar-code/hermes-agent/issues/143

### 工具权限过滤
1. https://blog.csdn.net/u014158743/article/details/161489584
2. https://blog.csdn.net/Rainsirius/article/details/162834978
3. https://www.cnblogs.com/aimagician/p/20134953
4. https://github.com/d-wwei/agent-rbac
5. https://developer.aliyun.com/article/1743830
6. https://appsentinels.ai/blog/mcp-access-control-how-to-enforce-least-privilege-across-ai-agent-tool-chains/
7. https://www.iesdouyin.com/share/video/7679816409261690154
8. https://cloud.tencent.cn/developer/article/2722553?policyId=1004
9. https://juejin.cn/post/7626197125011111946
10. https://blog.csdn.net/m0_67391870/article/details/161851930

### 模型路由
1. https://github.com/aguil/agents/pull/188
2. https://github.com/steveyegge/gastown/discussions/2531
3. https://blog.csdn.net/sinat_28461591/article/details/147402865
4. https://arxiv.org/pdf/2502.11133
5. https://learn.microsoft.com/en-gb/AZURE/foundry/openai/how-to/model-router-agents
6. https://arxiv.org/pdf/2608.09155
7. https://developer.nvidia.com/blog/route-ai-agent-workloads-across-models-with-nvidia-nemo-switchyard

### 单角色调度
1. https://codefully.ai/blog/multi-agent-orchestration
2. https://blog.csdn.net/sjsi13/article/details/164231010
3. https://m.nowcoder.com/discuss/916430150495895552

---

> **说明**：本文档只做文字搬运工，不做评价或修改。全部方案推进完后，再站在总体角度统一修改。
