# -*- coding: utf-8 -*-
"""批量写入10个OpenManus成熟方案+深度定制"""
import os

BASE = r"D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus\training_logs\网友成熟方案收藏"

# 我们的现有情况（深度定制的基础）
OUR_CONTEXT = """
## 【我们的现有情况·深度定制基础】

### 已有资产
- OpenManus统帅：已安装，路径 D:\\360Downloads\\金庸\\一念永恒\\一念永恒小说\\开源拉取\\OpenManus
- 三个标签Chrome（端口9333）：豆包、千问国际版、智谱，multi_bridge.py常驻
- 跑批脚本：三个标签\\半个智能体代码库\\执行层\\run_chN_4api.py
- 飞书控制：应用"统帅"（收消息）+ "最强大脑"（发消息），feishu_relay_v1.py中转
- 谷歌中转API：三模型轮转（2.5-flash-lite 1000次/天、3.5-flash 200次/天、2.5-pro 100次/天）
- 智谱4.5-air：1200万收费额度
- 智谱4.0 (glm-4-flash)：免费
- 硅基9B (GLM-4-9B)：免费
- DeepSeek网页中转API：可用
- 28个自定义工具：batch_run、status_monitor、usage_monitor、notify_feishu、python_execute等

### 已修复的问题
- batch_run工具异步子进程+实时日志+心跳
- 模型轮转（ask_tool和ask_with_images都已支持）
- LLM API超时保护（120秒）
- notify_feishu异步化
- python_execute用subprocess重构
- base.py添加step_timeout=120秒
- config.toml BOM修复，max_tokens=4096，temperature=0.0
- 跑批脚本章节号查找支持两位数格式

### 核心目标
- 统帅能独立完成金庸小说跑批任务
- 通过飞书远程控制与监控
- MainAgent只做监督+改代码，不直接操作
- 实时日志驱动调试法

### 深度定制原则
- 只做加法，不做减法
- 每个方案的优点都吸收到我们的系统中
- 优先使用网友成熟方案，不自己从零写代码
"""

