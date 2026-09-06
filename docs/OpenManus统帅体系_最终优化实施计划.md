# OpenManus统帅体系 - 最终优化实施计划

> 制定时间：2026-09-06
> 分析来源：豆包（架构分析）+ 智谱清言（工程优化和验证）
> 原则：只做加法，不做减法；保留现有所有功能和经验
> 目标：从"功能原型"向"工程化产品"跨越，最终打包同步到Mac电脑

---

## 一、优化总览

### 1.1 架构优化（来自豆包）

| 优先级 | 优化项 | 核心内容 |
|--------|--------|---------|
| **P0** | 统一门面Commander统帅入口 | 封装ManusWithRoles和MultiRoleOrchestrator，自动判断单角色/多角色路由 |
| **P0** | 轻量事件总线EventBus | 任务启动/角色切换/异常报错/执行完成全部抛出事件，驱动看板更新和日志采集 |
| **P0** | 全局统一状态中心StateStore | 集中持久保存任务元数据、角色运行快照、执行历史、告警标签，消除状态孤岛 |
| **P1** | 统一配置管理层ConfigHub | 聚合toml/txt/世界书，支持环境区分，单独解析模型轮转 |
| **P1** | 异步Worker任务队列 | 拆分网关与执行worker，飞书长连接落地，任务超时管控 |
| **P2** | 标准化集成测试流水线 | 端到端测试覆盖多角色完整协同链路，自动化经验包蒸馏 |

### 1.2 工程优化（来自智谱）

| 优先级 | 优化项 | 核心内容 |
|--------|--------|---------|
| **P0** | 全局资源锁与Chrome实例隔离 | ResourceManager单例，维护Browser实例池，并行模式限制同时运行的Browser数量 |
| **P0** | 强制全局网络超时控制 | 应用启动入口第一行执行socket.setdefaulttimeout(180)，所有HTTP调用封装显式timeout |
| **P1** | 统一配置中心ConfigHub | 聚合TOML/TXT/世界书，环境变量覆盖，模型轮转逻辑独立解析器 |
| **P1** | 重试与熔断机制 | ResilienceDecorator，指数退避重试，特定死循环逻辑熔断 |
| **P2** | 统一日志流与结构化输出 | LogMonitor升级为asyncio.Queue事件消费者，所有组件发送结构化日志事件，包含trace_id |

### 1.3 目标架构（五层）

```
接入网关层（FeishuHandler / CmdConsoleHandler / WebAPI Handler）
    ↓
统一统帅门面层【新增 Commander + EventBus 事件总线】
    ↓
调度编排层（ManusWithRoles / MultiRoleOrchestrator / RoleOrchestrator）
    ↓
执行内核层（Manus原生内核 / Bridge模块 / LLM调用层）
    ↓
持久化&观测底座【新增 StateStore / ConfigHub / ExperienceArchiver】
```

---

## 二、分阶段实施计划

### Phase 5.1：P0核心稳定性（预计2-3小时）

**目标**：解决最紧迫的稳定性问题，保障系统不崩溃

#### 任务清单

| 序号 | 任务 | 内容 | 验收标准 |
|------|------|------|---------|
| 5.1.1 | 全局网络超时控制 | 在应用启动入口第一行执行socket.setdefaulttimeout(180)，所有LLM和飞书API调用封装显式timeout | 长回复不导致线程阻塞，网络波动下系统存活 |
| 5.1.2 | 全局资源锁ResourceManager | 构建ResourceManager单例类，维护Browser实例池或信号量，并行模式限制同时运行的Browser数量为1-2 | 多角色并行调用不产生Chrome Profile冲突或端口冲突 |
| 5.1.3 | 统一门面Commander类 | 创建Commander类，封装ManusWithRoles和MultiRoleOrchestrator，自动判断单角色/多角色路由，统一入参和返回结构 | 外部调用方只需对接Commander，不需要手动判断使用哪个调度器 |
| 5.1.4 | 轻量事件总线EventBus | 创建EventBus模块，支持发布/订阅事件（TaskStart/RoleActivate/ErrorOccur/TaskDone/AlertTrigger），兼容原有同步调用模式 | 任务启动/角色切换/异常报错/执行完成全部抛出事件，看板和日志可订阅 |
| 5.1.5 | 全局统一状态中心StateStore | 创建StateStore类，集中持久保存任务元数据、角色运行快照、执行历史、告警标签，TaskDashboard/RoleOrchestrator/LogMonitor全部读写同一个状态数据源 | 任务失败时可一键汇总任务信息+角色快照+完整运行日志 |

