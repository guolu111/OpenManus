# 方案10：Run OpenManus on Windows: 2026 Installation Guide（三标签深度优化版）

> 来源：https://codersera.com/blog/run-open-manus-on-windows-installation-guide/
> 深度定制时间：2026-09-05
> 三标签优化时间：2026-09-06
> 优化标签：豆包（第1部分）、千问国际版（第2部分）、智谱清言（第3部分，因HTTP 500未完成，使用前两标签建议汇总）
> 定制原则：只做加法，不做减法，吸收每个方案的优点到我们的系统中


## 【我们的现有情况·深度定制基础】

### 已有资产
- OpenManus统帅：已安装，路径 D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus
- 三个标签Chrome（端口9333）：豆包、千问国际版、智谱，multi_bridge.py常驻（端口8010）
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


## 【三标签深度优化·新增改进建议】

### 豆包的改进建议（第1部分，5条）

#### 建议1：编写旧Windows17763专属环境兼容清单 + 一键环境校验BAT
- **问题**：原始文档只覆盖纯API部署流程，没有内置对接本地multi_bridge.py(8010端口)三Chrome标签网页中转集群的一键配置脚本；缺少一套完整环境自检批处理脚本，无法一键校验Python双版本、端口占用、浏览器实例、依赖包、配置文件合法性，故障排查全靠人工逐行核对。
- **具体修改**：
  - 在项目根目录新建脚本 `env_check.bat`
  - 在README补充 `win10_17763_requirements.txt` 锁定兼容依赖版本，不改动原有uv/conda部署文档
- **验证方式**：双击运行bat脚本，正常环境输出全部ok；手动关闭multi_bridge服务，脚本标记异常并写入日志。
- **优先级**：P0（立即）

#### 建议2：增加网页桥接模式一键配置模板，对接8010 multi_bridge服务
- **改进点**：在config模板目录新增 `config_chrome_bridge.toml` 预制配置文件，原生支持 api_type=chrome_bridge，省去手动填写桥接地址，一键切换网页三标签模型池。
- **路径**：`config/config_chrome_bridge.toml`
- **预设**：bridge地址 http://127.0.0.1:8010，预注册豆包、千问国际版、智谱三个网页模型；增加注释说明和切换方式
- **验证方式**：该文件为正式config.toml，发起一次LLM请求，确认请求转发到multi_bridge端口。

#### 建议3：编写进程自愈批处理，浏览器/桥接进程异常自动重启
- **改进点**：针对Playwright、Chrome调试标签、multi_bridge常驻进程，增加监控重启脚本；进程退出时自动调用notify_feishu推送重启告警，适配无人值守金庸跑批。
- **新增守护脚本**：`daemon_watchdog.bat`
- **增加逻辑**：检测chrome、multi_bridge.py存活状态；进程消失自动拉起；执行状态写入运行日志
- **验证方式**：手动结束Chrome进程，观察看门狗脚本自动重启浏览器桥接并推送飞书消息。
- **优先级**：P1（近期）

#### 建议4：本地化配额成本统计模块，适配自有全部模型资源池
- **改进点**：在usage_monitor工具内部新增自定义记账规则，区分免费额度、按token计费、网页桥接零消耗三类资源；输出自定义跑批成本报表，替代原版海外模型成本估算表。
- **文件路径**：`app/tool/usage_monitor.py`
- **新增配额配置字典**：谷歌每日限额、智谱计费余额、免费模型不计费；每次调用记录消耗台账保存至 `./quota_log/quota_record.csv`
- **验证方式**：执行多轮不同模型调用，打开csv台账核对每一条调用的资源消耗分类。

#### 建议5：增加一键重置调试环境脚本，快速清理异常缓存快照
- **改进点**：新增 `reset_debug.bat`，一键清理旧agent快照、tool缓存、流式日志，保留配置文件不变；调试卡死场景快速重置环境，不需要手动删除文件夹。
- **根目录新增**：`reset_debug.bat`，仅清空run_cache、run_log、tool_cache三个缓存目录
- **验证方式**：运行脚本后缓存目录清空，config.toml文件完整保留不被删除。
- **优先级**：P2（远期）