plans = [
    {
        "file": "001_实战踩坑血泪史_深度定制版.md",
        "title": "方案1：【实战踩坑】我的OpenManus使用血泪史（深度定制版）",
        "source": "https://blog.csdn.net/m0_73753352/article/details/146126584",
        "original": """
## 原始方案核心内容

### 一、执行流程中添加循环检测
- actions_history记录每一步的action
- is_in_loop判断：连续2次相同action判定为循环
- 检测到循环时添加特殊提示重新规划

### 二、常见踩坑点
1. 工具调用参数格式错误：LLM返回的JSON参数不符合工具schema
2. 无限循环：LLM反复调用同一个工具
3. 上下文过长：消息历史超过模型上下文窗口
4. 工具执行超时：工具执行时间过长导致整个任务卡住
5. 模型返回空内容：LLM没有返回任何tool_calls也没有content

### 三、解决方案
- 循环检测阈值设为2（duplicate_threshold=2）
- handle_stuck_state方法创建stuck_prompt鼓励改变策略
- 工具参数验证：执行前先验证参数是否符合schema
- 工具执行超时保护：每个工具单独设置超时
- 上下文滑动窗口：保留最近100条消息
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- base.py已有is_stuck方法（duplicate_threshold=2）和handle_stuck_state方法
- toolcall.py已有工具级超时保护（60秒）
- 消息滑动窗口：OpenManus原生保留最近100条消息

### 需要增加的（加法）
1. **actions_history增强**：在toolcall.py的think方法中记录每一步的完整action（工具名+参数+返回摘要），写入实时日志
2. **循环检测升级**：不仅检测完全相同的action，还要检测"语义相似"的action（如反复调用status_monitor但参数略有不同）
3. **工具参数预验证**：在execute_tool执行前，先用jsonschema验证参数，不符合时返回明确的错误信息让LLM修正
4. **stuck_prompt个性化**：根据我们的跑批任务场景，定制stuck_prompt，明确告诉统帅"跑批任务必须先调用batch_run工具"
5. **循环自愈**：检测到循环后，不仅添加提示，还要自动跳过当前步骤，直接进入下一步规划

### 具体修改点
- app/agent/toolcall.py：think方法添加actions_history记录
- app/agent/base.py：is_stuck方法升级为语义相似检测
- app/agent/toolcall.py：execute_tool添加参数预验证
- app/prompt/manus.py：stuck_prompt添加跑批任务专属提示
"""
    },
    {
        "file": "002_本地部署全攻略_深度定制版.md",
        "title": "方案2：OpenManus本地部署全攻略（深度定制版）",
        "source": "https://blog.csdn.net/tt34567/article/details/152113214",
        "original": """
## 原始方案核心内容

### 一、环境准备
- Python 3.12+
- uv包管理器（比pip快5-10倍）
- Git
- Playwright浏览器

### 二、安装步骤
1. git clone https://github.com/FoundationAgents/OpenManus.git
2. uv venv --python 3.12
3. uv pip install -r requirements.txt
4. playwright install chromium
5. copy config/config.example.toml config/config.toml

### 三、配置要点
- model选择：Claude 3.7 Sonnet（默认）、GPT-4o、DeepSeek、Ollama本地模型
- base_url必须以/v1结尾（OpenAI兼容）或/v1/（Anthropic）
- max_tokens建议4096
- temperature建议0.0（任务执行）或0.7（创意）

### 四、常见问题
- Python版本不对：必须3.12+，3.9会导入失败
- config.py.example不存在：现在是config/config.toml
- Playwright浏览器未安装：playwright install chromium
- API key在curl能用但OpenManus不能用：base_url结尾问题
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- 已安装Python 3.12.9，uv虚拟环境
- Playwright已安装
- config.toml已配置谷歌中转API

### 需要增加的（加法）
1. **部署脚本固化**：写一个deploy_openmanus.py脚本，一键完成所有部署步骤（包括我们的自定义工具复制、配置文件生成）
2. **配置模板化**：创建config.template.toml，包含我们所有的自定义配置（模型轮转、工具路径、飞书webhook等），新部署时只需填API key
3. **环境检查脚本**：启动前自动检查Python版本、依赖安装、Playwright浏览器、API key有效性、三个标签Chrome是否在线
4. **多环境支持**：支持开发环境（本地调试）和生产环境（另一台电脑部署），通过环境变量切换
5. **自动更新机制**：从Git拉取最新代码后，自动迁移自定义工具和配置

### 具体修改点
- 新建 scripts/deploy_openmanus.py：一键部署脚本
- 新建 config/config.template.toml：配置模板
- 新建 scripts/env_check.py：环境检查脚本
- 新建 scripts/auto_update.py：自动更新脚本
"""
    },
    {
        "file": "003_掘金部署问题_深度定制版.md",
        "title": "方案3：尝试部署OpenManus以及遇到的问题（深度定制版）",
        "source": "https://juejin.cn/post/7481584094113185792",
        "original": """
## 原始方案核心内容

### 一、遇到的主要问题
1. MCP服务器配置错误导致启动失败
2. 浏览器自动化权限问题（Windows上）
3. 模型API连接超时
4. 工具调用返回结果过大导致上下文溢出
5. 异步编程错误：在async函数中调用同步函数

### 二、解决方案
- MCP服务器配置：先禁用所有MCP，逐个启用排查
- Windows权限：以管理员身份运行PowerShell，或将项目移出OneDrive同步文件夹
- API超时：增加httpx.Timeout配置，添加重试机制
- 结果截断：max_observe参数限制工具返回结果长度
- 异步错误：所有外部调用必须用await，同步函数用asyncio.to_thread包装

### 三、关键经验
- 先跑通最小配置（只有terminate工具），再逐个添加工具
- 每个工具添加后单独测试，不要一次性加所有工具
- 日志级别设为DEBUG，方便排查问题
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- 已禁用filesystem MCP（mcp.json为空）
- notify_feishu已用asyncio.to_thread包装
- LLM API已添加httpx.Timeout和重试
- 项目在D盘，不在OneDrive

### 需要增加的（加法）
1. **工具逐个测试脚本**：写一个test_tools.py脚本，逐个测试每个自定义工具，输出测试报告
2. **MCP安全启动**：启动时先检查mcp.json，如果有配置则先测试连接，连接失败自动禁用并记录日志
3. **结果智能截断**：不是简单截断，而是根据工具类型智能截断（如batch_run只返回进度摘要，status_monitor返回完整状态）
4. **异步错误检测**：在代码中添加静态检查，确保没有在async函数中调用同步阻塞函数
5. **最小配置启动模式**：支持--minimal参数启动，只加载核心工具（terminate、status_monitor），用于快速排查问题

### 具体修改点
- 新建 scripts/test_tools.py：工具逐个测试脚本
- app/agent/manus.py：添加--minimal启动模式
- app/agent/toolcall.py：结果智能截断
- 新建 scripts/async_check.py：异步错误静态检查
"""
    },
    {
        "file": "004_工具调用格式错误_深度定制版.md",
        "title": "方案4：OpenManus工具调用消息格式错误全解析（深度定制版）",
        "source": "https://blog.csdn.net/gitblog_01406/article/details/150380750",
        "original": """
## 原始方案核心内容

### 一、工具调用格式错误的常见类型
1. tool_calls为None但content也为空
2. tool_calls中的function.name不存在
3. function.arguments不是合法JSON
4. 参数类型错误（如应该传int但传了str）
5. 缺少必填参数

### 二、根本原因
- 模型对工具schema理解不准确
- 系统提示词没有明确说明工具调用格式
- 上下文过长导致模型"忘记"工具格式
- 模型本身工具调用能力不足（小模型尤其明显）

### 三、解决方案
1. 系统提示词中明确说明工具调用格式和示例
2. 工具description写得非常详细，包含参数说明和使用示例
3. 错误处理：格式错误时返回明确的错误信息，让模型修正
4. 降级策略：连续3次格式错误后，切换到更强大的模型
5. 工具调用示例：在系统提示词中加入1-2个完整的工具调用示例
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- toolcall.py的think方法已有tool_calls计数和格式验证
- 每个工具都有name、description、parameters

### 需要增加的（加法）
1. **工具调用示例注入**：在系统提示词中为每个关键工具（batch_run、status_monitor、notify_feishu）添加完整的调用示例
2. **错误反馈增强**：格式错误时，不仅返回"参数错误"，还要返回"正确的参数应该是什么样的"示例
3. **模型自动降级**：连续2次工具调用格式错误，自动切换到更强大的模型（如从2.5-flash-lite切换到2.5-pro）
4. **工具schema优化**：每个工具的parameters添加"description"字段，说明每个参数的含义和取值范围
5. **批量工具调用提示**：明确告诉模型"可以一次调用多个工具"，减少调用次数

### 具体修改点
- app/prompt/manus.py：添加工具调用示例
- app/agent/toolcall.py：错误反馈增强，添加模型自动降级
- 所有自定义工具：parameters添加description字段
"""
    },
    {
        "file": "005_API连接问题_深度定制版.md",
        "title": "方案5：OpenManus项目中API连接问题的终极指南（深度定制版）",
        "source": "https://blog.csdn.net/gitblog_01414/article/details/150381062",
        "original": """
## 原始方案核心内容

### 一、API连接问题分类
1. 认证错误（401）：API key无效或过期
2. 速率限制（429）：调用频率超限
3. 超时错误：网络不稳定或API响应慢
4. 服务器错误（500/502/503）：API服务端问题
5. 连接错误：网络不通或DNS解析失败

### 二、解决方案
- 认证错误：立即终止任务，告警通知
- 速率限制：指数退避重试，最多6次
- 超时错误：延长超时时间，重试3次
- 服务器错误：固定间隔重试3次
- 连接错误：检查网络，切换备用API

### 三、多API容错架构
- 主API + 备用API配置
- 主API失败时自动切换到备用API
- API健康检查：定期测试API可用性
- 调用统计：记录每个API的成功率和响应时间
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- LLM API已添加httpx.Timeout（connect=10s, read=60s）和max_retries=2
- 模型轮转已支持日限额保护
- 谷歌中转有三个模型可轮转

### 需要增加的（加法）
1. **多API容错架构**：配置主API（谷歌中转）+ 备用API（智谱4.5-air），主API连续失败3次自动切换
2. **API健康检查脚本**：每5分钟测试所有API的可用性，写入api_health.json
3. **错误类型分级处理**：
   - 401认证错误：立即通知飞书，暂停任务
   - 429速率限制：自动切换到下一个模型，等待30秒
   - 超时：重试3次，每次延长超时（60s→120s→180s）
   - 500/502/503：固定间隔重试3次
   - 连接错误：检查网络，切换备用API
4. **API调用统计面板**：在任务看板显示每个API的调用次数、成功率、平均响应时间
5. **API配额预警**：谷歌中转达到900次（90%）时飞书通知，智谱4.5-air达到1000万额度时通知

### 具体修改点
- app/llm.py：添加多API容错切换逻辑
- 新建 scripts/api_health_check.py：API健康检查
- app/tool/usage_monitor_tool.py：添加API调用统计
- app/tool/notify_feishu_tool.py：添加API配额预警
"""
    },
    {
        "file": "006_Playwright浏览器配置_深度定制版.md",
        "title": "方案6：OpenManus项目中Playwright浏览器自动化环境配置全攻略（深度定制版）",
        "source": "https://blog.csdn.net/gitblog_01422/article/details/150380796",
        "original": """
## 原始方案核心内容

### 一、Playwright配置要点
1. headless模式：生产环境用headless=true，调试用headless=false
2. 视口大小：默认1280x720，可根据需要调整
3. 超时配置：navigation_timeout=30000，action_timeout=10000
4. 浏览器上下文：持久化上下文保存登录态
5. 反检测：添加user-agent、禁用webdriver标志

### 二、常见问题
1. 页面加载超时：增加navigation_timeout
2. 元素找不到：使用wait_for_selector，增加超时
3. 登录态丢失：使用persistent_context保存cookies
4. 被网站检测为机器人：添加反检测措施
5. 多标签页冲突：每个任务用独立的browser_context

### 三、最佳实践
- 浏览器实例复用：不要每次都启动新浏览器
- 页面操作后等待：wait_for_load_state('networkidle')
- 错误截图：失败时自动截图保存
- 日志记录：记录每个页面操作
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- 三个标签Chrome使用独立端口9333，持久化登录态
- multi_bridge.py桥接服务常驻

### 需要增加的（加法）
1. **OpenManus浏览器与三个标签Chrome分离**：OpenManus自己的浏览器（Playwright）用于联网搜索和一般浏览，三个标签Chrome（端口9333）专用于深度思考，互不干扰
2. **OpenManus浏览器持久化上下文**：保存登录态（如GitHub、飞书开发者平台），避免每次重新登录
3. **浏览器健康监控**：定期检查OpenManus浏览器和三个标签Chrome的状态，崩溃时自动重启
4. **反检测增强**：OpenManus浏览器添加user-agent伪装、禁用webdriver标志、模拟人类操作延迟
5. **失败自动截图**：浏览器操作失败时自动截图保存到logs/browser_screenshots/，方便排查
6. **三个标签Chrome防风控**：
   - 必须从历史对话拉取聊天，不新建对话框
   - 每个对话使用次数登记（10-40次轮换）
   - 操作间隔随机化（2-5秒）
   - 模拟人类输入（逐字输入而非一次性粘贴）

### 具体修改点
- 新建 scripts/browser_health_monitor.py：浏览器健康监控
- app/tool/browser_tool.py（如有）：添加持久化上下文和反检测
- 三个标签/半个智能体代码库/执行层/run_chN_4api.py：增强防风控
"""
    },
    {
        "file": "007_架构深度剖析_深度定制版.md",
        "title": "方案7：OpenManus: Deep Dive into the Open-Source AI Agent Framework（深度定制版）",
        "source": "https://enricopiovano.com/blog/openmanus-open-source-ai-agent-framework/",
        "original": """
## 原始方案核心内容

### 一、Agent状态机
- 四个状态：idle（就绪）→ running（运行中）→ finished（完成）→ error（错误）
- 状态转换通过context manager确保一致性
- 异常时短暂进入error状态，然后恢复到之前的状态

### 二、ReAct模式
- Think（思考）：LLM决定下一步动作
- Act（行动）：执行工具调用
- 交替进行，直到任务完成

### 三、分层Agent设计
- BaseAgent：基础抽象，管理状态、步骤、内存
- ReActAgent：添加think-act循环
- ToolCallAgent：实现工具调用
- ManusAgent：通用智能体，配备Python执行、搜索、浏览器、文件操作

### 四、记忆管理
- 滑动窗口：保留最近100条消息
- 工具结果集成：统一格式转换

### 五、Flow编排
- PlanningFlow：先分解任务为计划，再逐步执行
- 进度跟踪：每个步骤有状态（not_started/in_progress/completed/blocked）

### 六、卡住检测与恢复
- 监控最近助手消息的重复性
- 连续2次相同判定为卡住
- 干预：修改next_prompt鼓励改变策略
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- 状态机：OpenManus原生实现
- ReAct模式：原生实现
- 滑动窗口：原生100条消息
- 卡住检测：base.py已有is_stuck和handle_stuck_state

### 需要增加的（加法）
1. **状态持久化**：将Agent状态（idle/running/finished/error）写入logs/agent_state.json，即使进程崩溃也能恢复
2. **自定义ManusAgent**：继承ToolCallAgent，添加我们的专属能力：
   - 跑批任务专用流程（先status_monitor→再batch_run→再监控进度→最后notify_feishu）
   - 三个标签深度思考调用（ask_tag_3labels工具）
   - 飞书通知自动触发（任务开始/完成/失败时）
3. **记忆增强**：
   - 任务摘要：每完成5步，自动生成任务摘要，替换早期消息
   - 关键信息提取：从工具结果中提取关键信息，只保留关键信息到记忆
4. **PlanningFlow应用**：对于复杂任务（如"优化所有脚本"），先使用PlanningFlow分解为子任务，再逐个执行
5. **卡住恢复升级**：
   - 第1次卡住：添加stuck_prompt
   - 第2次卡住：自动切换到更强大的模型
   - 第3次卡住：通知飞书，请求人工干预
6. **状态监控API**：提供HTTP接口查询当前Agent状态，供任务看板调用

### 具体修改点
- app/agent/manus.py：自定义ManusAgent，添加跑批专用流程
- 新建 app/memory/enhanced_memory.py：记忆增强
- 新建 app/flow/batch_flow.py：跑批专用Flow
- app/agent/base.py：卡住恢复升级
"""
    },
    {
        "file": "008_LLM集成最佳实践_深度定制版.md",
        "title": "方案8：OpenManus LLM集成最佳实践：多模型适配与性能优化（深度定制版）",
        "source": "https://adg.csdn.net/6970911d437a6b40336abf84.html",
        "original": """
## 原始方案核心内容

### 一、多模型适配策略
- 配置驱动：TOML配置文件支持多模型
- 单例模式：每个模型配置只创建一个客户端实例
- 动态客户端创建：根据api_type自动初始化对应客户端
- 统一消息格式化：支持文本、图像多模态

### 二、Token优化五大策略
1. 消息压缩与摘要：长对话历史压缩
2. 动态上下文窗口：根据模型能力调整
3. 增量对话模式：只传递新增内容
4. 优先级导向内容截断：按关键词重要性保留
5. 结构化数据压缩：非结构化转结构化

### 三、错误处理与重试
- 速率限制：指数退避+延长等待，重试6次
- 认证错误：立即终止+告警
- API错误：固定间隔重试3次
- Token超限：内容压缩+重试
- 超时：延长超时+重试3次

### 四、性能调优参数
- temperature：0.0（任务）/0.7（创意）
- max_tokens：1024-4096
- stream：流式响应
- tool_choice：auto/required/none
- response_format：json_object
- seed：可复现结果
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- 模型轮转：三模型轮转[0,0,0,1,0,0,0,2]
- 日限额保护：每个模型有每日上限
- LLM API超时：httpx.Timeout + asyncio.wait_for 120秒
- max_tokens=4096，temperature=0.0

### 需要增加的（加法）
1. **任务级模型选择**：根据任务复杂度自动选择模型：
   - 简单任务（状态查询、通知）：2.5-flash-lite
   - 中等任务（代码修改、数据分析）：3.5-flash
   - 复杂任务（架构设计、问题诊断）：2.5-pro
   - 超复杂任务（需要深度思考）：调用三个标签
2. **Token智能优化**：
   - 工具结果自动摘要：超过500字的工具结果，先用智谱4.0免费API摘要后再存入记忆
   - 历史消息压缩：每10步自动压缩早期消息
   - 系统提示词优化：去除冗余内容，只保留核心规则
3. **智谱4.5-air作为备用大脑**：谷歌中转全部达到日限额时，自动切换到智谱4.5-air
4. **硅基9B作为粗活专用**：日志摘要、数据搬运、格式整理等粗活，用硅基9B免费API
5. **模型性能监控**：记录每个模型的响应时间、成功率、Token消耗，定期生成报告
6. **流式响应**：启用stream模式，减少感知延迟（如果OpenManus支持）

### 具体修改点
- app/llm.py：任务级模型选择逻辑
- 新建 app/memory/token_optimizer.py：Token智能优化
- app/llm.py：智谱4.5-air备用大脑切换
- 新建 scripts/model_performance_report.py：模型性能监控
"""
    },
    {
        "file": "009_工具调用系统开发指南_深度定制版.md",
        "title": "方案9：工具调用系统开发指南：OpenManus硅基流动API全链路实战（深度定制版）",
        "source": "https://blog.csdn.net/gitblog_01425/article/details/150262406",
        "original": """
## 原始方案核心内容

### 一、ToolCallAgent核心
- 继承ReActAgent，专注工具调用
- 工具选择策略：AUTO/NONE/REQUIRED
- max_steps限制最大执行步骤

### 二、BaseTool抽象基类
- 统一接口：name、description、parameters、execute
- Pydantic类型验证
- 支持同步和异步执行

### 三、PlanningFlow规划式流程
- 先分解任务为计划
- 步骤状态跟踪：not_started/in_progress/completed/blocked
- 可视化流程状态

### 四、工具设计最佳实践
1. 单一职责：每个工具只做一件事
2. 参数验证：Pydantic严格验证
3. 错误处理：详细错误信息
4. 结果标准化：统一结果格式
5. 资源管理：正确释放资源

### 五、性能优化
1. 工具缓存：相同输入缓存结果
2. 异步并发：并行调用独立工具
3. 步骤合并：减少不必要的工具调用
4. 结果分页：大型结果分页
5. 模型选择：根据任务复杂度选模型
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- 28个自定义工具，都继承BaseTool
- batch_run、status_monitor、usage_monitor、notify_feishu等核心工具

### 需要增加的（加法）
1. **工具分类体系**：将28个工具分为4类：
   - 核心工具（必须加载）：terminate、status_monitor、batch_run
   - 监控工具：usage_monitor、log_viewer、api_health
   - 执行工具：python_execute、file_editor、browser_search
   - 通知工具：notify_feishu、notify_dingtalk
2. **工具缓存机制**：
   - status_monitor：缓存5秒（避免频繁调用）
   - usage_monitor：缓存60秒
   - api_health：缓存5分钟
3. **工具结果标准化**：所有工具返回统一格式{ok: bool, summary: str, details: dict, error: str}
4. **工具依赖管理**：工具之间有依赖关系时（如batch_run依赖status_monitor），自动确保依赖工具先执行
5. **工具使用统计**：记录每个工具的调用次数、成功率、平均执行时间，定期优化
6. **自定义工具热加载**：修改工具代码后，不需要重启OpenManus，自动重新加载
7. **PlanningFlow应用到跑批**：跑批任务先分解为"准备→执行→监控→完成"四个阶段

### 具体修改点
- 新建 app/tool/tool_registry.py：工具分类和注册管理
- app/tool/base_tool.py：添加缓存机制和结果标准化
- 新建 app/flow/batch_planning_flow.py：跑批专用PlanningFlow
- 新建 scripts/tool_usage_stats.py：工具使用统计
"""
    },
    {
        "file": "010_Windows安装指南_深度定制版.md",
        "title": "方案10：Run OpenManus on Windows: 2026 Installation Guide（深度定制版）",
        "source": "https://codersera.com/blog/run-open-manus-on-windows-installation-guide/",
        "original": """
## 原始方案核心内容

### 一、系统要求
- Windows 10 22H2或Windows 11
- Python 3.12+
- 16GB RAM（云端LLM）/32GB（本地模型）
- 3GB磁盘（venv+Playwright）

### 二、安装方法
- Method A: uv（推荐，快5-10倍）
- Method B: Miniconda/Anaconda

### 三、模型选择
- Claude 3.7 Sonnet（默认，最可靠）
- GPT-4o（工具调用可靠）
- DeepSeek V3.2（最便宜）
- Ollama本地模型（Qwen 3.5-Coder 32B最佳）

### 四、常见坑
- Python 3.9环境导入失败
- config.py.example不存在（现在是config/config.toml）
- Playwright浏览器未安装
- API key在curl能用但OpenManus不能用（base_url结尾）
- Windows浏览器沙箱权限问题
- agent卡住刷新页面（调试时设headless=false）

### 五、成本估算
- 典型多步网页研究任务：30-80k输入token，5-15k输出token
- Claude 3.7 Sonnet：$0.10-0.40
- GPT-4o：$0.05-0.20
- DeepSeek：<$0.02
""",
        "customization": """
## 【深度定制·适配我们的系统】

### 我们已有的对应实现
- Windows 11，Python 3.12.9
- uv虚拟环境
- 谷歌中转API（免费额度）

### 需要增加的（加法）
1. **另一台电脑部署准备**：
   - 写一个完整的部署指南（针对Mac/Windows）
   - 打包所有自定义工具和配置为一个zip
   - 一键部署脚本（install_on_new_machine.py）
   - 数据迁移脚本（把跑批结果、日志、配置迁移到新机器）
2. **跨平台兼容性**：
   - 所有路径使用os.path.join，不硬编码Windows路径
   - 路径配置集中到config.toml的[paths] section
   - 测试在Mac/Linux上的兼容性
3. **资源监控**：
   - 监控CPU、内存、磁盘使用率
   - 超过阈值时飞书通知
   - 自动清理旧日志（7天前的日志自动删除）
4. **启动器优化**：
   - 写一个start_openmanus.bat（Windows）和start_openmanus.sh（Mac/Linux）
   - 启动前自动检查环境
   - 启动后自动打开飞书通知"统帅已启动"
5. **成本控制**：
   - 我们使用免费API，成本为0
   - 但要记录每次任务的Token消耗，估算如果用付费API的成本
   - 优化工具调用次数，减少Token消耗
6. **无头模式默认**：生产环境默认headless=true，只有调试时才设为false

### 具体修改点
- 新建 scripts/install_on_new_machine.py：一键部署脚本
- 新建 scripts/data_migration.py：数据迁移
- config.toml：添加[paths] section，集中路径配置
- 新建 start_openmanus.bat / start_openmanus.sh：启动器
- 新建 scripts/resource_monitor.py：资源监控
"""
    }
]

# 写入每个方案
for plan in plans:
    filepath = os.path.join(BASE, plan["file"])
    content = f"""# {plan['title']}

> 来源：{plan['source']}
> 深度定制时间：2026-09-05
> 定制原则：只做加法，不做减法，吸收每个方案的优点到我们的系统中

{OUR_CONTEXT}

---

{plan['original']}

---

{plan['customization']}

---

## 【执行优先级】

### 立即执行（P0）
- [ ] 从本方案中提取最关键的1-2个改进点
- [ ] 修改对应代码文件
- [ ] 语法验证
- [ ] 测试验证

### 后续执行（P1）
- [ ] 其余改进点按优先级逐步实施
- [ ] 每个改进点实施后记录到训练日志

### 验证标准
- 代码语法正确
- 不破坏现有功能
- 改进点有明确的测试用例
- 测试通过后记录到002_完整版调试方案.md
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已写入: {plan['file']} ({len(content)} bytes)")

print(f"\n共写入 {len(plans)} 个方案到 {BASE}")