#### 交付物
- `app/commander.py` - 统一门面Commander类
- `app/event_bus.py` - 轻量事件总线
- `app/state_store.py` - 全局统一状态中心
- `app/resource_manager.py` - 全局资源锁
- 修改 `app/agent/manus_with_roles.py` - 集成事件总线和状态中心
- 修改 `app/role_cards/multi_role_orchestrator.py` - 集成资源锁

---

### Phase 5.2：P1架构与可维护性（预计3-4小时）

**目标**：提升架构可维护性，落地飞书长连接

#### 任务清单

| 序号 | 任务 | 内容 | 验收标准 |
|------|------|------|---------|
| 5.2.1 | 统一配置中心ConfigHub | 开发ConfigHub类，聚合TOML/TXT/世界书，支持环境变量覆盖（ENV=prod），模型轮转逻辑提取为独立解析器 | 配置不再分散，模型轮转Bug的土壤消除，支持多环境部署 |
| 5.2.2 | 重试与熔断机制 | 设计ResilienceDecorator，网络请求指数退避重试（1s/2s/4s），特定死循环逻辑熔断（连续3次检测到特定错误日志则终止任务） | 瞬时网络抖动不导致任务失败，死循环逻辑被及时终止 |
| 5.2.3 | 异步Worker任务队列 | 拆分网关与执行worker，FeishuHandler仅负责消息接收与指令提交，真正的AI任务交给后台Worker异步执行，支持任务超时管控（180秒+socket底层超时双配置） | 飞书长连接落地，任务不阻塞飞书网关，支持后台静默执行和离线回调 |
| 5.2.4 | 任务看板Web UI | 基于TaskDashboard数据，创建简单的Web UI（Flask/FastAPI+HTML），展示任务队列、执行进度、重试统计、成功率 | 可通过浏览器实时查看任务状态，不需要看日志文件 |

#### 交付物
- `app/config_hub.py` - 统一配置中心
- `app/resilience.py` - 重试与熔断机制
- `app/worker.py` - 异步Worker任务队列
- `app/web_dashboard.py` - 任务看板Web UI
- `templates/dashboard.html` - 看板页面模板

---

### Phase 5.3：P2可观测性与扩展性（预计2-3小时）

**目标**：完善可观测性，建立自动化经验包蒸馏

#### 任务清单

| 序号 | 任务 | 内容 | 验收标准 |
|------|------|------|---------|
| 5.3.1 | 统一日志流与结构化输出 | LogMonitor升级为基于asyncio.Queue的事件消费者，所有组件不直接写文件，而是发送结构化日志事件，日志包含trace_id | 全链路可追踪，Web UI可展示实时日志 |
| 5.3.2 | 标准化集成测试流水线 | 端到端测试用例覆盖多角色完整协同链路，任务执行结束后自动打三标签/四标签跑批标记 | 每次代码变更后可自动运行集成测试，保障不回归 |
| 5.3.3 | 自动化经验包蒸馏 | 创建ExperienceArchiver类，任务结束自动打包日志、蒸馏文档、更新世界书与标签跑批记录，写入经验包目录 | 经验包自动更新，不需要手动整理 |

#### 交付物
- 修改 `app/remote_control/log_monitor.py` - 升级为事件消费者
- `tests/test_integration.py` - 集成测试
- `app/experience_archiver.py` - 经验包自动蒸馏

---

## 三、bridge网络请求监听升级（已完成）

> 这是次要任务，已在优化期间同步完成

- ✅ 添加了网络请求监听器（被动监听HTTP响应和WebSocket，不触发封控）
- ✅ 在 `_wait_for_fulltext_reply` 之前优先检查网络回复
- ✅ 发送消息前清除上一次的网络回复
- ✅ 在两个页面创建的地方都设置了网络监听器
- ✅ 语法检查通过

