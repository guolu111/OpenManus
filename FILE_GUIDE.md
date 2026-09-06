# OpenManus统帅体系 - 文件详细说明指南

> 版本：v1.0（P0核心稳定性版）
> 更新时间：2026-09-06
> 说明：本文档对项目中每个文件都有详细说明，新电脑看着本文档就能部署和了解每个细节。

---

## 目录

1. [项目概述](#1-项目概述)
2. [根目录文件说明](#2-根目录文件说明)
3. [app/ 核心代码目录](#3-app-核心代码目录)
4. [角色卡/ 目录](#4-角色卡-目录)
5. [经验包/ 目录](#5-经验包-目录)
6. [docs/ 文档目录](#6-docs-文档目录)
7. [tests/ 测试目录](#7-tests-测试目录)
8. [部署指南](#8-部署指南)
9. [快速开始](#9-快速开始)
10. [常见问题](#10-常见问题)

---

## 1. 项目概述

### 1.1 项目定位

OpenManus统帅体系是一个基于开源OpenManus框架魔改的AI Agent系统，集成了：
- **角色卡体系**：9张业务角色卡，4级权限，五维评分选择器
- **API六层架构**：谷歌中转API为主，智谱4.5/4.0、硅基9B为辅
- **军队式树状结构**：统帅→中层指挥官→角色卡→脚本
- **世界书**：动态共享信息空间（通气公告/决议台账/执行历史）
- **飞书远程操控闭环**：通过飞书消息远程控制和监控

### 1.2 目标架构（五层）

```
接入网关层（FeishuHandler / CmdConsoleHandler / WebAPI Handler）
    ↓
统一统帅门面层【Commander + EventBus 事件总线】
    ↓
调度编排层（ManusWithRoles / MultiRoleOrchestrator / RoleOrchestrator）
    ↓
执行内核层（Manus原生内核 / Bridge模块 / LLM调用层）
    ↓
持久化&观测底座【StateStore / ConfigHub / ExperienceArchiver】
```

### 1.3 版本历史

| 版本 | 日期 | 主要内容 |
|------|------|---------|
| v1.0 | 2026-09-06 | P0核心稳定性版：Commander/EventBus/StateStore/ResourceManager |
| Phase 4 | 2026-09-06 | 飞书远程操控闭环：FeishuHandler/TaskDashboard/LogMonitor |
| Phase 3 | 2026-09-06 | 多角色协同：MultiRoleOrchestrator/3个中层指挥官/世界书 |
| Phase 2 | 2026-09-06 | 角色卡深度集成：ManusWithRoles集成类 |
| Phase 1 | 2026-09-06 | 基础框架：角色卡模块/API六层架构/总体架构设计 |

---

## 2. 根目录文件说明

### 2.1 核心配置文件

| 文件名 | 说明 | 修改位置 |
|--------|------|---------|
| `config.toml` | **核心配置文件**（不含真实密钥，需自行填写） | API密钥、模型配置、模型轮转策略 |
| `config.example.toml` | 配置示例文件 | 参考格式，不直接使用 |
| `.gitignore` | Git忽略文件配置 | 排除config.toml、web_cache、日志等敏感文件 |
| `requirements.txt` | Python依赖列表 | 部署时 `pip install -r requirements.txt` |
| `pyproject.toml` | 项目元数据和构建配置 | 项目名称、版本、依赖 |

### 2.2 入口文件

| 文件名 | 说明 | 功能 |
|--------|------|------|
| `main.py` | **主入口文件** | 启动OpenManus统帅服务，初始化所有组件 |
| `openmanus_runner.py` | 运行器 | 带单实例锁的运行入口，防止多进程冲突 |
| `test_p0_core.py` | P0核心模块测试 | 测试Commander/EventBus/StateStore/ResourceManager |

### 2.3 文档文件

| 文件名 | 说明 |
|--------|------|
| `README.md` | 项目说明（简要） |
| `FILE_GUIDE.md` | **本文档**（详细文件说明） |
| `MAC_QUICKSTART.md` | Mac快速上手指南 |
| `部署指南.md` | 详细部署指南 |

---

## 3. app/ 核心代码目录

### 3.1 目录结构

```
app/
├── __init__.py              # 模块入口
├── agent/                   # Agent核心
│   ├── __init__.py
│   ├── manus.py             # Manus原生内核（开源框架）
│   └── manus_with_roles.py  # ✨ ManusWithRoles集成类（Phase 2）
├── role_cards/              # 角色卡模块（Phase 1）
│   ├── __init__.py
│   ├── role_card.py         # RoleCard数据类 + RoleCardLoader加载器
│   ├── role_registry.py     # ROLE_REGISTRY硬编码9张卡 + PermissionLevel枚举
│   ├── role_selector.py     # RoleSelector角色选择器（五维评分）
│   ├── role_orchestrator.py # RoleOrchestrator角色调度器（激活/取消激活）
│   └── multi_role_orchestrator.py # ✨ MultiRoleOrchestrator多角色协同（Phase 3）
├── remote_control/          # 远程控制模块（Phase 4）
│   ├── __init__.py
│   ├── feishu_handler.py    # FeishuHandler飞书消息处理器
│   ├── task_dashboard.py    # TaskDashboard任务看板
│   └── log_monitor.py       # LogMonitor日志监督器
├── commander.py             # ✨ 统一门面Commander统帅入口（P0）
├── event_bus.py             # ✨ 轻量事件总线EventBus（P0）
├── state_store.py           # ✨ 全局统一状态中心StateStore（P0）
├── resource_manager.py      # ✨ 全局资源锁ResourceManager（P0）
├── config.py                # 配置管理
├── llm.py                   # LLM调用层（模型轮转）
├── single_instance.py       # 单实例锁
└── tool/                    # 工具目录
    ├── __init__.py
    └── optimize_plans_tool.py # 优化计划工具
```

### 3.2 P0核心模块详细说明

#### 3.2.1 `app/commander.py` - 统一门面Commander统帅入口

**文件大小**：约17KB
**核心类**：`Commander`（单例模式）

**功能说明**：
- 作为唯一对外调用门面，封装ManusWithRoles和MultiRoleOrchestrator
- 自动判断单角色/多角色协同路由
- 统一入参格式、统一返回结构、统一提交任务到状态中心
- 兼容两种运行模式：同步阻塞（旧脚本兼容）/ 异步后台任务（飞书长流程）
- 自动对接EventBus与StateStore，所有操作自动落状态、抛事件

**关键方法**：
| 方法 | 说明 |
|------|------|
| `submit_task(command, task_type, run_mode, ...)` | **统一入口**，提交任务 |
| `get_task_status(task_id)` | 获取任务状态（异步模式下查询） |
| `cancel_task(task_id)` | 取消任务 |
| `list_available_roles()` | 列出可用角色 |
| `explain_role_selection(command)` | 解释角色选择 |

**使用示例**：
```python
from app.commander import get_commander, RunMode, TaskType

commander = get_commander()

# 同步模式（阻塞等待结果）
result = await commander.submit_task(
    command="分析这段文本",
    task_type=TaskType.AUTO,  # 自动判断单角色/多角色
    run_mode=RunMode.SYNC,
    role_name="分析",
)

# 异步模式（立即返回task_id，后台执行）
task_id = await commander.submit_task(
    command="并行处理多个任务",
    task_type=TaskType.MULTI_ROLE,
    run_mode=RunMode.ASYNC,
    role_names=["分析", "生成", "匹配"],
)
```

**修改位置**：
- 任务类型判断逻辑：`_detect_task_type()` 方法
- 单角色执行逻辑：`_execute_single_role()` 方法
- 多角色执行逻辑：`_execute_multi_role()` 方法

---

#### 3.2.2 `app/event_bus.py` - 轻量事件总线EventBus

**文件大小**：约8.5KB
**核心类**：`EventBus`（单例模式）、`Event`、`EventType`

**功能说明**：
- 任务启动、角色切换、异常报错、执行完成全部抛出事件
- 驱动看板更新、日志采集、告警触发
- 适配实时日志驱动调试法
- 兼容原有同步调用模式，不破坏现有代码
- 支持通配符订阅（如 "task_*" 订阅所有任务事件）

**事件类型**：
| 事件类型 | 说明 |
|----------|------|
| `TASK_SUBMITTED` | 任务已提交 |
| `TASK_START` | 任务开始执行 |
| `TASK_PROGRESS` | 任务进度更新 |
| `TASK_DONE` | 任务完成 |
| `TASK_FAILED` | 任务失败 |
| `TASK_CANCELLED` | 任务取消 |
| `ROLE_ACTIVATE` | 角色激活 |
| `ROLE_DEACTIVATE` | 角色取消激活 |
| `ERROR_OCCUR` | 错误发生 |
| `ALERT_TRIGGER` | 告警触发 |
| `LOG_EVENT` | 日志事件 |

**使用示例**：
```python
from app.event_bus import get_event_bus, EventType, publish_event

bus = get_event_bus()

# 订阅事件
async def my_handler(event):
    print(f"收到事件: {event.event_type.value} - {event.message}")

bus.subscribe("task_start", my_handler)
bus.subscribe("task_*", my_handler)  # 通配符订阅

# 发布事件
await publish_event(
    EventType.TASK_START,
    message="任务开始",
    task_id="task_001",
    role_name="分析",
)
```

**修改位置**：
- 事件类型定义：`EventType` 枚举
- 事件分发逻辑：`_dispatch()` 方法
- 异步worker：`_dispatch_worker()` 方法

---

#### 3.2.3 `app/state_store.py` - 全局统一状态中心StateStore

**文件大小**：约15KB
**核心类**：`StateStore`（单例模式）、`TaskState`、`RoleState`、`AlertState`、`StateSnapshot`

**功能说明**：
- 集中持久保存任务元数据、角色运行快照、执行历史、告警标签
- TaskDashboard、RoleOrchestrator、LogMonitor全部读写同一个状态数据源
- 跑完任务自动打包运行记录，写入经验包目录
- 任务失败时可一键汇总「任务信息 + 角色快照 + 完整运行日志」
- 支持持久化到JSON文件，应用重启后可恢复状态

**状态分类**：
| 分类 | 说明 |
|------|------|
| `tasks` | 任务状态（pending/running/completed/failed/cancelled） |
| `roles` | 角色状态（active/inactive，当前激活的角色卡） |
| `alerts` | 告警状态（active/acknowledged/resolved） |
| `snapshots` | 运行快照（任务执行过程中的关键状态快照） |
| `logs` | 日志索引（按任务和时间索引） |

**使用示例**：
```python
from app.state_store import get_state_store, TaskStatus

store = get_state_store()

# 创建任务
task = await store.create_task(
    task_id="task_001",
    command="分析文本",
    priority=1,
    role_name="分析",
)

# 更新任务状态
task = await store.update_task_status(
    "task_001",
    TaskStatus.RUNNING,
    progress=0.5,
)

# 获取任务完整汇总（任务信息 + 角色快照 + 完整运行日志）
summary = await store.get_task_summary("task_001")
```

**修改位置**：
- 持久化逻辑：`_save()` 和 `_load()` 方法
- 任务汇总逻辑：`get_task_summary()` 方法
- 持久化目录：初始化时的 `persist_dir` 参数

---

#### 3.2.4 `app/resource_manager.py` - 全局资源锁ResourceManager

**文件大小**：约6.8KB
**核心类**：`ResourceManager`（单例模式）

**功能说明**：
- 维护Browser实例池或信号量，确保Chrome实例在任务期间独占
- 并行模式下强制限制同时运行的Browser数量（默认1，最安全）
- 确保launch_persistent_context启动的Chrome实例不产生Profile冲突或端口冲突
- 任务结束后自动释放资源

**关键方法**：
| 方法 | 说明 |
|------|------|
| `acquire_browser(purpose, timeout)` | 获取浏览器资源（信号量控制并发数） |
| `acquire_profile(profile_path, timeout)` | 获取Chrome Profile独占锁 |
| `acquire_port(port, timeout)` | 获取端口独占锁 |
| `get_active_resources()` | 获取当前活跃的资源列表 |
| `get_stats()` | 获取资源管理器统计信息 |

**使用示例**：
```python
from app.resource_manager import get_resource_manager, setup_global_timeout

# 设置全局网络超时（应用启动时第一行调用）
setup_global_timeout(180)

rm = get_resource_manager()

# 获取浏览器资源（自动控制并发数）
async with rm.acquire_browser("角色A跑批") as res:
    # 执行需要浏览器的任务
    pass
# 自动释放资源
```

**修改位置**：
- 最大并发浏览器数：初始化时的 `max_concurrent_browsers` 参数（默认1）
- 资源锁实现：`acquire_browser()` 等上下文管理器方法

---

### 3.3 Phase 1-4 模块说明

#### 3.3.1 `app/role_cards/` - 角色卡模块（Phase 1）

| 文件 | 说明 | 核心功能 |
|------|------|---------|
| `role_card.py` | RoleCard数据类 + RoleCardLoader | 15+字段角色卡定义，从txt读取带缓存 |
| `role_registry.py` | ROLE_REGISTRY + PermissionLevel | 硬编码9张卡元信息，4级权限枚举 |
| `role_selector.py` | RoleSelector角色选择器 | 五维评分（关键词0.5+任务类型0.4+权限0.1+上下文0.1），匹配算法优化 |
| `role_orchestrator.py` | RoleOrchestrator角色调度器 | 激活/取消激活角色，注入角色卡前缀到system_prompt |
| `multi_role_orchestrator.py` | MultiRoleOrchestrator多角色协同 | 串行/并行/混合三种模式，3个中层指挥官，世界书动态更新 |

**9张角色卡**：
1. 文件夹管理员（L3权限）
2. 分析（L0）
3. 生成（L1）
4. 老师（L0）
5. 学生（L1）
6. 匹配（L0）
7. 小助手（L2）
8. 每天更新（L2）
9. 脚本（L1）

---

#### 3.3.2 `app/agent/manus_with_roles.py` - ManusWithRoles集成类（Phase 2）

**功能说明**：
- 继承Manus，添加角色卡支持
- 角色选择/激活取消激活/run_with_role/run_with_auto_role
- 工具权限过滤框架
- 模型路由框架

**关键方法**：
| 方法 | 说明 |
|------|------|
| `select_role(command)` | 自动选择合适的角色 |
| `activate_role(role_name)` | 激活角色 |
| `deactivate_role()` | 取消激活角色 |
| `run_with_role(role_name, command)` | 用指定角色执行任务 |
| `run_with_auto_role(command)` | 自动选择角色执行任务 |
| `role_status()` | 获取当前角色状态 |
| `explain_role_selection(command)` | 解释角色选择原因 |
| `list_available_roles()` | 列出可用角色 |

---

#### 3.3.3 `app/remote_control/` - 远程控制模块（Phase 4）

| 文件 | 说明 | 核心功能 |
|------|------|---------|
| `feishu_handler.py` | FeishuHandler飞书消息处理器 | 消息解析/指令解析/消息发送/签名验证/令牌管理 |
| `task_dashboard.py` | TaskDashboard任务看板 | 优先级队列/状态追踪/重试机制/统计报告/状态持久化 |
| `log_monitor.py` | LogMonitor日志监督器 | 实时扫描/日志级别识别/错误模式识别/告警聚合/统计分析 |

**飞书指令**：
- `/task` - 提交任务
- `/status` - 查看状态
- `/help` - 帮助
- `/role` - 角色管理
- `/chat` - 普通对话

---

## 4. 角色卡/ 目录

### 4.1 目录结构

```
角色卡/
├── 文件夹管理员.txt          # 总管理员卡（控制链权威源）
├── 每天更新.txt              # 连载业务卡（R-01~R-20）
├── 老师.txt                  # 老师角色卡
├── 分析.txt                  # 分析角色卡
├── 生成.txt                  # 生成角色卡
├── 学生.txt                  # 学生角色卡
├── 匹配.txt                  # 匹配角色卡
├── 小助手.txt                # 中转API调度管家
├── 脚本.txt                  # 脚本角色卡
├── 世界书/                   # 世界书目录
│   ├── 通用世界书_v3.9.txt  # 通用世界书
│   ├── Command_Log.txt      # 命令日志
│   └── 数据契约_Schema_v1.0.json # 数据契约Schema
├── 小助手说明/               # 小助手说明目录
│   ├── 豆包桥接_测试失败记录_待激活.txt # 豆包测试失败记录
│   ├── 小助手使用说明.txt    # 小助手使用说明
│   └── 统一桥接服务_测试报告_v1.0.txt # 桥接服务测试报告
├── 文档/                     # 文档目录
│   └── 四角色卡v5.0修改方案_四层分开版.txt # 四角色卡修改方案
├── 蒸馏/                     # 蒸馏文档目录
│   ├── 项目记忆_蒸馏版.txt   # 项目记忆蒸馏版
│   ├── 蒸馏_20260903_0811.txt # 蒸馏记录
│   ├── 流程总览_小助手整理_20260903.txt # 流程总览
│   ├── 每天更新_备份_v2.0_起承转合前.txt # 每天更新备份
│   ├── 聊天记录蒸馏版（角色卡相关）.txt # 角色卡相关聊天记录蒸馏
│   └── 聊天记录蒸馏版（非角色卡相关）.txt # 非角色卡相关聊天记录蒸馏
└── 运行记录/                 # 运行记录目录（54个文件）
    ├── 角色卡运行记录_v1.0.txt
    ├── 10个方案三标签深度优化任务完成报告_20260906.txt
    ├── 鹿鼎记跑批报告_20260905.txt
    ├── 4标签跑批全流程方案_20260904.txt
    ├── CDP直连3标签_第21章跑批报告_20260904.txt
    └── ...（更多运行记录）
```

### 4.2 角色卡格式说明

每张角色卡txt文件包含以下字段：
```
【角色名称】：分析
【权限级别】：L0（只读）
【适用场景】：文本分析、内容总结、数据解读
【核心能力】：...
【工具白名单】：read_file, search, analyze
【偏好模型】：gemini-2.5-flash-lite
【系统提示词】：...
```

---

## 5. 经验包/ 目录

### 5.1 目录结构

```
经验包/
├── README.md                 # 经验包说明文档
├── 运行记录/                 # 54个文件，282.7 KB
│   ├── 角色卡运行记录_v1.0.txt
│   ├── 10个方案三标签深度优化任务完成报告_20260906.txt
│   ├── 鹿鼎记跑批报告_20260905.txt
│   ├── 鹿鼎记24-28章四API跑批详细报告_20260905.txt
│   ├── CDP直连3标签_第21章跑批报告_202604.txt
│   ├── 4标签跑批全流程方案_20260904.txt
│   ├── 4标签跑批全流程报告_20260904.txt
│   ├── 任务Pro充当统帅_第9-21章跑批记录（13个文件）
│   ├── 验收记录_第20-21章（6个文件）
│   ├── 跑批归档_第20-21章（6个文件）
│   └── ...（更多运行记录）
├── 蒸馏/                     # 6个文件，71.71 KB
│   ├── 项目记忆_蒸馏版.txt
│   ├── 蒸馏_20260903_0811.txt
│   ├── 流程总览_小助手整理_20260903.txt
│   ├── 每天更新_备份_v2.0_起承转合前.txt
│   ├── 聊天记录蒸馏版（角色卡相关）.txt
│   └── 聊天记录蒸馏版（非角色卡相关）.txt
├── 世界书/                   # 3个文件，20.55 KB
│   ├── 通用世界书_v3.9.txt
│   ├── Command_Log.txt
│   └── 数据契约_Schema_v1.0.json
├── 小助手说明/               # 3个文件，36.74 KB
│   ├── 豆包桥接_测试失败记录_待激活.txt
│   ├── 小助手使用说明.txt
│   └── 统一桥接服务_测试报告_v1.0.txt
└── 文档/                     # 1个文件，11.03 KB
    └── 四角色卡v5.0修改方案_四层分开版.txt
```

### 5.2 经验包价值

**运行记录（最宝贵）**：
- 三标签/四标签跑批经验
- bug修复记录
- 验收记录
- 省流模式经验
- 工具开发经验

**关键经验**：
1. 实时日志驱动调试法：只看日志、根据日志改代码、不手动干预、让统帅自己跑、卡住才介入
2. 模型轮转的正确实现方式：不能放在[llm.model_rotation]下，必须单独解析
3. bridge与Chrome的关系：bridge使用launch_persistent_context启动自己的Chrome实例，不能与提问机器同时使用同一个profile
4. 长回复处理的关键：超时时间要足够长（至少180秒），找不到"重新回答"按钮时不能死循环
5. 超时设置的正确方式：必须同时设置socket.setdefaulttimeout(timeout)

---

## 6. docs/ 文档目录

### 6.1 目录结构

```
docs/
├── README.md                 # 文档索引
├── API_ARCHITECTURE.md       # API六层架构设计（7.2KB）
├── OVERALL_ARCHITECTURE.md   # 总体架构设计（9.6KB）
├── ROLE_CARDS_ARCHITECTURE.md # 角色卡体系架构设计（4.9KB）
├── PROJECT_STRUCTURE.md      # 项目结构和目录索引（7.4KB）
├── USAGE_GUIDE.md            # 使用方法指南（3.3KB）
├── MAC_QUICKSTART.md         # Mac快速上手指南（2.8KB）
├── DEBUG_GUIDE.md            # 调试指南
├── 总体优化分析.md            # 总体优化分析（4KB）
├── OpenManus统帅体系_最终优化实施计划.md # 最终优化实施计划
├── 三标签总体优化分析/        # 三标签优化分析目录
│   ├── 00_汇总报告.md
│   ├── 01_豆包_架构分析.md
│   ├── 02_千问_功能优化.md
│   └── 03_智谱_工程优化和验证.md
└── 成熟方案参考/              # 成熟方案参考目录
    ├── Phase1_基础框架/
    │   └── Phase1_成熟方案汇总.md（17.6KB）
    ├── Phase2_角色卡集成/
    │   └── Phase2_成熟方案汇总.md（14.9KB）
    ├── Phase3_多角色协同/
    │   └── Phase3_成熟方案汇总.md（15.3KB）
    └── Phase4_飞书远程操控/
        └── Phase4_成熟方案汇总.md（14.1KB）
```

---

## 7. tests/ 测试目录

### 7.1 测试文件

| 文件 | 说明 | 测试内容 |
|------|------|---------|
| `test_p0_core.py` | P0核心模块测试 | Commander/EventBus/StateStore/ResourceManager，6个测试全部通过 |
| `test_role_cards.py` | 角色卡单元测试 | registry/loader/selector/orchestrator |
| `test_role_integration.py` | 角色卡集成测试 | 初始化/选择/加载/激活取消激活/选择解释 |
| `test_manus_with_roles.py` | ManusWithRoles集成测试 | 5个测试函数 |
| `test_multi_role.py` | 多角色协同测试 | 6个测试函数（初始化/指挥官/串行/并行/指挥官调度/世界书） |
| `test_remote_control.py` | 远程控制模块测试 | 飞书消息处理器/任务看板/日志监督器 |

### 7.2 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行P0核心模块测试
python test_p0_core.py

# 运行特定测试
python -m pytest tests/test_role_cards.py -v
```

---

## 8. 部署指南

### 8.1 环境要求

| 项目 | 要求 | 说明 |
|------|------|------|
| 操作系统 | macOS 12+ / Windows 10+ / Linux | 推荐macOS 15 |
| Python | 3.10+ | 推荐3.12（已测试） |
| 内存 | 8GB+ | 推荐16GB |
| 磁盘 | 2GB+ | 包含依赖和缓存 |
| 网络 | 可访问谷歌中转API | 需要API密钥 |

### 8.2 部署步骤

#### 步骤1：克隆仓库

```bash
git clone https://github.com/guolu111/OpenManus.git
cd OpenManus
```

#### 步骤2：创建虚拟环境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 步骤3：安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

#### 步骤4：配置API密钥

```bash
# 复制配置示例
cp config.example.toml config.toml

# 编辑config.toml，填入真实API密钥
# [llm]
# api_key = "你的API密钥"
# base_url = "https://gcli.ggchan.dev"
```

**重要**：`config.toml` 已被 `.gitignore` 排除，不会被提交到Git仓库。

#### 步骤5：初始化角色卡和经验包

角色卡和经验包已经包含在仓库中，无需额外操作。

#### 步骤6：运行测试验证

```bash
python test_p0_core.py
```

如果所有测试通过，说明部署成功。

#### 步骤7：启动服务

```bash
# 方式1：直接运行
python main.py

# 方式2：带单实例锁运行（推荐）
python openmanus_runner.py
```

### 8.3 飞书配置（可选）

如果需要使用飞书远程操控功能，需要额外配置：

1. 在飞书开放平台创建应用
2. 获取App ID和App Secret
3. 配置事件订阅（WebSocket长连接）
4. 在 `config.toml` 中填入飞书配置

详细配置见 `docs/USAGE_GUIDE.md`。

---

## 9. 快速开始

### 9.1 最简单的使用方式

```python
import asyncio
from app.commander import get_commander, RunMode, TaskType

async def main():
    # 获取Commander实例
    commander = get_commander()
    
    # 提交任务（同步模式，阻塞等待结果）
    result = await commander.submit_task(
        command="请分析这段文本的主要观点",
        task_type=TaskType.AUTO,  # 自动判断单角色/多角色
        run_mode=RunMode.SYNC,
    )
    
    print(f"任务状态: {result.status}")
    print(f"结果: {result.result}")

asyncio.run(main())
```

### 9.2 使用事件总线

```python
from app.event_bus import get_event_bus, EventType

bus = get_event_bus()

# 订阅任务完成事件
async def on_task_done(event):
    print(f"任务完成: {event.task_id}")
    print(f"结果: {event.data}")

bus.subscribe("task_done", on_task_done)
```

### 9.3 使用状态中心

```python
from app.state_store import get_state_store, TaskStatus

store = get_state_store()

# 创建任务
task = await store.create_task(
    task_id="my_task",
    command="我的任务",
    role_name="分析",
)

# 更新状态
task = await store.update_task_status("my_task", TaskStatus.RUNNING, progress=0.5)

# 获取完整汇总
summary = await store.get_task_summary("my_task")
```

---

## 10. 常见问题

### Q1：如何修改API密钥？

**A**：编辑 `config.toml` 文件，修改 `[llm]` 部分的 `api_key` 和 `base_url`。修改后重启服务即可。

### Q2：如何添加新的角色卡？

**A**：
1. 在 `角色卡/` 目录下创建新的txt文件，按照角色卡格式编写
2. 在 `app/role_cards/role_registry.py` 的 `ROLE_REGISTRY` 中添加新角色卡的元信息
3. 重启服务

### Q3：如何修改模型轮转策略？

**A**：编辑 `config.toml` 文件，修改 `[model_rotation]` 部分。注意：模型轮转必须单独解析，不能放在 `[llm]` 配置块下（这是经验包中的重要教训）。

### Q4：如何查看运行日志？

**A**：
- 实时日志：服务启动后会在控制台输出
- 历史日志：查看 `经验包/运行记录/` 目录
- 任务日志：通过 `StateStore.get_task_logs(task_id)` 获取

### Q5：如何备份和恢复状态？

**A**：
- 备份：复制 `state_store.json` 文件（在持久化目录下）
- 恢复：将备份的 `state_store.json` 放回持久化目录，重启服务即可恢复

### Q6：飞书远程操控如何配置？

**A**：详见 `docs/USAGE_GUIDE.md` 中的飞书配置部分。需要在飞书开放平台创建应用，配置事件订阅，然后在 `config.toml` 中填入飞书配置。

### Q7：如何升级到新版本？

**A**：
```bash
git pull
pip install -r requirements.txt --upgrade
python test_p0_core.py  # 验证升级
```

### Q8：遇到问题如何调试？

**A**：
1. 查看控制台输出的实时日志
2. 运行 `test_p0_core.py` 验证核心模块
3. 查看 `经验包/运行记录/` 中的历史记录
4. 参考 `docs/DEBUG_GUIDE.md` 调试指南

---

## 附录：文件修改速查表

| 我想修改... | 应该修改哪个文件 | 具体位置 |
|-------------|-----------------|---------|
| API密钥 | `config.toml` | `[llm]` 部分 |
| 模型轮转策略 | `config.toml` | `[model_rotation]` 部分（必须单独） |
| 添加角色卡 | `角色卡/` + `app/role_cards/role_registry.py` | 新建txt + ROLE_REGISTRY |
| 修改角色选择逻辑 | `app/role_cards/role_selector.py` | `select_role()` 方法 |
| 修改任务执行逻辑 | `app/commander.py` | `_execute_single_role()` / `_execute_multi_role()` |
| 添加事件类型 | `app/event_bus.py` | `EventType` 枚举 |
| 修改状态持久化 | `app/state_store.py` | `_save()` / `_load()` 方法 |
| 修改资源并发数 | `app/resource_manager.py` | `max_concurrent_browsers` 参数 |
| 修改飞书指令 | `app/remote_control/feishu_handler.py` | 指令解析部分 |
| 修改任务看板 | `app/remote_control/task_dashboard.py` | 看板逻辑部分 |
| 修改日志监控 | `app/remote_control/log_monitor.py` | 监控逻辑部分 |

---

**文档版本**：v1.0
**最后更新**：2026-09-06
**维护者**：OpenManus统帅体系开发团队
