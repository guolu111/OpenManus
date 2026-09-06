# 调试方案指南

> 本文档汇总了OpenManus统帅常见问题的排查和解决方案。90%的问题都能在这里找到答案。

## 一、启动问题

### 1.1 ModuleNotFoundError

**症状：**
```
ModuleNotFoundError: No module named 'xxx'
```

**原因：** 虚拟环境未激活或依赖未安装

**解决方案：**
```bash
# 1. 激活虚拟环境
source .venv/bin/activate  # Mac/Linux
# 或
.venv\Scripts\activate     # Windows

# 2. 重新安装依赖
pip install -r requirements.txt

# 3. 如果还是不行，重建虚拟环境
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1.2 配置文件找不到

**症状：**
```
FileNotFoundError: config/config.toml
```

**原因：** 没有从示例配置复制

**解决方案：**
```bash
cp config/config.example.toml config/config.toml
# 然后编辑 config.toml，填入你的API密钥
```

### 1.3 API密钥错误

**症状：**
```
AuthenticationError: Invalid API key
```

**原因：** API密钥错误或过期

**解决方案：**
1. 检查 `config/config.toml` 中的API密钥
2. 确认密钥没有多余的空格或换行
3. 重新生成API密钥
4. 测试API连通性：
```bash
curl -X POST https://your-api-endpoint/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-flash-lite", "messages": [{"role": "user", "content": "hi"}]}'
```

## 二、运行时问题

### 2.1 工具调用失败

**症状：** 统帅反复调用同一个工具但一直失败

**原因：** 工具参数错误或环境问题

**排查步骤：**
1. 查看 `logs/` 目录下的最新日志
2. 找到具体的错误信息
3. 检查工具参数是否正确
4. 手动执行工具对应的命令，看是否能成功

**常见工具问题：**

| 工具 | 常见问题 | 解决方案 |
|------|---------|---------|
| bash.py | 命令不存在 | 检查命令拼写，安装缺失软件 |
| python_execute.py | 语法错误 | 检查Python代码语法 |
| web_search.py | 网络不通 | 检查网络连接和代理设置 |
| browser.py | 浏览器启动失败 | 检查Chromium是否安装，profile是否损坏 |

### 2.2 上下文过长

**症状：**
```
ContextWindowExceededError: tokens exceed limit
```

**原因：** 对话太长，超出模型上下文限制

**解决方案：**
1. 输入 `/clear` 清空上下文
2. 长内容存文件，上下文只留摘要和路径
3. 工具返回结果过长时自动截断
4. 使用支持更长上下文的模型

### 2.3 模型限流

**症状：**
```
RateLimitError: 429 Too Many Requests
```

**原因：** API调用频率过高或当日额度用完

**解决方案：**
1. 等待1-2分钟后重试
2. 四模型自动轮转（已配置）
3. 简单任务用智谱/硅基，不占Gemini额度
4. 查看当日用量：`/status`

### 2.4 统帅陷入循环

**症状：** 统帅反复想同一件事，调用相同的工具，没有进展

**原因：** 思维陷入死循环，或工具返回结果不符合预期

**解决方案：**
1. 手动打断：输入"停一下，换个思路"
2. 查看 `todo.md`，确认当前步骤
3. 检查工具返回结果是否正确
4. 如果是工具问题，换一个工具或方法
5. 如果是思路问题，明确给出新方向

## 三、浏览器和3标签问题

### 3.1 浏览器启动失败

**症状：**
```
BrowserInitError: Failed to launch browser
```

**原因：** Chromium未安装或profile损坏

**解决方案：**
```bash
# 1. 安装Chromium
brew install --cask chromium  # Mac
# 或
choco install chromium        # Windows

# 2. 如果profile损坏，删除后重建
rm -rf ~/.openmanus/chrome_profile
# 然后重新启动，会自动创建新profile
```

### 3.2 3标签桥接异常

**症状：**
```
BridgeError: Connection refused on port 8010
```

**原因：** 桥接服务未启动或崩溃

**解决方案：**
```bash
# 1. 检查桥接状态
python -c "from app.tool.bridge_health_tool import check; print(check())"

