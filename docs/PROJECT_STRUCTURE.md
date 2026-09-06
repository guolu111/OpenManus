# 项目结构和目录索引

> 本文档帮助你快速了解OpenManus项目的每个目录和文件是做什么的。

## 一、整体架构

```
OpenManus/
├── 📖 docs/                    # 文档目录（先看这里！）
├── 🧠 app/                     # 核心代码
├── ⚙️ config/                  # 配置文件
├── 📚 knowledge_base/          # 知识库（DeepSeek 3673条思考过程）
├── 📝 training_logs/           # 训练日志和调试方案
├── 📊 evaluation/              # 评测套件
├── 🎨 assets/                  # 静态资源（图片等）
├── 🧪 tests/                   # 测试代码
├── 📦 examples/                # 示例用例
├── 🔌 protocol/                # 协议实现（A2A等）
├── 📁 logs/                    # 运行日志（自动生成）
├── 💾 memory/                  # 持久记忆（自动生成）
├── 🎯 workspace/               # 工作空间（自动生成）
├── main.py                     # 主入口
├── requirements.txt            # Python依赖
├── README.md                   # 项目说明
└── .gitignore                  # Git忽略规则
```

## 二、核心目录详解

### 📖 docs/ - 文档目录（新手必看）

| 文件 | 内容 | 适合谁看 |
|------|------|---------|
| [MAC_QUICKSTART.md](MAC_QUICKSTART.md) | Mac 5分钟快速上手指南 | 第一次使用的人 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 本文档，项目结构和目录索引 | 想了解项目全貌的人 |
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | 使用方法指南，深入学习各种功能 | 已经能启动，想深入使用的人 |
| [DEBUG_GUIDE.md](DEBUG_GUIDE.md) | 调试方案指南，常见问题排查 | 遇到问题的人 |
| [MAC_SOFTWARE_OPTIMIZATION.md](MAC_SOFTWARE_OPTIMIZATION.md) | Mac软件清单和优化方案 | Mac用户，想优化性能的人 |

### 🧠 app/ - 核心代码

```
app/
├── agent/                  # Agent实现
│   ├── base.py            # 基础Agent类
│   ├── manus.py           # 统帅Agent（核心！）
│   ├── toolcall.py        # 工具调用逻辑
│   ├── browser.py         # 浏览器Agent
│   ├── data_analysis.py   # 数据分析Agent
│   ├── mcp.py             # MCP协议Agent
│   ├── react.py           # ReAct模式Agent
│   ├── sandbox_agent.py   # 沙箱Agent
│   └── swe.py             # 软件工程Agent
├── tool/                   # 工具集（20+工具）
│   ├── bash.py            # Shell命令执行
│   ├── python_execute.py  # Python代码执行
│   ├── str_replace_editor.py # 文件编辑
│   ├── file_operators.py  # 文件操作
│   ├── web_search.py      # 网页搜索
│   ├── search/            # 搜索引擎（百度/必应/谷歌/DDG）
│   ├── auto_memory.py     # 自动记忆
│   ├── memory_tool.py     # 记忆工具
│   ├── notify_feishu_tool.py # 飞书通知
│   ├── status_monitor_tool.py # 状态监控
│   ├── usage_tool.py      # 用量统计
│   ├── voice_correct_tool.py # 语音纠错
│   ├── zhipu_helper_tool.py # 智谱助手
│   ├── siliconflow_helper_tool.py # 硅基流动助手
│   ├── bridge_health_tool.py # 3标签桥接健康检查
│   ├── batch_run_tool.py  # 批量跑批
│   ├── optimize_plans_tool.py # 计划优化
│   ├── ask_enhancer_tool.py # 提问增强
│   ├── ask_tag.py         # 3标签提问
│   ├── comment_search_tool.py # 评论搜索
│   ├── computer_use_tool.py # 电脑操作
│   ├── crawl4ai.py        # 网页爬取
│   ├── create_chat_completion.py # 创建聊天补全
│   ├── mcp.py             # MCP工具
│   ├── planning.py        # 规划工具
│   ├── terminate.py       # 终止工具
│   ├── tool_collection.py # 工具集合
│   ├── chart_visualization/ # 图表可视化
│   └── sandbox/           # 沙箱工具
├── prompt/                 # 提示词
│   └── manus.py           # 统帅系统提示词（10章！）
├── config.py               # 配置管理
├── llm.py                  # LLM调用
├── logger.py               # 日志
├── schema.py               # 数据结构
├── single_instance.py      # 单实例锁
├── exceptions.py           # 异常定义
├── bedrock.py              # Bedrock支持
├── dreaming/               # 梦境模块（自我反思）
│   └── dreaming.py
├── flow/                   # 流程引擎
│   ├── base.py
│   ├── flow_factory.py
│   └── planning.py
├── mcp/                    # MCP服务器
│   └── server.py
├── sandbox/                # 沙箱
│   ├── client.py
│   └── core/
├── daytona/                # Daytona沙箱
└── utils/                  # 工具函数
    ├── files_utils.py
    └── logger.py
```

### ⚙️ config/ - 配置文件

| 文件 | 说明 |
|------|------|
| config.example.toml | 示例配置（复制为config.toml后填入密钥） |
| config.example-model-*.toml | 各模型的示例配置 |
| mcp.example.json | MCP配置示例 |

**重要：** `config.toml` 包含真实API密钥，不会被打包到zip中，也不会提交到Git。

### 📚 knowledge_base/ - 知识库

