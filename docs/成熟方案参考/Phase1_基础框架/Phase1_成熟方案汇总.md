# Phase 1 成熟方案汇总（基础框架）

> 本文档是Phase 1（基础框架）对应的成熟方案扒取，只做文字搬运工，不做评价或修改。
> 全部方案推进完后，再站在总体角度统一修改。

---

## 一、多Agent角色卡体系（Persona-based Multi-Agent）

### 1.1 Frontier: Role Design & Multi-Agent Specialization

来源：https://github.com/dformoso/positronic/blob/main/docs/agentic-patterns/02_role_design_detailed.md

**核心观点**：
- Multi-agent role decomposition works when roles are non-overlapping.
- Multi-agent systems get a bad reputation in 2026 ("just use a single agent with tools"). The literature is more nuanced. Multi-agent wins when:
  - Roles are non-overlapping — clean responsibility boundaries.
  - Communication is structured — artifacts/protocols, not free-form chat.
  - The task naturally decomposes — coding (PM/Eng/QA), research (search/synthesize/cite).

### 1.2 Building Persona-Based Agents On Demand

来源：https://arxiv.org/pdf/2604.27882v1

**核心观点**：
- A persona is a structured specification that defines the agent's role, the domain competencies it should exhibit, the communication style it should adopt when contributing to the final response, and what capabilities it owns.
- AgentFactory: each synthesized persona is used to initialize one agent instance.
- This process is aware of already existing agents and roles, allowing for precise persona development and avoiding duplicates.

### 1.3 Multiple Personas 沉浸式AI角色扮演引擎

来源：https://hub.cocoloop.cn/skills/243

**核心观点**：
- Multiple Personas 是一个AI子代理人格管理系统，允许用户创建、管理和与具有独特个性的AI角色进行对话。
- 核心工作流程分为三个层次：用户可以通过创建`profiles/<name>/`目录结构，分别编写：
  - `SOUL.md`（身份与价值观）
  - 其他配置文件

### 1.4 OpenClaw 多 Agent 协作完整指南

来源：https://blog.csdn.net/weixin_51035135/article/details/158659469

**核心观点**：
- OpenClaw 支持在同一 workspace 中运行多个独立的 AI 代理（Agent），每个 Agent 可以有：
  - 不同的 人格（Soul）
  - 不同的 身份（Identity）
  - 不同的 模型、温度、权限
  - 不同的 技能 与 记忆
- 这些 Agent 可以通过 会话（Session） 相互通信，形成团队协作。

### 1.5 Collective Persona Operations

来源：https://github.com/a-organvm/collective-persona-operations

**核心组件**：

| Component | Responsibility | Input | Output |
| --- | --- | --- | --- |
| Context Detector | Determine which persona(s) apply | Org, repo, doc type, audience | Active persona ID(s) |
| Composition Engine | Merge multiple personas for cross-organ contexts | Set of persona IDs + dominance rules | Composite persona spec |
| State Machine | Enforce legal transitions and hysteresis | Current state + context change event | New state or rejection |
| Validator | Check output against declared persona | Document + persona spec | Pass/fail + diagnostics |

### 1.6 多 Agent 框架深度剖析：CrewAI 角色分工、AutoGen 多轮对话

来源：https://blog.csdn.net/sjsi13/article/details/164231010

**调度策略**：

| 策略 | 说明 | 适用场景 |
| --- | --- | --- |
| RoundRobin | 轮流发言 | 简单循环、人人都能发言 |
| Selector | 由 LLM 选择最合适的下一个发言者 | 角色分工明确，需要动态调度 |
| Mention | 由当前发言者显式 @ 下一位 | 需要精确控制流程 |
| Random | 随机选择 | 探索式对话、创意生成 |

**核心结论**：Selector 策略最适合角色分工明确的场景。

### 1.7 Symdicate 多Agent框架

来源：https://github.com/CTOUT/Symdicate

**核心观点**：
- A multi-agent framework for GitHub Copilot (with multi-engine skill support for Google Gemini) built around composable, symbiotic AI agents.
- Each agent in Symdicate has a well-defined cognitive identity — purpose, reasoning style, toolset, behavioural rules, and communication style — making them predictable building blocks that can be targeted, layered, and fused.
- NeuroGraft: Grafts a persona onto any Copilot agent at one of four cognitive depths.

### 1.8 主从式多智能体：手写Supervisor与子Agent团队

来源：https://m.nowcoder.com/discuss/916430150495895552

