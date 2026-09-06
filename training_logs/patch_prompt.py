# -*- coding: utf-8 -*-
"""修改系统提示词，添加跑批任务标准流程和工具调用示例"""

with open('app/prompt/manus.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''      "6. 【跑批任务必须用batch_run工具】——不要用python_execute直接运行跑批脚本（会阻塞事件循环），必须用batch_run工具。\\n"
  )'''

new = '''      "6. 【跑批任务必须用batch_run工具】——不要用python_execute直接运行跑批脚本（会阻塞事件循环），必须用batch_run工具。\\n"
      "\\n"
      "===== 跑批任务标准流程（2026-09-05 网友方案深度定制）=====\\n"
      "当用户要求跑批（如跑鹿鼎记第3章）时，必须严格按照以下流程执行，不得跳过或更改顺序：\\n"
      "\\n"
      "【第1步】任务初始化（必须同时调用3个工具）：\\n"
      "   - status_monitor(action=update, status=running, task=鹿鼎记第X章跑批, step=初始化, detail=任务开始)\\n"
      "   - usage_monitor(channel=all)  查询初始API用量\\n"
      "   - notify_feishu(text=【监控】跑批开始：鹿鼎记第X章, type=text)  发送开始通知\\n"
      "\\n"
      "【第2步】启动跑批（必须调用batch_run工具）：\\n"
      "   - batch_run(book=鹿鼎记, chapter=X, mode=pure_data)\\n"
      "   - 注意：batch_run启动后立即返回（不等待完成），返回结果包含started=True和PID和实时日志路径\\n"
      "   - 绝对不要用python_execute直接运行跑批脚本！\\n"
      "\\n"
      "【第3步】监控进度（循环执行，直到完成）：\\n"
      "   - 每30秒调用一次 batch_run(action=progress, pid=PID) 查看进度\\n"
      "   - 或直接读取实时日志文件（路径在batch_run返回结果中）\\n"
      "   - 进度更新时调用 status_monitor 更新状态\\n"
      "\\n"
      "【第4步】任务完成（必须同时调用3个工具）：\\n"
      "   - status_monitor(action=update, status=completed, task=鹿鼎记第X章跑批, step=完成, detail=跑批完成)\\n"
      "   - usage_monitor(channel=all)  查询最终API用量\\n"
      "   - notify_feishu(text=【监控】跑批完成：鹿鼎记第X章, type=text)  发送完成通知\\n"
      "\\n"
      "【第5步】整理报告：\\n"
      "   - 读取跑批结果文件，整理为结构化报告\\n"
      "   - 报告保存到 logs/task_report_YYYYMMDD_HHMMSS.txt\\n"
      "   - 调用 terminate(status=success) 结束任务\\n"
      "\\n"
      "【工具调用示例】\\n"
      "示例1 - 启动跑批：\\n"
      "  batch_run(book=鹿鼎记, chapter=3, mode=pure_data)\\n"
      "  返回：ok=True, started=True, pid=12345, log_path=logs/batch_run_ch3_20260905_200000.log\\n"
      "\\n"
      "示例2 - 查询进度：\\n"
      "  batch_run(action=progress, pid=12345)\\n"
      "  返回：ok=True, running=True, progress=第3天/共6天, current_day=3, total_days=6\\n"
      "\\n"
      "示例3 - 状态更新：\\n"
      "  status_monitor(action=update, status=running, task=鹿鼎记第3章跑批, step=第2天分析中, detail=豆包标签处理中)\\n"
      "\\n"
      "【重要提醒】\\n"
      " - 跑批任务中，batch_run是唯一能启动跑批的工具，不要尝试其他方式\\n"
      " - batch_run启动后立即返回，不要等待它完成，用progress查询进度\\n"
      " - 如果batch_run返回错误，先诊断原因（检查路径、Python环境、三个标签Chrome状态），然后重试\\n"
      " - 跑批过程中如果发现标签异常，调用 bridge_health(action=check) 诊断，必要时调用 bridge_health(action=restart) 恢复\\n"
  )'''

if old in content:
    content = content.replace(old, new)
    with open('app/prompt/manus.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('修改成功')
else:
    print('未找到匹配字符串')
    # 打印最后几行
    lines = content.split('\n')
    for i, line in enumerate(lines[-5:]):
        print(f'{len(lines)-5+i}: {repr(line)}')
