# 方案10：Run OpenManus on Windows: 2026 Installation Guide（深度定制版）

> 来源：https://codersera.com/blog/run-open-manus-on-windows-installation-guide/
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


---


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