**核心观点**：
- 给单体 Agent、子 Agent、主 Agent 一个统一的壳子。
- `SpecialistAgent`，给 `ReActAgent` 套上一份领域人设和一个身份，就成了一个有明确领域身份的子 Agent——它自己没有循环，循环全借 `ReActAgent` 的。

---

## 二、Hierarchical Multi-Agent架构（层级制多智能体）

### 2.1 Autonoma: A Hierarchical Multi-Agent Framework

来源：https://arxiv.org/pdf/2603.19270

**核心架构**：
- Hierarchical agent architecture, comprising a Coordinator, Planner, Supervisor, and a suite of specialized Worker agents.
- Translating natural language prompts into structured, executable workflows.
- The Supervisor agent oversees the Worker agents.

### 2.2 一文讲清：7种常见的多Agent协作架构模式

来源：https://juejin.cn/post/7644744610916335657

**模式二：Hierarchical（层级制）**
- 层级制架构可以直接理解为Orchestrator-Worker模式的升级版本。
- 当项目内的Agent数量超过10个，单层中央调度模式会出现性能瓶颈，这时就需要引入分层架构。
- 整体架构呈树状结构：顶层的Orchestrator只对接数个中层管理者Manager，再由各个Manager分别管辖专属的Worker执行组。
- 顶层调度端不会直接对接底层执行Agent，全程只和中层Manager通信。

### 2.3 Agent 的任务编排：从 System Prompt 到 Hierarchical Multi-Agent

来源：https://juejin.cn/post/7668547554775367720

**Orchestrator-Worker：并行专业分工**
- 当任务的规模超出一个 Agent 的注意力范围时，Plan-and-Execute 的静态图就撑不住了。
- 你需要的是一个"导演+演员"模型——一个统筹者（Orchestrator）把大问题拆成独立子任务，派给一群专业子 Agent（Workers），各自完成后再汇总。
- Anthropic 在 2025 年 6 月公开了他们内部的多Agent架构。

### 2.4 hierarchical-agents 项目

来源：https://github.com/GieshBuilds/hierarchical-agents

**核心观点**：
- Turn isolated Hermes agent profiles into a coordinated organization with hierarchy, messaging, delegation, and shared memory.
- This project is a coordination layer that runs on top of Hermes — it does not replace it.
- Hermes gives each agent its own profile — an isolated session with its own identity, tools, and state. But profiles can't talk to each other directly.

### 2.5 多智能体(Multi-Agent)架构深度拆解

来源：https://www.woshipm.com/ai/1546717.html

**3.2 层级式（Hierarchical）**
- 核心逻辑：树形分层结构，按「manager → sub-manager → worker」的层级逐级拆解任务。
- 高层负责战略决策，中层负责任务拆分，底层负责执行，实现多层级管控。
- 核心特点：适合大型复杂项目、跨部门协作、企业级工作流。
- 典型落地：Anthropic Claude Subagent、LangGraph 原生支持。

### 2.6 AI Agent设计模式 Day 14: Hierarchical模式

来源：https://blog.csdn.net/qq_qingtian/article/details/155059280

**架构设计**：
Hierarchical模式的系统架构呈金字塔形，包含三层核心组件：

- **顶层：Manager Agent**
  - 输入：用户自然语言请求
  - 输出：结构化任务计划（JSON格式）
  - 能力：战略思维、优先级排序、风险评估

- **中层：Coordinator Agents（按领域划分）**
  - 示例：ResearchCoordinator、WritingCoordinator、DataAnalysisCoordinator
  - 输入：高层任务指令
  - 输出：原子操作序列
  - 能力：领域知识、工具理解、依赖管理

- **底层：Worker Agents**
  - 输入：原子操作
  - 输出：执行结果
  - 能力：具体工具调用、专业领域执行

### 2.7 Agent Orchestration Patterns: Swarm vs Mesh vs Hierarchical vs Pipeline

来源：https://gurusup.com/blog/agent-orchestration-patterns

**Hierarchical Pattern**
- The hierarchical pattern organizes agents into a tree structure with multiple levels of delegation.
- A top-level manager agent delegates to mid-level supervisor agents, who in turn delegate to leaf-level worker agents.
- Each level adds a layer of abstraction: the top level reasons about strategy, mid levels reason about tactics, and leaf-level agents execute specific actions.
- This mirrors how large engineering organizations operate. A VP sets product direction, engineering managers translate it into sprint plans, and individual engineers execute.