```
knowledge_base/
├── README.md                          # 知识库说明
└── deepseek_thinking/                 # DeepSeek思考过程知识库
    ├── search.py                      # 检索工具
    ├── DeepSeek思考经验包.txt          # 105条精选思考示例（6大分类）
    ├── DeepSeek思考经验包.json         # 3673条结构化思考过程
    ├── DeepSeek_AI回复语料.txt         # AI回复语料（34.84 MB）
    ├── DeepSeek用户消息语料.txt        # 用户消息语料（49.43 MB）
    ├── DeepSeek词频统计.json           # 词频统计
    ├── _extract_thinking.py           # 思考过程提取脚本
    └── _extract_deepseek.py           # DeepSeek数据提取脚本
```

**使用方法：**
```bash
# 查看统计
python knowledge_base/deepseek_thinking/search.py --stats

# 按关键词搜索
python knowledge_base/deepseek_thinking/search.py --keyword "任务拆解"

# 按分类查询
python knowledge_base/deepseek_thinking/search.py --category "需求分析"

# 随机抽取示例
python knowledge_base/deepseek_thinking/search.py --random 5
```

### 📝 training_logs/ - 训练日志和调试方案

```
training_logs/
├── README.md                             # 训练日志说明
├── TEMPLATE.md                           # 日志模板
├── 001_实时日志驱动调试法.md              # 调试方法1
├── 002_完整版调试方案.md                  # 调试方法2
├── Manus官方提示词参考_20260906.md       # 官方提示词参考
├── 工具分类管理框架_20260906.md           # 工具管理框架
├── fix_rotation.py                       # 修复模型轮转
├── integrate_lock.py                     # 集成锁
├── patch_prompt.py                       # 补丁提示词
├── register_tool.py                      # 注册工具
├── write_10_plans.py                     # 写10个计划
└── 网友成熟方案收藏/                      # 从网友那里收集的成熟方案
    ├── README_索引.md
    ├── 001_实战踩坑血泪史_深度定制版.md
    ├── 002_本地部署全攻略_深度定制版.md
    ├── 003_掘金部署问题_深度定制版.md
    ├── 004_工具调用格式错误_深度定制版.md
    ├── 005_API连接问题_深度定制版.md
    ├── 006_Playwright浏览器配置_深度定制版.md
    ├── 007_架构深度剖析_深度定制版.md
    ├── 008_LLM集成最佳实践_深度定制版.md
    ├── 009_工具调用系统开发指南_深度定制版.md
    ├── 010_Windows安装指南_深度定制版.md
    ├── 10方案可行性检查与改造汇总_20260906.md
    ├── 三标签优化版/                    # 针对3标签的优化方案
    └── 方案执行报告/                    # 方案执行报告
```

### 📊 evaluation/ - 评测套件

| 文件 | 说明 |
|------|------|
| golden_tasks.json | 黄金测试任务集 |
| run_evaluation.py | 评测运行脚本 |
| README.md | 评测说明 |

### 🔌 protocol/ - 协议实现

```
protocol/
└── a2a/                   # Agent-to-Agent协议
    └── app/
        ├── README.md
        ├── agent.py
        ├── agent_executor.py
        └── main.py
```

## 三、统帅提示词10章速览

`app/prompt/manus.py` 是统帅的灵魂，包含10章：

| 章节 | 内容 | 来源 |
|------|------|------|
| 一、角色与核心循环 | 6步Agent循环、KV缓存优化、todo.md、错误现场保留 | 核心设计 |
| 二、工具与执行规范 | Shell/编码/文件规则、工具使用反例 | 核心设计 |
| 三、浏览器与信息检索 | 浏览器工具使用、恢复循环、无进度检测 | 核心设计 |
| 四、通信与错误处理 | 消息工具、错误处理流程 | 核心设计 |
| 五、三标签与多模型分工 | 智谱/硅基/3标签分工、模型分级调用 | 定制功能 |
| 六、监控与日志 | 状态更新、API用量告警、异步铁律 | 定制功能 |
| 七、自我学习与进化 | 持久记忆、技能沉淀、日报式复盘 | 定制功能 |
| 八、跑批标准流程 | 5步跑批流程、3标签使用细节、验收标准 | 业务定制 |
| 九、思维链经验 | 6大思维模式（需求分析/任务拆解/决策判断/错误处理/回复组织/思维纪律） | DeepSeek 3673条蒸馏 |
| 十、知识库检索 | 完整知识库使用方法、检索命令 | DeepSeek 3673条本体 |

## 四、自动生成的目录（不要手动修改）

| 目录 | 内容 | 何时生成 |
|------|------|---------|
| logs/ | 运行日志 | 每次运行自动生成 |
| memory/ | 持久记忆 | 学习到新经验时自动生成 |
| workspace/ | 工作空间 | 执行任务时自动生成 |
| .learnings/ | 错误和经验记录 | 遇到错误时自动生成 |
| chatsHistory/ | 聊天历史 | 每次对话自动保存 |

## 五、快速定位

| 我想... | 去哪里 |
|---------|--------|
| 快速启动 | 看 [MAC_QUICKSTART.md](MAC_QUICKSTART.md) |
| 了解项目全貌 | 看本文档 |
| 深入学习使用 | 看 [USAGE_GUIDE.md](USAGE_GUIDE.md) |
| 遇到问题排查 | 看 [DEBUG_GUIDE.md](DEBUG_GUIDE.md) |
| Mac优化 | 看 [MAC_SOFTWARE_OPTIMIZATION.md](MAC_SOFTWARE_OPTIMIZATION.md) |
| 修改统帅行为 | 改 `app/prompt/manus.py` |
| 添加新工具 | 在 `app/tool/` 下添加，然后在 `app/tool/tool_collection.py` 注册 |
| 配置API | 改 `config/config.toml` |
| 查看思考经验 | 用 `knowledge_base/deepseek_thinking/search.py` 检索 |
| 查看调试方案 | 看 `training_logs/` 目录 |