#### 豆包认为最有价值的部分
- uv与Anaconda两套可选部署流程，方便我们在双Python环境之间灵活切换
- 完整汇总Windows平台高频踩坑清单（base_url后缀、Playwright缺失、浏览器沙箱权限、配置文件名变更），提前规避部署故障
- 区分云端LLM与本地Ollama两套硬件资源标准，给我们本地轻量化部署硅基9B模型提供硬件评估依据
- 提供Token量级与费用估算方法论，可以迁移改造为我们专属的配额监控记账体系，支撑大批量无人值守小说跑批任务成本管控


### 千问国际版的改进建议（第2部分，5条）

#### 建议1：零环境引导部署（Bootstrap机制）
- **问题**：一键部署脚本的"先有鸡还是先有蛋"悖论。原方案提出用Python写install_on_new_machine.py来部署，但如果目标新电脑连Python和uv都没有，这个Python脚本根本无法运行。
- **改进点**：解决目标机器无Python环境时，部署脚本无法运行的问题，实现真正的"开箱即用"。
- **具体实现**：`bootstrap_win.bat` 核心逻辑
  ```bat
  @echo off
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  call uv python install 3.12.9
  call uv venv --python 3.12.9 .venv
  call .venv\Scripts\activate.bat
  call uv pip install -r requirements.txt
  echo [4/4] 运行深度定制部署脚本...
  python scripts/install_on_new_machine.py
  ```
- **优先级**：P0（立即）

#### 建议2：全局路径"去硬编码化"的自动化扫描与修复工具
- **问题**：跨平台路径配置的"硬编码残留"风险。原方案仅提出在config.toml中集中配置路径，但我们现有的28个自定义工具、跑批脚本（run_chN_4api.py）甚至OpenManus源码中，极大概率已经硬编码了 D:\360Downloads\... 这样的绝对路径。仅改配置文件无法解决代码深处的硬编码问题。
- **改进点**：彻底解决历史代码中硬编码的 D:\360Downloads\... 路径问题，确保跨平台兼容性真正落地。
- **具体修改**：新建 `scripts/path_refactor_scanner.py`。该脚本扫描项目中所有 .py、.toml、.json 文件，使用正则匹配硬编码路径，并生成修复报告或自动替换为相对路径/配置读取。
  ```python
  import os, re
  from pathlib import Path
  HARD_CODED_PATTERN = re.compile(r'[Dd]:\\360Downloads|D:/360Downloads')
  def scan_and_report(root_dir):
      hits = []
      for root, _, files in os.walk(root_dir):
          if '.venv' in root or '__pycache__' in root: continue
          for file in files:
              if file.endswith(('.py', '.toml', '.json')):
                  filepath = os.path.join(root, file)
                  with open(filepath, 'r', encoding='utf-8') as f:
                      content = f.read()
                  if HARD_CODED_PATTERN.search(content):
                      hits.append(filepath)
      return hits
  ```
- **验证方式**：运行扫描脚本，确认准确列出了所有包含 D:\360Downloads 的文件。手动修复后，将整个项目移动到 E:\Test 目录，确认统帅和跑批脚本均能正常运行，无路径报错。

#### 建议3：日志清理的"安全回收站"与"句柄保护"机制
- **问题**：自动清理旧日志的"误删正在写入文件"风险。原方案提出"7天前的日志自动删除"。如果batch_run的长任务日志跨越了7天，或者清理脚本没有检查文件句柄，直接os.remove会导致正在写入的进程抛出IOError甚至崩溃。
- **改进点**：防止自动清理日志时误删正在被batch_run写入的文件，保障长周期任务的稳定性。
- **具体修改**：在 `scripts/resource_monitor.py` 中，将"直接删除"改为"安全移动"，并增加文件占用检测。
  ```python
  import os, time, shutil
  from datetime import datetime
  def safe_cleanup_logs(log_dir, days=7):
      trash_dir = os.path.join(log_dir, ".trash")
      os.makedirs(trash_dir, exist_ok=True)
      cutoff_time = time.time() - (days * 86400)
      for filename in os.listdir(log_dir):
          filepath = os.path.join(log_dir, filename)
          if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
              # 1. 尝试检测文件是否被占用（Windows特有逻辑）
              try:
                  with open(filepath, 'a'): pass  # 尝试以追加模式打开
              except IOError:
                  continue  # 文件正在被写入，跳过
              # 2. 不直接删除，而是移动到回收站并加上时间戳
              dest = os.path.join(trash_dir, f"{datetime.now():%Y%m%d_%H%M%S}_{filename}")
              shutil.move(filepath, dest)
  ```
