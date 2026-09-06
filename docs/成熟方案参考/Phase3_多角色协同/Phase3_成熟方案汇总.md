# Phase 3 成熟方案汇总（多角色协同）

> 本文档是Phase 3（多角色协同）对应的成熟方案扒取，只做文字搬运工，不做评价或修改。
> 全部方案推进完后，再站在总体角度统一修改。

---

## 一、多角色协同编排模式（串行/并行/DAG）

### 1.1 多Agent协作的3种编排模式：串行、并行与DAG

来源：https://blog.csdn.net/z_soft_ym/article/details/164230261

**模式一：串行编排（Sequential）**
- 核心逻辑：Agent A的输出，作为Agent B的输入。像流水线一样，一个接一个处理。
```
[输入] → Agent A → Agent B → Agent C → [输出]
```
- 适用场景：业务流程是线性的，每一步的输出都是下一步的输入，且各步骤之间强依赖。
- 典型案例：文档解析 → 信息提取 → 摘要生成 → 格式化输出

**模式二：并行编排（Parallel）**
- 核心逻辑：多个Agent同时处理同一个任务的不同方面，最后由汇总Agent整合结果。
```
          → Agent A（搜索）
[输入] →  → Agent B（分析） → [汇总] → [输出]
          → Agent C（验证）
```
- 适用场景：任务可以拆分为多个独立子任务，各子任务之间没有依赖关系，可以同时执行。
- 典型案例：多源信息检索、多角度分析、多模型交叉验证

**模式三：DAG编排（有向无环图）**
- 核心逻辑：Agent之间的依赖关系形成有向无环图，某些Agent需要等待多个前置Agent完成后才能执行。
```
Agent A → Agent B → Agent D
     ↘ Agent C ↗
```
- 适用场景：任务有复杂的依赖关系，某些步骤需要多个前置步骤的结果作为输入。
- 典型案例：复杂研究报告（需要多个数据源汇总后才能分析）

### 1.2 swarms 企业级多Agent编排框架

来源：https://github.com/kyegomez/swarms

**三种核心架构**：

| Architecture | Description | Best For |
| --- | --- | --- |
| SequentialWorkflow | Agents execute tasks in a linear chain; the output of one agent becomes the input for the next. | Step-by-step processes such as data transformation pipelines and report generation. |
| ConcurrentWorkflow | Agents run tasks simultaneously for maximum efficiency. | High-throughput tasks such as batch processing and parallel data analysis. |
| AgentRearrange | Dynamically maps complex relationships (e.g., a - b, c) between agents. | Flexible and adaptive workflows, task distribution, and dynamic routing. |

### 1.3 多智能体架构深度拆解：协作模式、框架与落地建议

来源：https://www.woshipm.com/ai/1546717.html

**3.3 流水线（Pipeline）**
- 核心逻辑：线性链式传递，多个智能体按固定顺序串联执行，上游智能体的输出作为下游的输入，每个角色生成结构化中间产物，按流程逐步推进。
- 核心特点：结构简单、开发成本低、执行确定性强，无需复杂调度。
- 典型落地：Google ADK、CrewAI
- 适用场景：内容生成流水线、数据处理管道、标准化业务流程

**3.2 层级式（Hierarchical）**
- 核心逻辑：树形分层结构，按「manager → sub-manager → worker」的层级逐级拆解任务，高层负责战略决策，中层负责任务拆分，底层负责执行，实现多层级管控。
- 核心特点：适合大型复杂项目、跨部门协作、企业级工作流。
- 典型落地：Anthropic Claude Subagent、LangGraph 原生支持
- 适用场景：智能客服、RAG+Agent 知识库、内容生成、流程自动化、跨领域复杂任务拆解

### 1.4 多 Agent 工作流：从概念到落地

来源：https://ghp666.blog.csdn.net/article/details/161519067

**四种核心模式**：
业界所有多 Agent 系统，底层不外乎这四种模式的排列组合：
1. 顺序流水线（Sequential Pipeline）
2. 并行分发（Parallel Dispatch）
3. 层级管理（Hierarchical Management）
4. 对等协作（Peer-to-Peer Collaboration）

