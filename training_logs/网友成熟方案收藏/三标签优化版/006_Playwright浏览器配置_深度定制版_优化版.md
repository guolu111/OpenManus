# 006_Playwright浏览器配置_深度定制版（三标签深度优化版）

> 优化时间: 2026-09-05 21:59:07
> 参与标签: 豆包、千问国际版、智谱清言
> 优化原则: 只做加法，不做减法

---

## 原始方案

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


---

## 三标签改进建议汇总

### 豆包的建议

问题 1：原始方案偏向全新启动 Playwright 实例，没有对接现有9333 端口 Chrome 调试端口，没有复用已常驻运行的浏览器标签池，会重复拉起浏览器造成资源浪费，和multi_bridge.py现有架构脱节。
问题 2：异常处理缺少自愈重启逻辑，浏览器进程卡死、端口断开后任务直接失败，没有自动重连 9333 或告警触发进程重启。
问题 3：失败截图、操作日志只落本地文件，没有对接notify_feishu推送异常截图与日志摘要，无法远程监控浏览器自动化故障。
问题 4：缺少心跳保活机制，长时间金庸跑批空闲时调试端口静默断开，不会提前探测连接可用性。
问题 5：没有对接status_monitor上报浏览器连接状态，飞书控制端无法获知浏览器池是否正常在线。
问题 6：没有区分调试可视化模式 / 后台静默跑批模式双配置开关，无法一键切换，适配开发调试与正式跑批两套场景。
我的改进建议（只做加法）
建议 1：优先复用本机 9333 远程调试端口，接管已有 Chrome 而不是新建浏览器
改进点：保留原生 Playwright 启动逻辑作为备用；优先连接 ws://127.0.0.1:9333 复用常驻三标签浏览器池，和multi_bridge.py共用一套浏览器实例，减少内存占用。
具体修改：
修改文件：D:\360Downloads\金庸\一念永恒\一念永恒小说\开源拉取\OpenManus\playwright_client.py（若无该文件则新增）
python
运行
from playwright.sync_api import connect
try:
browser = connect("ws://127.0.0.1:9333")
except Exception:
# 保留原方案：本地启动浏览器作为降级兜底
browser = playwright.chromium.launch(headless=headless_flag)验证方式：Chrome 提前开启 9333 调试端口，运行脚本直接附着现有窗口；关闭 Chrome 后程序自动拉起全新浏览器兜底。
优先级：P0（立即）
建议 2：增加浏览器心跳探活 + 断线自动重连机制
改进点：每一次页面操作前检测 9333 端口连通性；连接丢失触发一次重连，重连失败推送飞书告警，更新status_monitor状态。
修改文件：playwright_client.py，封装health_check()心跳函数，每次访问页面前执行探测；捕获连接异常执行重试逻辑。
async def browser_heartbeat():
resp = requests.get("http://127.0.0.1:9333/json/version",timeout=3)
return resp.status_code == 200
except:
return False
验证方式：运行自动化脚本中途关闭 Chrome 进程，观察日志触发重连逻辑，失败推送飞书告警。
建议 3：操作失败自动截图，截图摘要通过 notify_feishu 远程推送
改进点：保留本地保存错误截图逻辑；捕获页面异常后，截图写入./log/browser_snapshot/，同时发送飞书消息附带故障描述，便于远程排查。
修改文件：playwright_client.py异常捕获分支
snap_path = Path("./log/browser_snapshot")
snap_path.mkdir(exist_ok=True,parents=True)
page.screenshot(path=str(snap_path / f"fail_{int(time.time())}.png"))
await notify_feishu(title="浏览器自动化异常",content=f"会话:{session_id} 页面加载失败")
验证方式：主动制造元素找不到 / 超时错误，检查截图目录生成图片，飞书收到告警消息。
优先级：P1（近期）
建议 4：双模式配置开关，config.toml 区分调试可视化 / 静默跑批
改进点：在配置文件增加运行模式标识，开发调试时可视化窗口，正式金庸跑批使用静默后台模式，保留原始 headless 配置能力。
修改config.toml追加配置块
toml
[
browser_setting
]
mode = "batch"   # batch=静默后台，debug=可视窗口
navigation_timeout = 30000
action_timeout = 10000
playwright_client.py读取 mode 变量自动选择 headless 参数。
验证方式：修改 mode 值分别运行，观察浏览器是否弹出窗口。
建议 5：浏览器状态上报 status_monitor，纳入全局任务监控面板
改进点：浏览器成功连接、心跳断开、重连失败事件全部上报监控工具，飞书控制端可以实时查看浏览器池健康状态。
在连接成功 / 失败分支追加调用监控接口
await status_monitor(session_id=session_id,browser_state="online"/"offline"/"retrying")
验证方式：启停浏览器，查看监控日志记录对应状态变更。
建议 6：操作流水日志持久化保存，记录完整页面访问轨迹
改进点：每次页面跳转、元素点击、等待操作写入独立日志文件，保存在./log/browser_step/，跑批复盘时还原完整自动化流程。
在每个页面动作后追加日志写入逻辑，记录时间戳、动作名称、页面 url。
验证方式：执行一轮浏览器操作，日志文件夹生成带时间戳的操作记录 txt。
优先级：P2（远期）
我认为这个方案中最有价值的部分
完整梳理 Playwright 五大高频故障场景以及对应的标准处理手段（持久 cookie、等待策略、反爬检测）；
提供一套成熟工程化最佳实践：浏览器实例复用、networkidle 等待、失败截图、全链路日志，符合自动化跑批的生产规范；
给出可直接落地的超时、视口、持久上下文配置模板，不需要从零调研 Playwright 官方文档，复用社区稳定实践。
怎样对接`notify_feishu`推送异常截图与日志摘要？
PPT 生成
AI 播客
录音转写