- **验证方式**：启动一个耗时较长的batch_run任务，同时手动触发日志清理逻辑。确认正在写入的日志文件未被删除，而7天前的旧日志被安全移动到了.trash目录。
- **优先级**：P1（近期）

#### 建议4：启动器脚本的"环境自愈"与"防呆设计"
- **问题**：启动器脚本（bat/sh）的"环境残留"与"端口冲突"隐患。Windows的.bat脚本在启动前，如果不检查并清理上次异常退出残留的进程（如占用9333端口的Chrome或8010端口的bridge），会导致新实例启动失败且难以排查。
- **改进点**：解决因上次异常退出导致的端口占用、配置丢失等"幽灵Bug"，实现启动前的自动自愈。
- **具体修改**：在 `start_openmanus.bat` 中增加环境清理和配置备份恢复逻辑。
  ```bat
  :: start_openmanus.bat 增加自愈逻辑
  echo [自检] 清理残留的 multi_bridge 进程...
  for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8010" ^| findstr "LISTENING"') do (
      taskkill /F /PID %%a >nul 2>&1
  )
  echo [自检] 检查 config.toml 完整性...
  if not exist "config.toml" (
      echo [警告] config.toml 丢失，从备份恢复...
      copy "config.toml.bak" "config.toml"
  )
  echo [启动] 激活环境并启动统帅...
  python main.py
  ```
- **验证方式**：手动启动一个占用8010端口的假进程（如 python -m http.server 8010），然后运行 start_openmanus.bat，确认脚本能自动杀掉假进程并成功启动统帅。

#### 建议5：成本估算的"模型级精准计费"与"飞书虚拟账单"
- **问题**：成本估算的"一刀切"失真。原方案提出记录Token并估算成本，但不同模型（lite/3.5/pro/智谱）的输入输出单价差异巨大，如果用一个统一的"平均单价"去乘总Token数，估算结果将毫无参考价值。
- **改进点**：摒弃"一刀切"的成本估算，建立基于模型维度的精准计费系统，培养成本意识。
- **具体修改**：在 `app/llm.py` 的响应拦截器中，增加按模型分类的Token统计，并在 `scripts/cost_estimator.py` 中配置各模型的实时单价，每日通过飞书发送"虚拟账单"。
  ```python
  # 在 scripts/cost_estimator.py 中
  MODEL_PRICING = {
      "gemini-2.5-flash-lite": {"input": 0.0, "output": 0.0},      # 免费
      "gemini-3.5-flash": {"input": 0.5, "output": 1.5},           # 每百万Token美元
      "gemini-2.5-pro": {"input": 1.25, "output": 5.0},
      "zhipu-4.5-air": {"input": 0.5, "output": 0.5}               # 人民币/千Token，需转换
  }
  def generate_daily_bill(stats):
      total_cost_usd = 0
      bill_lines = ["📊 统帅昨日虚拟账单："]
      for model, tokens in stats.items():
          price = MODEL_PRICING.get(model, {"input":0, "output":0})
          cost = (tokens['input'] / 1_000_000 * price['input']) + \
                 (tokens['output'] / 1_000_000 * price['output'])
          total_cost_usd += cost
          bill_lines.append(f"  {model}: {tokens['input']}输入 + {tokens['output']}输出 = ${cost:.4f}")
      bill_lines.append(f"总计: ${total_cost_usd:.4f}")
      return "\n".join(bill_lines)
  ```