**核心思想**：
一个 Agent 只专注一件事 → 多个 Agent 并行工作 → 编排器汇总结果

### 1.5 多Agent协作模式完全指南：从单兵到军团的架构设计

来源：https://blog.csdn.net/su2231595742/article/details/163197783

**三大基础模式（铁三角）**：
多篇文章指出：顺序、并行、层级三种模式覆盖了90%的实际场景。这是多Agent协作的"铁三角"。

**① 流水线 串行（Pipeline / Sequential）**
- 核心思想：Agent像工厂流水线上的工位，前一个的输出是后一个的输入，严格按序执行。
- 数据流特征：单向流动，信息只从左到右（或从上到下）。

**② 并行 分发（Parallel / Fan-out）**
- 核心思想：一个调度器把任务拆成多个独立子任务，分发给多个Worker同时执行，最后汇总结果。
- 数据流特征：一对多分发，多对一汇总。

**③ 层级 管理（Hierarchical / Manager-Worker）**
- 核心思想：树形结构，顶层Manager拆任务，中层Manager再拆分，底层Worker执行。
- 数据流特征：自上而下指令传递，自下而上结果汇报。

### 1.6 Multi-Agent AI Systems in Production

来源：https://www.aimagicx.com/blog/multi-agent-ai-production-architecture-patterns-2026

**Pipeline模式**：
```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│(Ingest)  │ → │(Process) │ → │(Validate)│ → │(Output)  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
```
- How it works: Agents are arranged in a linear sequence. Each agent's output becomes the next agent's input. Similar to Unix pipes but with AI agents.

---

## 二、中层指挥官（Hierarchical Multi-Agent / Manager-Worker）

### 2.1 Manager-Worker Agent Architectures: A Practical Introduction

来源：https://www.swarms.ai/blog/manager-worker-agent-architectures

**核心观点**：
- A manager-worker architecture, sometimes called a director-worker or hierarchical pattern, fixes this by splitting a task into two distinct roles:
  - one agent that plans and delegates
  - a set of agents that execute
- This post is about that split, the topology of who reports to whom and how a task moves through the hierarchy, not the messaging mechanics underneath it.

### 2.2 Why Single Agents Fail: Building Scalable AI Teams with the Manager-Worker Pattern

来源：https://programmingcentral.hashnode.dev/why-single-agents-fail-building-scalable-ai-teams-with-the-manager-worker-pattern

**核心观点**：
- Hierarchical Agent Teams solve this by introducing a Manager-Worker pattern.
- This is a structural architecture where a "Manager" agent (often called a Supervisor or Orchestrator) delegates specific subtasks to specialized "Worker" agents.
- The Manager does not perform the actual work; instead, it focuses on task decomposition and routing.
- It analyzes the high-level objective, breaks it down into discrete, manageable units, and assigns each unit to the most competent Worker.

### 2.3 Hierarchical Agents

来源：https://avahi.ai/glossary/hierarchical-agents/

**Typical Roles In A Hierarchical Agent System**

**Supervisor or Director Agent**
- Purpose: Owns the overall objective and boundaries.
- Responsibilities:
  - Interpret user intent and constraints
  - Define success criteria and stopping conditions
  - Enforce governance rules (policy, permissions, risk limits)
  - Decide whether to accept, revise, or reject outputs

**Manager or Planner Agent**
- Purpose: Convert strategy into actionable tasks.
- Responsibilities:
  - Decompose goals into sub-tasks
  - Assign tasks to appropriate workers
  - Monitor progress and handle failures
  - Aggregate results from workers

**Worker Agent**
- Purpose: Execute specialized tasks.
- Responsibilities:
  - Perform assigned sub-tasks
  - Report results and status
  - Handle errors within their scope

### 2.4 大模型多Agent核心能力：深入了解协作架构与任务调度

来源：https://bbs.huaweicloud.com/blogs/d2d32ae48a084890a8af8f70da2666f6

