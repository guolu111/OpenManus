# 006_Playwright浏览器配置_深度定制版 - 豆包的改进建议

> 生成时间: 2026-09-05 21:49:52
> 处理部分: 第1/3部分

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