**升级原理**：只被动监听浏览器和服务器之间的网络请求，不修改任何请求或响应，不注入任何JavaScript，就像在旁边"旁听"对话，完全不会被AI平台检测到。

---

## 四、经验包打包（已完成）

> 已将一念永恒项目积累的宝贵经验打包到OpenManus项目中

- ✅ 运行记录：54个文件，282.7 KB（三标签/四标签跑批经验、bug修复、验收记录）
- ✅ 蒸馏文档：6个文件，71.71 KB（项目记忆蒸馏版、聊天记录蒸馏版）
- ✅ 世界书：3个文件，20.55 KB（通用世界书v3.9、Command_Log）
- ✅ 小助手说明：3个文件，36.74 KB
- ✅ 文档：1个文件，11.03 KB
- ✅ 经验包说明文档：README.md

**总计**：67个文件，约423 KB

---

## 五、最终打包同步计划

### 5.1 打包前检查清单

- [ ] Phase 5.1（P0核心稳定性）全部完成并测试通过
- [ ] Phase 5.2（P1架构与可维护性）全部完成并测试通过
- [ ] Phase 5.3（P2可观测性与扩展性）全部完成并测试通过
- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 经验包已更新到最新
- [ ] 文档已更新（使用指南、Mac快速上手指南）
- [ ] 配置文件已准备（config.toml，不含真实密钥）
- [ ] .gitignore已配置（排除config.toml、web_cache、日志等）

### 5.2 打包内容

```
OpenManus统帅体系_v1.0/
├── app/                          # 核心代码
│   ├── agent/                    # Agent核心（ManusWithRoles等）
│   ├── role_cards/               # 角色卡模块
│   ├── remote_control/           # 远程控制模块（飞书/看板/日志）
│   ├── commander.py              # 统一门面（新增）
│   ├── event_bus.py              # 事件总线（新增）
│   ├── state_store.py            # 状态中心（新增）
│   ├── config_hub.py             # 配置中心（新增）
│   ├── resource_manager.py       # 资源管理器（新增）
│   ├── resilience.py             # 重试熔断（新增）
│   ├── worker.py                 # 异步Worker（新增）
│   ├── experience_archiver.py    # 经验包蒸馏（新增）
│   └── web_dashboard.py          # Web看板（新增）
├── 角色卡/                        # 角色卡（9张业务卡+管理员卡+世界书+小助手说明）
├── 经验包/                        # 经验包（运行记录+蒸馏+世界书+小助手说明+文档）
├── docs/                          # 文档（架构设计+使用指南+优化方案+成熟方案参考）
├── tests/                         # 测试（单元测试+集成测试）
├── templates/                     # Web模板（看板页面）
├── config.example.toml            # 配置示例（不含真实密钥）
├── requirements.txt               # 依赖列表
├── main.py                        # 主入口
├── README.md                      # 项目说明
└── MAC_QUICKSTART.md             # Mac快速上手指南
```

### 5.3 同步到Mac的步骤

1. 将打包文件上传到GitHub仓库（guolu111/OpenManus）
2. 在Mac电脑上clone仓库
3. 按照MAC_QUICKSTART.md安装依赖
4. 复制config.example.toml为config.toml，填入真实API密钥
5. 运行 `python main.py serve` 启动服务
6. 通过飞书远程控制

---

## 六、任务面板

### 当前任务状态

| 任务 | 状态 | 优先级 |
|------|------|--------|
| bridge网络请求监听升级 | ✅ 已完成 | 次要 |
| 经验包打包 | ✅ 已完成 | 次要 |
| 三标签总体优化分析 | ✅ 已完成 | 主要 |
| Phase 5.1 P0核心稳定性 | ⏳ 待执行 | P0 |
| Phase 5.2 P1架构与可维护性 | ⏳ 待执行 | P1 |
| Phase 5.3 P2可观测性与扩展性 | ⏳ 待执行 | P2 |
| 最终打包同步到Mac | ⏳ 待执行 | 最终目标 |

---

**文档创建时间**：2026-09-06
**分析来源**：豆包（架构分析5970字）+ 智谱清言（工程优化5721字）
**下一步**：开始执行Phase 5.1（P0核心稳定性）