# 2. 重启桥接
python -c "from app.tool.bridge_health_tool import restart; print(restart())"

# 3. 如果还是不行，手动启动
python bridges/multi_bridge.py &
```

### 3.3 网页版AI登录态丢失

**症状：** 3标签返回"请先登录"

**原因：** 浏览器profile被清理或登录过期

**解决方案：**
1. 启动统帅后会自动弹出Chromium
2. 手动扫码登录智谱/千问/豆包
3. 登录态会自动保存到profile
4. 下次启动自动恢复登录

**注意：** 不要删除 `~/.openmanus/chrome_profile/` 目录，否则登录态会丢失。

### 3.4 智谱清言需要点"重新回答"

**症状：** 智谱清言有时返回"本次回答已被终止"

**原因：** 智谱风控机制，长时间无响应会自动终止

**解决方案：**
1. 统帅已内置自动检测和重试机制
2. 检测到"回答已被终止"会自动点"重新回答"
3. 如果连续3次失败，会切换到其他标签

## 四、性能优化

### 4.1 启动慢

**优化方法：**
1. 使用SSD硬盘
2. 关闭不必要的后台程序
3. 预加载常用模型
4. 使用更快的API端点

### 4.2 响应慢

**优化方法：**
1. 简单任务用轻量模型（flash-lite）
2. 数据搬运外包给智谱/硅基
3. 减少不必要的工具调用
4. 批量处理而不是逐个处理

### 4.3 内存占用高

**优化方法：**
1. 定期 `/clear` 清空上下文
2. 长内容存文件，不留在上下文
3. 关闭不需要的浏览器标签
4. 限制同时运行的任务数

## 五、日志和诊断

### 5.1 查看日志

```bash
# 查看最新日志
ls -lt logs/ | head -10
tail -f logs/最新日志文件.log

# 查看错误日志
grep -i "error" logs/*.log

# 查看梦境日志
ls -lt logs/dreaming/
```

### 5.2 查看记忆和经验

```bash
# 查看历史错误
cat .learnings/ERRORS.md

# 查看已学经验
cat .learnings/LEARNINGS.md

# 查看持久记忆
cat memory/*.json
```

### 5.3 诊断脚本

```bash
# 运行诊断
python -c "
from app.tool.status_monitor_tool import get_status
print(get_status())
"

# 查看用量
python -c "
from app.tool.usage_tool import get_usage
print(get_usage())
"
```

## 六、紧急恢复

### 6.1 统帅完全无响应

1. 按 `Ctrl+C` 终止
2. 检查是否有残留进程：`ps aux | grep python`
3. 杀掉残留进程：`kill -9 <PID>`
4. 检查单实例锁：`rm -f .openmanus.lock`
5. 重新启动

### 6.2 配置文件损坏

1. 从示例配置恢复：`cp config/config.example.toml config/config.toml`
2. 重新填入API密钥
3. 如果有备份，从备份恢复

### 6.3 数据丢失

1. 检查Git历史：`git log --oneline -10`
2. 恢复误删文件：`git checkout -- <filename>`
3. 从zip包重新解压
4. 检查 `memory/` 和 `logs/` 目录是否完整

## 七、获取帮助

如果以上方案都无法解决问题：

1. **查看训练日志**：`training_logs/` 目录有大量调试方案
2. **查看网友方案**：`training_logs/网友成熟方案收藏/` 有10个深度定制方案
3. **搜索知识库**：`python knowledge_base/deepseek_thinking/search.py --keyword "你的问题"`
4. **查看TODO**：`cat TODO_待修复问题清单.md` 可能有已知问题
5. **提交Issue**：在GitHub仓库提交Issue，附上日志

---

**记住：** 90%的问题都是配置问题，先检查配置，再看日志，最后才改代码。
