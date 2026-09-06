# 方案6：OpenManus项目中Playwright浏览器自动化环境配置全攻略（深度定制版）

> 来源：https://blog.csdn.net/gitblog_01422/article/details/150380796
> 深度定制时间：2026-09-05
> 定制原则：只做加法，不做减法，吸收每个方案的优点到我们的系统中


## 【我们的现有情况·深度定制基础】

### 已有资产
- OpenManus统帅：已安装，路径 D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus
- 三个标签Chrome（端口9333）：豆包、千问国际版、智谱，multi_bridge.py常驻
- 跑批脚本：三个标签\半个智能体代码库\执行层\run_chN_4api.py
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


---


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


---


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