### 2.8 Multi-Agent Orchestration: Architecture, Types & Use Cases

来源：https://codefully.ai/blog/multi-agent-orchestration

**Hierarchical (Orchestrator-Worker)**
- The most widely deployed pattern in production systems.
- A central orchestrator receives the top-level task, decomposes it into sub-tasks, and delegates each to a specialised worker agent.
- Worker agents execute and return results to the orchestrator, which synthesises them into a final output and handles any failure or retry logic.
- This pattern excels at complex, multi-domain workflows where a coherent final output must be assembled from diverse inputs.

---

## 三、API路由和模型分配（Model Routing）

### 3.1 【LLM Gateway】生产级部署实战：LiteLLM + 多模型路由

来源：https://blog.csdn.net/qq_73472828/article/details/160699220

**核心观点**：
- 80% 的场景（简单问答、信息提取、格式转换）用低成本模型就能完美完成，成本只有顶级模型的 1/10。
- 通过 Gateway 配置，实现核心场景保效果，非核心场景降成本：

```yaml
router_settings:
routing_rules:
# 核心场景：Agent规划、代码生成、复杂推理，用顶级模型
- rule_name: "core-business"
condition:
query_contains: ["..."]
```

### 3.2 LLM 模型路由：业内实现方案调研

来源：https://xie.infoq.cn/article/ded5f03c6294454772a0e0f1c

**路由类型分类**：

| 类型 | 说明 | 代表项目 |
| --- | --- | --- |
| 基础设施路由 | 在同一模型或等价部署之间做负载均衡 | Azure Model Router、RouteLLM、RoRF |
| 语义/任务路由 | 先识别领域、动作、复杂度、工具需求，再按配置把任务交给指定模型 | Arch-Router、vLLM Semantic Router |
| 级联路由 | 先调用便宜模型，根据答案置信度决定是否升级到强模型 | FrugalGPT、AutoMix |

### 3.3 Keeping Up with the Models: Online Deployment and Routing of LLMs at Scale

来源：https://www.arxiv.org/pdf/2506.17254

**核心观点**：
- We cast the reality as an online decision problem that couples stage-wise deployment, made at fixed maintenance windows, with per-query routing among the models kept live.
- We introduce StageRoute, a hierarchical algorithm that:
  1. optimistically selects up to Mmax models for the next stage using reward upper-confidence and cost lower-confidence bounds
  2. solves a budget-constrained bandit subproblem to route each incoming query.

### 3.4 nexus-llm-router 项目

来源：https://github.com/Francis1998/nexus-llm-router

**核心功能**：
- Intelligent multi-LLM routing middleware with task-aware model selection, cost optimization, fallback safety, and a drop-in OpenAI-compatible API.
- Nexus gives the application one stable OpenAI-compatible API while moving model choice, fallback, budget, audit, and routing rationale into infra-owned middleware.

### 3.5 多模型 API 统一管理的方案对比：One API vs NewAPI vs LiteLLM

来源：https://blog.csdn.net/lotusxyhf/article/details/162575549

**方案对比**：

| 维度 | One API | NewAPI | LiteLLM |
| --- | --- | --- | --- |
| 管理后台 | ✅ 基础 | ✅ 增强版 | ✅ 企业级（SaaS 版） |
| 配额管理 | 按用户/分组 | 按用户/分组/模型 | 按 Key/用户/团队 |
| 负载均衡 | 权重轮询 | 权重轮询 + 聚合路由 | 多策略（轮询/最低延迟/智能路由） |
| Fallback | 手动配置 | 自动切换 | 自动 + 配置化 |

### 3.6 AI API网关架构设计：构建多模型统一路由与自动故障转移

来源：https://www.cnblogs.com/wgwyanfs/p/21285018

**路由选择算法**：
路由层根据以下因素决定使用哪个provider：

- **优先级（Priority）**：每条路由有一个`priority` 值，数字越小越优先。同一个标准模型可挂多条路由，形成有序的fallback链。
- **能力过滤（Capability Filter）**：如果请求需要特定能力（如视觉、函数调用），自动过滤不支持该能力的路由。
- **成本优先（Cost-based）**：在能力满足的前提下，优先选择成本最低的路由。

```yaml
cost:
  input: 3.00          # $/MTok，成本价
  output: 15.00
```

### 3.7 Best 7 AI Gateways for Multi-Model Routing in 2026

来源：https://futureagi.com/blog/best-ai-gateways-model-routing/