**分层层级架构**：
- 中心化架构的升级版本。
- 解决单中心Agent算力不足、统筹能力有限的问题。
- 采用树形分层结构，分为顶层、中层、底层三级Agent，分级管理、层层递进。

**层级职责**：
- **顶层Agent**：负责全局需求拆解、目标把控、结果终审；
- **中层Agent**：承接板块任务，二次拆分并分配工作、汇总板块结果；
- **底层Agent**：专注具体任务落地执行。

**优缺点**：
- 优点：分摊统筹压力、权责清晰、可扩展性强
- 缺点：层级过多会增加通信延迟、需要良好的中层设计

### 2.5 AI Agent设计模式 Day 14: Hierarchical模式

来源：https://blog.csdn.net/qq_qingtian/article/details/155059280

**架构设计**：
Hierarchical模式的系统架构呈金字塔形，包含三层核心组件：

**顶层：Manager Agent**
- 输入：用户自然语言请求
- 输出：结构化任务计划（JSON格式）
- 能力：战略思维、优先级排序、风险评估

**中层：Coordinator Agents（按领域划分）**
- 示例：ResearchCoordinator、WritingCoordinator、DataAnalysisCoordinator
- 输入：高层任务指令
- 输出：原子操作序列
- 能力：领域知识、工具理解、依赖管理

**底层：Worker Agents**
- 输入：原子操作
- 输出：执行结果
- 能力：具体工具调用、专业领域执行

**核心观点**：
- 在现实世界中，许多任务无法由单一Agent或扁平化多Agent系统高效完成。
- Hierarchical模式借鉴了组织管理学中的"指挥链"思想和软件工程中的"分层架构"。
- 将整体任务自上而下分解为战略层、战术层和执行层，每一层由专门的Agent负责，形成清晰的控制流与信息流。
- 该模式特别适用于高复杂度、长周期、多阶段的任务。

### 2.6 Multi-Agent 架构全景：10 种协作模式深度解析

来源：https://gitcode.csdn.net/69b7db3c0a2f6a37c597e09d.html

**Manager-Worker模式架构图**：
```
┌──────┐
│ User │
└──┬───┘
   ▼
┌──────────┐
│ Manager  │  ← 拆分子任务、分配负责人、设定交付物
└────┬─────┘
     │
┌───────┼────────┐
▼       ▼        ▼
┌────────┐┌────────┐┌────────┐
│Worker A││Worker B││Worker C...│
└────────┘└────────┘└────────┘
```

### 2.7 Comparative Analysis of Agent Organization Models

来源：https://apxml.com/courses/multi-agent-llm-systems-design-implementation/chapter-2-architecting-agents-defining-roles/agent-organization-models

**Hierarchical Organization**：
- A hierarchical organization, also known as a centralized or leader-follower model, structures agents in a top-down command system.
- Typically, one or more manager agents oversee a group of worker agents.
- Manager agents are responsible for decomposing tasks, assigning sub-tasks to worker agents, monitoring progress, and aggregating results.
- Worker agents focus on executing their assigned specialized tasks and reporting back.

### 2.8 What are hierarchical AI agents?

来源：https://www.ibm.com/think/topics/hierarchical-ai-agents

**三层架构**：

**High-level agents**
- High-level agents are responsible for the "big picture," managing the overall system in alignment with broader goals.
- Interpreting a user request, forming a plan and dividing that plan into tasks are all high-level agent responsibilities.

**Mid-level agents**
- Mid-level agents receive directives from high-level agents.
- They refine and implement plans, further decompose tasks when needed and coordinate teams of low-level agents.
- In hierarchies without mid-level agents, high-level agents assume these duties in addition to their own.

**Low-level agents**
- Low-level agents perform the most specific, focused tasks within the system.
- They execute individual actions, process data, and handle specialized operations.

---

## 三、世界书/共享信息空间（Shared Memory / Blackboard）

### 3.1 Shared Memory and Blackboard Patterns

