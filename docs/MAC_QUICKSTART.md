# Mac 快速上手指南

> 本文档帮助你在Mac电脑上5分钟内启动OpenManus统帅。

## 一、这是什么？

OpenManus统帅是一个AI智能体框架，核心能力：
- **理解指令**：你用自然语言下达任务，它自动拆解执行
- **调用工具**：浏览器、文件操作、Python执行、飞书通知等20+工具
- **多模型协同**：Gemini做决策，智谱/硅基做数据搬运，3标签网页版做深度思考
- **自我进化**：自动记录错误和经验，越用越聪明

## 二、5分钟快速启动

### 第1步：安装基础环境（只需一次）

```bash
# 1. 安装Homebrew（如果没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Python 3.11+
brew install python@3.11

# 3. 安装Git（如果没有）
brew install git

# 4. 安装Chromium（开源浏览器，用于网页版AI标签）
brew install --cask chromium
```

### 第2步：下载并解压项目

```bash
# 解压下载的zip包
unzip OpenManus_一念永恒定制版_v4.zip
cd OpenManus
```

### 第3步：创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 第4步：配置API密钥

```bash
# 复制示例配置
cp config/config.example.toml config/config.toml

# 编辑配置文件，填入你的API密钥
nano config/config.toml
```

需要配置的API：
- **主力模型**：Gemini（谷歌中转API，决策用）
- **辅助模型**：智谱GLM-4.5-air（数据搬运用）
- **轻量模型**：硅基流动GLM-4-9B（简单任务用）

### 第5步：启动！

```bash
# 启动统帅
python main.py
```

启动后会显示：
```
✅ OpenManus统帅已启动
📁 工作目录: /path/to/OpenManus
🤖 当前模型: gemini-2.5-flash-lite
💡 输入你的任务，或输入 /help 查看命令
```

## 三、首次使用必做的3件事

### 1. 测试基础功能

在统帅界面输入：
```
帮我列出当前目录的文件
```
如果能正常返回文件列表，说明基础功能正常。

### 2. 配置飞书通知（可选但推荐）

```
帮我配置飞书通知，webhook地址是: https://open.feishu.cn/open-apis/bot/v2/hook/你的地址
```
配置后，任务开始/完成/出错都会自动发飞书消息到你手机。

### 3. 浏览知识库

统帅内置了DeepSeek 3673条思考过程蒸馏的知识库，遇到复杂问题会自动检索参考。

手动检索方法：
```bash
python knowledge_base/deepseek_thinking/search.py --stats
python knowledge_base/deepseek_thinking/search.py --keyword "任务拆解"
```

## 四、常用命令

| 命令 | 功能 |
|------|------|
| `/help` | 查看帮助 |
| `/status` | 查看当前状态（模型、用量、任务） |
| `/memory` | 查看记忆和经验库 |
| `/todo` | 查看当前任务清单 |
| `/clear` | 清空上下文 |
| `/exit` | 退出统帅 |

## 五、Mac专属优化建议

### 1. 2019款MacBook Pro优化

如果是2019款老Mac，建议：
- 系统：macOS 15（Sequoia）
- 浏览器：用Chromium代替Chrome（更轻量）
- 关闭不必要的后台特效：系统设置 → 辅助功能 → 显示 → 勾选"减少动态效果"

### 2. 发热控制

```bash
# 安装监控工具
brew install --cask stats

# 运行时如果发热严重，可以限制CPU频率
# （需要安装Turbo Boost Switcher）
brew install --cask turbo-boost-switcher
```

### 3. 浏览器profile管理

网页版AI标签（智谱/千问/豆包）的登录态存在：
```
~/.openmanus/chrome_profile/
```
首次使用需要手动扫码登录，之后会自动保存登录态。

## 六、常见问题

### Q: 启动报错 "ModuleNotFoundError"
A: 确保已经激活虚拟环境：`source .venv/bin/activate`，然后重新安装依赖：`pip install -r requirements.txt`

### Q: API调用失败
A: 检查 `config/config.toml` 中的API密钥是否正确，网络是否能访问对应API。

### Q: 网页版AI标签无法登录
A: 首次使用需要手动扫码登录。启动后会自动弹出Chromium浏览器，扫码登录智谱/千问/豆包即可。

### Q: 如何更新到最新版本？
A: 下载最新的zip包，解压后覆盖即可。配置文件和浏览器profile不会被覆盖。

## 七、下一步学习

- 📖 [项目结构和目录索引](PROJECT_STRUCTURE.md) - 了解每个目录是做什么的
- 📖 [使用方法指南](USAGE_GUIDE.md) - 深入学习统帅的各种功能
- 📖 [调试方案指南](DEBUG_GUIDE.md) - 遇到问题怎么排查
- 📖 [Mac软件清单和优化方案](MAC_SOFTWARE_OPTIMIZATION.md) - Mac端完整软件配置

---

**有问题？** 先看 [调试方案指南](DEBUG_GUIDE.md)，90%的问题都能在里面找到解决方案。
