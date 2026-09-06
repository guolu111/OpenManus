# 📋 OpenManus 待修复问题清单（智能体自行修复）

> 这是给 OpenManus 智能体自己看的修复清单。发现问题后，由智能体自行分析、自行修复，不需要外部干预。

---

## 问题1：auto_memory 提取失败（高优先级）

**发现时间**：2026-09-06 08:53
**发现场景**：独立运行任务"列出当前目录文件"后，任务完成但自动记忆提取失败

**错误信息**：
```
ERROR | app.tool.auto_memory:extract_and_store:197 - 自动记忆提取失败：'"store"'
```

**问题位置**：
- `app/tool/auto_memory.py` 第197行 `extract_and_store` 方法
- 调用链：`extract_and_store` → `_parse_llm_response` → `_validate_memory_item` → `memory_tool.execute(action="remember", store=store, ...)`

**可能原因分析**：
1. LLM 返回的 JSON 格式不符合预期，导致 `store` 字段解析错误
2. `_validate_memory_item` 方法返回的 `store` 值不是有效的 STORES 列表中的值（facts/episodes/skills）
3. `_parse_llm_response` 方法在解析 LLM 返回时，可能把键名 "store" 当成了值
4. memory_tool.execute 的参数名 `store` 可能和内部变量冲突

**建议排查步骤**：
1. 在 `extract_and_store` 方法中添加调试日志，打印 LLM 返回的原始 response
2. 检查 `_parse_llm_response` 方法的解析逻辑，确认返回的 items 格式
3. 检查 `_validate_memory_item` 方法，确认返回的 (store, key, value) 三元组
4. 在调用 `memory_tool.execute` 之前打印 store/key/value 的值
5. 检查 memory_tool.py 第120行 `if store not in STORES` 的判断逻辑

**修复要求**：
- 修复后必须重新运行一个完整任务，验证 auto_memory 能正常提取和存储记忆
- 修复后在本文件中标记为"已修复"，并记录修复方案
- 不要修改主流程逻辑，只修复记忆提取部分

**参考文件**：
- `app/tool/auto_memory.py`（问题文件）
- `app/tool/memory_tool.py`（被调用的记忆工具）
- `memory/facts.json` / `memory/episodes.json` / `memory/skills.json`（记忆存储文件）

---

## 问题2：工作目录理解偏差（低优先级）

**发现时间**：2026-09-06 08:53
**发现场景**：任务要求"列出当前目录"，但智能体理解为 workspace 目录

**问题描述**：
- 用户说"当前目录"，智能体默认理解为 `workspace/` 目录
- 实际上"当前目录"可能指 OpenManus 根目录
- 这是一个理解偏差，不影响功能，但可能影响用户体验

**建议修复方向**：
- 在系统提示词中明确"当前目录"的定义
- 或者在 str_replace_editor 工具的描述中明确工作目录
- 或者让智能体在不确定时主动询问用户

**优先级**：低，可以后续优化

---

## 修复记录模板

```
### 问题X：[问题标题]
- 修复时间：YYYY-MM-DD HH:MM
- 修复人：OpenManus 智能体自行修复
- 修复方案：[简述修复方案]
- 修改文件：[列出修改的文件]
- 验证结果：[运行验证任务的结果]
- 状态：✅ 已修复
```

---

**最后更新**：2026-09-06
**待修复问题数**：2（1个高优先级，1个低优先级）
**已修复问题数**：0