来源：https://github.com/rohitg00/ai-engineering-from-scratch/blob/df0fa776b128fce4f457aea02c0816d2ae981cc9/phases/16-multi-agent-and-swarms/13-shared-memory-blackboard/docs/en.md

**架构图**：
```
agent-A ──write──▶ ┌────────────────┐ ◀──read── agent-D
                   │ message pool   │
agent-B ──write──▶ │                │ ◀──read── agent-E
                   │ (global log)   │
agent-C ──write──▶ └────────────────┘ ◀──read── agent-F
```
- Blackboard with subscription.

### 3.2 Memory in LLM-based Multi-agent Systems: Mechanisms, Challenges, and Collective Intelligence

来源：https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.176539617.79044553/v1

**Shared Memory定义**：
- Shared memory is a memory resource accessible to multiple agents in the team.
- It serves as a common knowledge repository or global memory that the team of agents can collectively read from and contribute to.
- Shared memory could be a vector database, knowledge graph, or document that aggregates information from all agents.
- Unlike local memory, which is siloed per agent, shared memory breaks those silos.

### 3.3 基于大模型的多智能体系统中的记忆设计综述

来源：https://blog.csdn.net/qq_58602552/article/details/160121353

**共享记忆形式**：
- 向量数据库、知识图谱、文档、黑板。

**共享记忆作用**：
- 打破信息孤岛，形成团队全局心智。
- 可带权限策略，尤其适合竞争场景。

**Orchestrator（协调器）**：
- 负责调度、分配任务、合并信息、管理全局记忆的特殊智能体 / 模块。
- 持有高层策略，决定谁在何时行动。

**Blackboard（黑板）**：
- 经典去中心化求解架构，所有智能体可读写的共享工作区。
- 智能体根据黑板状态决定是否行动，无需中央调度器。

### 3.4 Blackboard Architecture for Multi-Agent Systems: Shared Knowledge Spaces

来源：https://www.callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces

**核心观点**：
- The blackboard architecture is a problem-solving pattern where multiple specialist agents (called knowledge sources) collaborate by reading from and writing to a shared data structure — the blackboard.
- A control shell decides which agent should act next based on the current state of the blackboard.
- Build a shared knowledge space where specialized agents contribute partial solutions that converge into complete answers.

### 3.5 The supervisor-blackboard pattern: coordinating multi-agent AI workflows

来源：https://simonevellei.com/en/the-supervisor-blackboard-pattern-coordinating-multi-agent-ai-workflows/

**核心观点**：
- Each one gets a prompt, produces output, and hands it to the next step. That works when the data flows in one direction.
- But some workflows need agents to build on each other's work incrementally, reading and writing to a shared context. This is the blackboard pattern.
- The idea comes from AI research in the 1970s.
- Multiple knowledge sources (agents) read from and write to a shared data structure (the blackboard).
- A control component decides which knowledge source should contribute next based on the current state.

### 3.6 多 Agent 记忆要不要共享，如何设计？

来源：https://www.iesdouyin.com/share/video/7681228879284948264

**三层记忆架构**：

**L1 私有记忆（最底层）**：
- 每个agent，比如planner、coder、reviewer，都有自己独享的本地向量库。
- 这里面存的是草稿，中间状态和局部偏好。
- 这些数据默认是不外泄的。
- 优点：检索快、噪声低、能有效防止角色污染。

**L2 共享黑板（中间层）**：
- 这里存的是全局状态，用户画像和最终产物。
- 大家都在这块黑板上读写。
- 为了避免冲突，通常有写入规则（如追加写入、版本控制）。

**L3 全局知识（最顶层）**：
- 这里存的是团队共享的知识库、规则、历史经验。
- 所有agent都可以读取，但只有特定角色可以写入。
- 相当于团队的"宪法"和"百科全书"。

### 3.7 Multi-Agent 系统设计模式

来源：https://blog.csdn.net/qq_74421990/article/details/159954095

