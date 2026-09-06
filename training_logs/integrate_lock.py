# -*- coding: utf-8 -*-
"""在openmanus_runner.py中集成单实例锁"""

with open('openmanus_runner.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在import部分添加single_instance
old_import = "from pathlib import Path"
new_import = """from pathlib import Path

# ============ 单实例锁（2026-09-05添加，防止多个统帅进程同时运行）============
try:
    from app.single_instance import SingleInstance
except ImportError:
    SingleInstance = None
"""

if old_import in content and "single_instance" not in content:
    content = content.replace(old_import, new_import)
    print("已添加single_instance import")
else:
    print("import已存在或未找到")

# 2. 在main函数开头添加单实例锁检查
# 找到main函数的定义
old_main_start = "def main():"
if old_main_start in content:
    # 在main函数的第一行添加单实例锁
    # 先找到main函数后面的第一行代码
    lines = content.split('\n')
    in_main = False
    main_start_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == "def main():":
            main_start_idx = i
            in_main = True
            continue
        if in_main and line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
            # 找到main函数的第一行实际代码
            indent = line[:len(line) - len(line.lstrip())]
            lock_code = f'''{indent}# ============ 单实例锁检查 ============
{indent}_lock = None
{indent}if SingleInstance:
{indent}    _lock = SingleInstance("openmanus")
{indent}    if not _lock.acquire():
{indent}        logger.error("已有统帅实例在运行，退出。请先停止旧实例再启动新任务。")
{indent}        sys.exit(1)
{indent}else:
{indent}    logger.warning("单实例锁模块未找到，跳过检查")
{indent}
'''
            lines.insert(i, lock_code)
            content = '\n'.join(lines)
            print("已在main函数开头添加单实例锁检查")
            break
else:
    print("未找到main函数")

# 3. 在main函数结尾添加锁释放（在sys.exit之前）
# 找到所有sys.exit的地方，在之前添加锁释放
if "_lock" in content:
    # 在程序退出前释放锁
    old_exit = "    sys.exit(0)"
    new_exit = '''    if _lock:
        _lock.release()
    sys.exit(0)'''
    if old_exit in content and "_lock.release()" not in content:
        content = content.replace(old_exit, new_exit)
        print("已添加锁释放")

with open('openmanus_runner.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修改完成")