- **验证方式**：运行一天包含多模型调用的任务后，在飞书群收到格式化的"虚拟账单"，确认各模型的Token统计准确，且成本估算符合官方定价逻辑。
- **优先级**：P2（远期）

#### 千问认为最有价值的部分
- **跨平台兼容性与路径集中管理的构想**：这是系统从"个人玩具"走向"工程化产品"的必经之路。将路径配置从代码中剥离，集中到config.toml，不仅解决了当前的Windows硬编码问题，更为未来迁移到Linux服务器或Mac环境扫清了最大障碍。
- **资源监控与自动清理日志的闭环**：在无人值守的长周期跑批中，磁盘空间耗尽是最常见的致命故障之一。提出监控磁盘并自动清理旧日志，是保障系统"可自愈、高可用"的关键基础设施。
- **成本控制与Token记录的"虚拟账单"思维**：即使当前使用的是免费API，建立精确的Token消耗记录和成本估算模型，也是极其优秀的工程习惯。这不仅能帮助我们评估当前方案的效率，更为未来切换到付费API或进行模型降级/升级提供了坚实的数据支撑。


### 智谱清言的改进建议（第3部分，未完成）
> 因bridge服务处理智谱清言标签时连续出现HTTP 500 Internal Server Error，3次重试均失败，本部分建议未生成。后续bridge修复后可补充。

---


## 【汇总·10条改进建议优先级排序】

| 序号 | 建议 | 来源 | 优先级 | 预计工作量 |
|---|---|---|---|---|
| 1 | 零环境引导部署（Bootstrap机制） | 千问 | P0 | 中 |
| 2 | 一键环境校验BAT（env_check.bat） | 豆包 | P0 | 小 |
| 3 | 网页桥接模式一键配置模板（config_chrome_bridge.toml） | 豆包 | P0 | 小 |
| 4 | 全局路径"去硬编码化"扫描与修复工具 | 千问 | P1 | 大 |
| 5 | 日志清理的"安全回收站"与"句柄保护"机制 | 千问 | P1 | 中 |
| 6 | 进程自愈批处理（daemon_watchdog.bat） | 豆包 | P1 | 中 |
| 7 | 启动器脚本的"环境自愈"与"防呆设计" | 千问 | P1 | 中 |
| 8 | 本地化配额成本统计模块（usage_monitor增强） | 豆包 | P2 | 中 |
| 9 | 成本估算的"模型级精准计费"与"飞书虚拟账单" | 千问 | P2 | 大 |
| 10 | 一键重置调试环境脚本（reset_debug.bat） | 豆包 | P2 | 小 |


---


## 【执行优先级】

### 立即执行（P0）
- [ ] 从零环境引导部署（Bootstrap机制）中提取最关键的1-2个改进点
- [ ] 编写env_check.bat一键环境校验脚本
- [ ] 编写config_chrome_bridge.toml网页桥接模式配置模板
- [ ] 修改对应代码文件
- [ ] 语法验证
- [ ] 测试验证

### 后续执行（P1）
- [ ] 全局路径"去硬编码化"扫描与修复工具
- [ ] 日志清理的"安全回收站"与"句柄保护"机制
- [ ] 进程自愈批处理（daemon_watchdog.bat）
- [ ] 启动器脚本的"环境自愈"与"防呆设计"
- [ ] 每个改进点实施后记录到训练日志

### 远期执行（P2）
- [ ] 本地化配额成本统计模块（usage_monitor增强）
- [ ] 成本估算的"模型级精准计费"与"飞书虚拟账单"
- [ ] 一键重置调试环境脚本（reset_debug.bat）

### 验证标准
- 代码语法正确
- 不破坏现有功能
- 改进点有明确的测试用例
- 测试通过后记录到002_完整版调试方案.md
- 跨平台兼容性测试（Windows + Mac/Linux）
- 无人值守跑批稳定性测试（72小时连续运行）