**四种核心设计模式**：
1. `Router-Specialist`：适合多能力入口
2. `Planner-Executor`：适合长链路任务分解
3. `Blackboard / Shared Memory`：适合多 Agent 协作共享状态
4. `Event-Driven Orchestration`：适合复杂异步流程

### 3.8 Shared Memory vs. Message Passing in Multi-Agent-Systemen

来源：https://blckalpaca.at/de/wissen/ki-agenten/multi-agent-systeme-grundlagen/shared-memory-vs-message-passing

**Blackboard-Pattern**：
- Das Blackboard-Pattern ist eine Shared-Memory-Variante.
- Ein gemeinsamer Speicher (das Blackboard) hält den Zustand der Aufgabe.
- Mehrere spezialisierte Agenten lesen relevante Teile, tragen ihre Teilergebnisse ein und reagieren auf Änderungen anderer.
- Es eignet sich für Aufgaben ohne festen Ablaufplan.
- Der kritische Punkt ist die Schreibkonsistenz: in Produktion meist als Single-Writer oder mit Versionskontrolle implementiert.

### 3.9 The Blackboard Architecture: Solving the Agent 'Phone Game'

来源：https://rajatpandit.com/the-blackboard-architecture/

**三个核心原语**：
1. **The Blackboard**: This is a shared, globally accessible state object. It contains the current problem state, partial solutions, and all historical contexts.
2. **Knowledge Sources (Agents)**: Each agent reads from the blackboard, contributes its expertise, and writes back to the blackboard. Agents do not talk to each other directly.
3. **Controller**: A dynamic scheduler that decides which agent should act next based on the current state of the blackboard.

**核心观点**：
- In a Blackboard architecture, agents absolutely do not talk to each other directly. They do not pass messages.
- Instead, they all talk to the Board.

---

## 四、参考资源汇总

### 多角色协同编排模式
1. https://blog.csdn.net/z_soft_ym/article/details/164230261
2. https://github.com/kyegomez/swarms
3. https://www.woshipm.com/ai/1546717.html
4. https://ghp666.blog.csdn.net/article/details/161519067
5. https://blog.csdn.net/su2231595742/article/details/163197783
6. https://www.aimagicx.com/blog/multi-agent-ai-production-architecture-patterns-2026

### 中层指挥官（Hierarchical Multi-Agent）
1. https://www.swarms.ai/blog/manager-worker-agent-architectures
2. https://programmingcentral.hashnode.dev/why-single-agents-fail-building-scalable-ai-teams-with-the-manager-worker-pattern
3. https://avahi.ai/glossary/hierarchical-agents/
4. https://bbs.huaweicloud.com/blogs/d2d32ae48a084890a8af8f70da2666f6
5. https://blog.csdn.net/qq_qingtian/article/details/155059280
6. https://gitcode.csdn.net/69b7db3c0a2f6a37c597e09d.html
7. https://apxml.com/courses/multi-agent-llm-systems-design-implementation/chapter-2-architecting-agents-defining-roles/agent-organization-models
8. https://www.ibm.com/think/topics/hierarchical-ai-agents

### 世界书/共享信息空间（Shared Memory / Blackboard）
1. https://github.com/rohitg00/ai-engineering-from-scratch/blob/df0fa776b128fce4f457aea02c0816d2ae981cc9/phases/16-multi-agent-and-swarms/13-shared-memory-blackboard/docs/en.md
2. https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.176539617.79044553/v1
3. https://blog.csdn.net/qq_58602552/article/details/160121353
4. https://www.callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces
5. https://simonevellei.com/en/the-supervisor-blackboard-pattern-coordinating-multi-agent-ai-workflows/
6. https://www.iesdouyin.com/share/video/7681228879284948264
7. https://blog.csdn.net/qq_74421990/article/details/159954095
8. https://blckalpaca.at/de/wissen/ki-agenten/multi-agent-systeme-grundlagen/shared-memory-vs-message-passing
9. https://rajatpandit.com/the-blackboard-architecture/

---

> **说明**：本文档只做文字搬运工，不做评价或修改。全部方案推进完后，再站在总体角度统一修改。
