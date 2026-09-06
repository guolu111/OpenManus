# 工具掩码机制研究文档

> 参考 Manus 教训三：工具太多怎么办？给它"蒙上眼"，而不是"拿走"

## 问题背景

当 Agent 学会的工具越来越多（当前 OpenManus 有 20+ 工具），它就开始犯傻了，不知道该用哪个。

**常规思路的问题**：按需加载工具，这轮用不到的工具就不放在上下文里。

**Manus 踩坑结论**：这是个巨坑！因为：
1. 工具定义通常放在上下文开头，每动一次工具列表就改了"考卷"开头，KV缓存全废
2. 模型看到之前操作记录里有某个工具，但现在工具列表里没了，会"精神错乱"

## Manus 的解决方案：工具掩码（Masking）

工具列表永远是固定的、完整的。但在某个特定状态下，通过技术手段在模型生成答案的最后一刻告诉它：
"虽然你有很多工具，但你现在只能用那几个以 `browser_` 开头的！"

### 实现方式：掩码 token logits

在 LLM 生成工具调用时，通过 logits 处理器（logits processor）在生成的最后一刻，把不允许使用的工具的 token 概率设为 -inf（或非常小的值）。

这样：
- ✅ 工具列表保持稳定，KV缓存不失效
- ✅ 模型不会"精神错乱"
- ✅ 可以动态控制当前可用工具范围

## OpenManus 实现方案

### 方案A：基于 OpenAI API 的 logit_bias（简单但有限）

OpenAI API 支持 `logit_bias` 参数，可以给特定 token 设置偏置。

**优点**：实现简单，直接在 API 调用时传参
**缺点**：
- 只能设置偏置，不能完全禁用（最大值100，不能设为-inf）
- 工具名可能由多个 token 组成，需要精确计算 token ID
- 不是所有模型都支持（Gemini/智谱等可能不支持）

### 方案B：基于提示词的软掩码（简单但效果差）

在系统提示词中添加："当前状态下，你只能使用以下工具：tool1, tool2, tool3"

**优点**：实现最简单，不需要修改代码
**缺点**：
- 模型可能不遵守，仍然调用其他工具
- 增加了提示词长度
- 效果不稳定

### 方案C：基于后处理的硬掩码（推荐，效果好）

在 LLM 返回工具调用后，检查工具名是否在允许列表中。如果不在，返回错误信息，让模型重新选择。

**优点**：
- 实现相对简单，在工具调用层做校验
- 效果稳定，模型调用不允许的工具会收到明确错误
- 不依赖特定模型的 API 特性
- 可以记录违规调用，用于后续优化

**缺点**：
- 模型可能会反复尝试调用不允许的工具，浪费 token
- 需要在错误提示中明确告诉模型哪些工具可用

### 方案D：基于自定义 LLM 封装的 logits 掩码（最完美但复杂）

封装 LLM 调用，在生成过程中注入 logits 处理器，完全禁用不允许的工具。

**优点**：
- 效果最完美，模型根本无法生成不允许的工具名
- KV缓存完全不失效
- 符合 Manus 原始方案

**缺点**：
- 实现复杂，需要深入修改 LLM 调用层
- 依赖模型 API 是否支持流式生成和 logits 处理器
- 不同模型的实现方式可能不同

## 推荐实施路径

### 第一阶段：方案C（后处理硬掩码）+ 方案B（提示词软掩码）

**实现位置**：`app/agent/toolcall.py` 的 `execute_tool` 方法

**实现逻辑**：
1. 添加 `allowed_tools` 属性（可选，None 表示全部可用）
2. 在 `execute_tool` 中检查工具名是否在允许列表中
3. 如果不在，返回明确的错误信息，包含当前可用工具列表
4. 在系统提示词中添加工具掩码使用说明

**代码框架**：
```python
class ToolCallAgent(ReActAgent):
    # 工具掩码：None 表示全部可用，列表表示只允许这些工具
    _allowed_tools: ClassVar[Optional[List[str]]] = None
    
    @classmethod
    def set_allowed_tools(cls, tools: Optional[List[str]] = None):
        """设置当前允许使用的工具列表（None 表示全部可用）"""
        cls._allowed_tools = tools
    
    async def execute_tool(self, command: ToolCall) -> str:
        name = command.function.name
        
        # 工具掩码检查
        if self._allowed_tools is not None and name not in self._allowed_tools:
            available = ", ".join(self._allowed_tools)
            return (
                f"Error: Tool '{name}' is not available in current context.\n"
                f"Available tools: {available}\n"
                f"Please select a tool from the available list."
            )
        
        # ... 原有逻辑
```

### 第二阶段：方案A（logit_bias 优化）

在第一阶段基础上，对于支持 logit_bias 的模型（如 OpenAI 系列），添加 logit_bias 参数，进一步减少模型调用不允许工具的概率。

### 第三阶段：方案D（完整 logits 掩码）

当需要更完美的效果时，深入修改 LLM 调用层，实现完整的 logits 掩码。

## 使用场景

1. **浏览器操作模式**：只允许 browser_* 系列工具
2. **文件操作模式**：只允许 str_replace_editor、bash、python_execute
3. **跑批模式**：只允许 batch_run、bridge_health、status_monitor、notify_feishu
4. **简单查询模式**：只允许 usage_monitor、status_monitor、memory
5. **安全模式**：禁用所有可能有风险的工具（如 bash、python_execute）

## 与 KV 缓存的协同

工具掩码机制的核心优势是与 KV 缓存协同：
- 工具列表永远不变 → 系统提示词前缀稳定 → KV 缓存命中率高
- 掩码通过 logits 或后处理实现 → 不修改上下文 → 不影响缓存
- 可以在不同任务间快速切换掩码模式 → 不需要重新构建上下文

## 后续优化方向

- [ ] 实现第一阶段（后处理硬掩码 + 提示词软掩码）
- [ ] 添加常用掩码模式预设（浏览器模式/文件模式/跑批模式等）
- [ ] 实现掩码模式的自动切换（根据任务类型自动选择）
- [ ] 研究方案A（logit_bias）的可行性
- [ ] 研究方案D（完整 logits 掩码）的实现路径
- [ ] 添加掩码使用统计，分析哪些模式最常用

## 参考资料

- Manus 创始人亲述：重写了4遍Agent框架，才悟出这7条教训
- Context Engineering for AI Agents: Lessons from Building Manus
- OpenAI API 文档：logit_bias 参数
