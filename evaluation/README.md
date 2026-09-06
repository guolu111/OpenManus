# OpenManus 评测体系说明

## 概述

本目录包含 OpenManus 的离线评测体系，参考网友成熟方案（Agent评测5硬指标）建立。

## 评测5个硬指标

| 指标 | 权重 | 说明 |
|------|------|------|
| 任务完成率 | 30% | 任务是否成功完成（需多随机种子统计） |
| 幻觉率 | 20% | 细分三类：未知工具幻觉/影子调用/参数幻觉 |
| 工具调用准确率 | 20% | 工具选择/参数正确/调用顺序 |
| 错误恢复率 | 15% | 遇到错误后能否自行恢复（基准80%） |
| 成本与延迟 | 15% | Token消耗/完成时间/cost per successful task |

## 文件说明

- `golden_tasks.json` - Golden Tasks 评测任务集（15个代表性任务）
- `run_evaluation.py` - 评测运行脚本
- `report_*.json` - 评测报告（自动生成）

## 任务分类

| 分类 | 数量 | 难度 | 说明 |
|------|------|------|------|
| 简单查询 | 2 | easy | API用量/任务状态查询 |
| 文件操作 | 1 | easy | 读取文件 |
| 代码执行 | 1 | easy | 简单计算 |
| 网络搜索 | 1 | medium | 联网搜索 |
| 多步任务 | 1 | medium | 规划并执行多步 |
| 粗活分流 | 1 | medium | 调用小模型 |
| 错误处理 | 2 | medium/hard | 不存在工具/错误恢复 |
| 记忆功能 | 1 | medium | remember/recall |
| 规划能力 | 1 | hard | 复杂任务规划 |
| 浏览器操作 | 1 | hard | 浏览器工具调用 |
| 参数幻觉 | 1 | hard | 参数幻觉测试 |
| 影子调用 | 1 | hard | 影子调用测试 |
| 长输出处理 | 1 | medium | 自动截断测试 |

## 使用方法

```bash
# 运行指定任务
python evaluation/run_evaluation.py --tasks T001,T002,T003

# 运行全部分类
python evaluation/run_evaluation.py --category 简单查询

# 运行全部任务
python evaluation/run_evaluation.py --all

# 指定输出文件
python evaluation/run_evaluation.py --all --output evaluation/my_report.json
```

## 通过标准

- 综合评分 ≥ 70分
- 任务完成率 ≥ 70%
- 幻觉率 ≤ 10%

## Brosweet 探针套件（进阶）

参考网友方案，后续可添加三类探针测试：

1. **诱饵目录**：故意移除任务需要的工具，看Agent是拒绝还是编造工具
2. **影子陷阱**：并列两个名字相似的工具，看Agent会不会选错
3. **过度承诺陷阱**：在系统提示词中写超出实际能力的描述，看Agent会不会真的去编

## 后续优化方向

- [ ] 接入CI/CD，每次代码变更自动运行评测
- [ ] 添加评测集三分法（训练集/验证集/测试集）
- [ ] 实现A/B测试框架，对比不同版本的性能
- [ ] 添加在线评测（生产环境分层采样）
- [ ] 集成轻量裁判模型（如 Galileo Luna-2）做全量评测
