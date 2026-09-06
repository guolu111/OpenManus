# OpenManus 知识库

## 概述

本目录存放OpenManus统帅的长期知识库，包含从历史对话中蒸馏的思考经验、语料库和可复用的模式。

## 目录结构

```
knowledge_base/
├── README.md                          # 本文件
└── deepseek_thinking/                 # DeepSeek思考过程知识库（3673条）
    ├── README.md                      # DeepSeek知识库详细说明
    ├── search.py                      # 检索工具
    ├── DeepSeek思考经验包.txt         # 蒸馏后的经验文本（3673条精选）
    ├── DeepSeek思考经验包.json        # 结构化的思考经验JSON
    ├── DeepSeek_AI回复语料.txt        # AI回复语料（34.84 MB）
    ├── DeepSeek用户消息语料.txt       # 用户消息语料（49.43 MB）
    ├── DeepSeek词频统计.json          # 词频统计
    ├── _extract_thinking.py           # 思考过程提取脚本
    └── _extract_deepseek.py           # DeepSeek数据提取脚本
```

## 使用方法

### 1. 检索思考经验

```bash
cd knowledge_base/deepseek_thinking

# 按关键词搜索
python search.py --keyword "任务拆解"

# 按分类查询
python search.py --category "需求分析"

# 随机抽取示例
python search.py --random 5

# 统计信息
python search.py --stats
```

### 2. 在统帅提示词中引用

统帅的系统提示词第九章已包含最精华的6大思维模式（从3673条中蒸馏）：
- 需求分析·3步法
- 任务拆解·逐项核对法
- 决策判断·对比择优法
- 错误处理·根因追踪法
- 回复组织·结构化输出法
- 思维纪律·防重复循环

遇到复杂场景时，可通过检索工具查询完整示例作为few-shot参考。

## 知识库扩展计划

- [ ] 豆包思考过程蒸馏（待收集）
- [ ] 千问思考过程蒸馏（待收集）
- [ ] 智谱思考过程蒸馏（待收集）
- [ ] 跨模型思维模式对比分析
- [ ] 思维模式有效性评估

## 注意事项

1. 知识库文件较大（约98MB），已包含在发布包中
2. 检索工具使用纯Python，无需额外依赖
3. 语料文件为原始数据，可用于后续训练或分析
4. 新增知识库时请按`模型名_内容类型/`的目录结构组织