### 千问国际版的建议

*（未返回有效内容）*

### 智谱清言的建议

你好！我是清言。针对“006_Playwright浏览器配置_深度定制版”方案的第3/3部分（执行优先级与验证标准），我已仔细阅读并结合我们的现有资产进行了深度分析。
由于本方案主题是“Playwright浏览器配置”，这直接关系到OpenManus统帅的“眼睛和手”。结合我们已有“三个标签Chrome（端口9333）+ multi_bridge.py常驻（端口8010）”的特殊架构，如果统帅修改Playwright配置（如参数、无头模式等）导致不兼容现有9333端口Chrome，会直接导致浏览器操作全面瘫痪。原方案的通用P0/P1清单缺乏针对浏览器层的防护与连通性验证。
以下是我的发现与具体改进建议（严格遵循只做加法原则）：
我发现的问题（如果有）
问题1：浏览器配置修改缺乏“防崩溃与启动自愈”机制。 Playwright的配置文件（如 browser_use 或 config.toml 中的连接参数）如果被改坏（如连不上9333端口、无头/有头模式冲突），会导致统帅启动浏览器时直接抛出异常卡死。原方案仅做“语法验证”，无法捕捉这种连接级崩溃。
问题2：“测试验证”缺乏针对浏览器的极简连通性沙盒。 验证浏览器配置是否修复，不能用全量小说任务测试。原方案未定义“最小化连通性测试”，如果直接跑批，一旦失败排查极难。
问题3：未结合现有 9333 端口 Chrome 与 8010 Bridge 的特性。 原方案未明确测试修改后的Playwright是否能正确接管我们既有的三个标签Chrome，存在环境脱节风险。
我的改进建议（只做加法）
在原方案的【立即执行（P0）】、【后续执行（P1）】和【验证标准】清单中，追加以下具体内容：
建议1：P0阶段增加“改前与连接失败自愈”子步骤改进点： 修改浏览器配置代码前，自动备份；修改后不仅验证语法，还要在沙盒中尝试启动/连接浏览器，连接失败则自动回滚，防止统帅卡死。
具体修改：
在P0清单中追加：
- [ ] 修改前，调用 python_execute 执行 shutil.copy('目标文件', '目标文件.bak')
- [ ] 语法验证后，调用 python_execute 运行极简连接测试（见建议2），若抛出异常或超时，自动执行 shutil.move('目标文件.bak', '目标文件') 回滚，并调用 notify_feishu 告警“浏览器配置连接失败，已自愈回滚”
验证方式： 故意把Playwright的 cdp_url 端口改为9334（错误端口），观察系统是否自动回滚原文件，且飞书“最强大脑”是否收到告警。
优先级： P0（立即）
建议2：在【验证标准】中增加“9333端口Chrome连通性沙盒测试”
改进点： 针对浏览器配置修复，定义一个只做“连接并获取标签页数量”的极简测试脚本，确保配置与现有的9333端口Chrome兼容。
在【验证标准】清单中追加：
- [ ] 调用 python_execute 并运行 browseronn.py，内容为：通过Playwright以CDP模式连接 http://127.0.0.1:9333，并执行 context.pages 获取当前页面数量，设置timeout=30秒
- [ ] 调用 status_monitor 查看实时日志，确认未报超时或连接拒绝（CRefused），且成功返回页面数（应为3）
验证方式： 统帅完成配置修改后直接运行此沙盒脚本。若日志显示成功获取页面数且无报错，即代表测试通过。
建议3：P1阶段增加“验证结果飞书自动归档”机制
改进点： 将浏览器配置的修改记录自动化归档，并向飞书同步当前浏览器连通状态。
在【后续执行（P1）】和【验证标准】中追加：
- [ ] 沙盒测试通过后，调用 thon_execute 以追加模式(mode='a')将修改记录写入 002_完整版调试方案.md
验证方式： 测试跑完后，检查 002_完整版调试方案.md 底部是否有新记录，且飞书群是否收到成功通报。
优先级： P1（近期）
我认为这个方案中最有价值的部分
“提取最关键的1-2个改进点”的小步快跑策略。 浏览器配置（尤其是接管已有Chrome实例的CDP连接配置）涉及多个参数（如 --remote-debugging-port、headless状态等），牵一发而动全身。原方案这种克制和聚焦的策略，是避免浏览器引擎崩溃的基石，我们只需补齐自动化沙盒连通测试的“血肉”即可。
2/2