| # | Platform | Best for |
| --- | --- | --- |
| 1 | Future AGI Agent Command Center | 15 routing and reliability strategies plus 18+ guardrails plus OTel-native cost metrics in one Apache 2.0 Go binary |
| 2 | Portkey | Conditional metadata routing with 9 operators plus 4-tier budget hierarchy |
| 3 | LiteLLM | Python-first teams |

### 3.8 LLM Router - Intelligent Multi-Provider AI System

来源：https://github.com/large-scale-ai-systems/multi-llm-router

**核心功能**：
- A sophisticated multi-LLM routing system that uses Control Theory (PID Controllers) and Vector Database evaluation to dynamically allocate requests across multiple Language Models based on real-time performance metrics, cost efficiency, and quality assessment.
- Multi-Provider Support: Pluggable any LLM including frontier OpenAI (GPT-4o), Anthropic Claude, Google Gemini, etc.

---

## 四、世界书/共享信息空间（Blackboard Pattern）

### 4.1 黑板系统 (Blackboard System) 详解

来源：https://github.com/ForceInjection/all-agentic-architectures/blob/main/07_blackboard_zh.ipynb

**核心观点**：
- 黑板系统 (Blackboard System) 是一种强大且高度灵活的模式，用于协调多个专家智能体。
- 这种架构模仿了一组人类专家围绕物理黑板协同解决复杂问题的理念。
- 黑板系统不再是僵化的、预定义的智能体交接序列，而是具有一个中央共享数据存储（即"黑板"），智能体可以在其中读取问题的当前状态并写入它们的贡献。
- 一个动态的控制器根据黑板的当前状态决定下一步哪个智能体应该行动。

### 4.2 Exploring Advanced LLM Multi-Agent Systems Based on Blackboard Architecture

来源：https://arxiv.org/pdf/2507.01701

**核心观点**：
- The blackboard is divided into two parts, a public space and private spaces:
  - The former is for all agents to use.
  - The latter solely for those involved in a debate or verification of private matter.
- In the blackboard system, agents communicate solely through the blackboard that contains all historical contexts.
- The blackboard actually serves as a public storage space to replace the memory modules typically possessed by LLM agents.

### 4.3 The Blackboard Architecture: Solving the Agent 'Phone Game'

来源：https://rajatpandit.com/the-blackboard-architecture/

**三个核心原语**：
1. **The Blackboard**: This is a shared, globally accessible state object. It contains the current problem state, partial solutions, and all historical contexts.
2. **Knowledge Sources (Agents)**: Each agent reads from the blackboard, contributes its expertise, and writes back to the blackboard. Agents do not talk to each other directly.
3. **Controller**: A dynamic scheduler that decides which agent should act next based on the current state of the blackboard.

**核心观点**：
- In a Blackboard architecture, agents absolutely do not talk to each other directly. They do not pass messages. Instead, they all talk to the Board.

### 4.4 Blackboard Pattern 官方目录

来源：https://agentpatternscatalog.github.io/patterns/patterns/blackboard.html

**核心组件**：

| 组件 | 说明 |
| --- | --- |
| Shared blackboard | inspectable workspace holding contributions under structured keys |
| Specialist agent | reader-writer that contributes when the board state matches its trigger |
| Controller | optional scheduler that decides which agent runs next given the board state |
| Conflict-resolution policy | last-write-wins, version-vector, or append-only discipline |
| Notification channel | change events that wake interested agents on relevant key updates |

### 4.5 Blackboard Architecture for Agent Collaboration Under Shared State

来源：https://gist.github.com/prasad-kumkar/090521fcd55d17113af8986146a9b04e

**四个组成部分**：
1. **a shared state store called the blackboard**
2. **specialized knowledge sources, which are the agents**
3. **a trigger or subscription layer that tells agents when to act**
4. **a control shell that orchestrates the overall process**

**核心观点**：
- This is not just a shared database. A good blackboard system has explicit object types, write rules, freshness controls, and conflict management.
- Without those controls, the blackboard turns into a noisy junk drawer and collaboration gets worse, not better.

### 4.6 Blackboard Architecture for Multi-Agent Systems: Shared Knowledge Spaces

来源：https://www.callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces

**核心观点**：
- The blackboard architecture is a problem-solving pattern where multiple specialist agents (called knowledge sources) collaborate by reading from and writing to a shared data structure — the blackboard.
- A control shell decides which agent should act next based on the current state of the blackboard.
- Build a shared knowledge space where specialized agents contribute partial solutions that converge into complete answers.

### 4.7 黑板模式介绍

来源：https://blog.csdn.net/qq_39437730/article/details/143183162

**核心观点**：
- 黑板模式（Blackboard Pattern）是一种用于解决复杂问题的架构模式，通常用于需要多个不同模块协同工作并通过共享信息来解决问题的场景。
- 它是一种面向知识共享的模式，广泛应用于人工智能系统、专家系统、机器人系统、复杂控制系统等领域。
- 黑板模式的核心思想是创建一个共享的全局数据结构，称为"黑板"，不同的模块（称为知识源或代理）可以在黑板上读取和写入信息。

### 4.8 7种常见的多Agent协作架构模式——模式四：Blackboard（黑板模型）

来源：https://juejin.cn/post/7644744610916335657

**核心观点**：
- 黑板模型是源自上世纪70年代的经典AI架构，最早被应用在语音识别系统中。
- 核心逻辑：所有Agent之间不直接交互沟通，系统内共享一块公共"黑板"；各个Agent按需读取黑板上的相关信息，完成自身任务后，再把结果更新写入黑板即可。
- 最大的好处：每个Agent只需订阅自身业务相关的信息字段，不用关心其他Agent在做什么，实现了完全的解耦。

### 4.9 Blackboard Architecture 学术定义

来源：https://cs.uwaterloo.ca/~m2nagapp/courses/CS446/1181/Arch_Design_Activity/Blackboard.pdf

**核心组件定义**：

- **Blackboard**: A global accessible database which stores inputs, partial solutions and partial results. The Blackboard represents the current system state.
- **Knowledge Source**: A knowledge source is an independent module which contains specialized knowledge needed for solving a problem. Each knowledge source has a set of triggering conditions, when satisfied, the knowledge source is enabled and executed to help progress the state of the problem on the Blackboard by solving a sub-problem which they specialize in.

---

## 五、参考资源汇总

### 多Agent角色卡体系
1. https://github.com/dformoso/positronic/blob/main/docs/agentic-patterns/02_role_design_detailed.md
2. https://arxiv.org/pdf/2604.27882v1
3. https://hub.cocoloop.cn/skills/243
4. https://blog.csdn.net/weixin_51035135/article/details/158659469
5. https://github.com/a-organvm/collective-persona-operations
6. https://blog.csdn.net/sjsi13/article/details/164231010
7. https://github.com/CTOUT/Symdicate
8. https://m.nowcoder.com/discuss/916430150495895552

### Hierarchical Multi-Agent架构
1. https://arxiv.org/pdf/2603.19270
2. https://juejin.cn/post/7644744610916335657
3. https://juejin.cn/post/7668547554775367720
4. https://github.com/GieshBuilds/hierarchical-agents
5. https://www.woshipm.com/ai/1546717.html
6. https://blog.csdn.net/qq_qingtian/article/details/155059280
7. https://gurusup.com/blog/agent-orchestration-patterns
8. https://codefully.ai/blog/multi-agent-orchestration

### API路由和模型分配
1. https://blog.csdn.net/qq_73472828/article/details/160699220
2. https://xie.infoq.cn/article/ded5f03c6294454772a0e0f1c
3. https://www.arxiv.org/pdf/2506.17254
4. https://github.com/Francis1998/nexus-llm-router
5. https://blog.csdn.net/lotusxyhf/article/details/162575549
6. https://www.cnblogs.com/wgwyanfs/p/21285018
7. https://futureagi.com/blog/best-ai-gateways-model-routing/
8. https://github.com/large-scale-ai-systems/multi-llm-router

### 世界书/共享信息空间（Blackboard Pattern）
1. https://github.com/ForceInjection/all-agentic-architectures/blob/main/07_blackboard_zh.ipynb
2. https://arxiv.org/pdf/2507.01701
3. https://rajatpandit.com/the-blackboard-architecture/
4. https://agentpatternscatalog.github.io/patterns/patterns/blackboard.html
5. https://gist.github.com/prasad-kumkar/090521fcd55d17113af8986146a9b04e
6. https://www.callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces
7. https://blog.csdn.net/qq_39437730/article/details/143183162
8. https://juejin.cn/post/7644744610916335657
9. https://cs.uwaterloo.ca/~m2nagapp/courses/CS446/1181/Arch_Design_Activity/Blackboard.pdf

---

> **说明**：本文档只做文字搬运工，不做评价或修改。全部方案推进完后，再站在总体角度统一修改。
