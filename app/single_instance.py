# -*- coding: utf-8 -*-
"""
single_instance.py · OpenManus统帅单实例锁
============================================
防止多个统帅进程同时运行，导致资源竞争和API调用混乱。

使用方法：
    from app.single_instance import SingleInstance
    
    lock = SingleInstance("openmanus")
    if not lock.acquire():
        print("已有统帅实例在运行，退出")
        sys.exit(1)
    
    # ... 正常运行 ...
    
    lock.release()  # 退出时释放
"""
import os
import sys
import time
import json
import tempfile
from datetime import datetime


class SingleInstance:
    """单实例锁（Windows兼容，用文件锁+PID验证）"""
    
    def __init__(self, name: str, lock_dir: str = None):
        self.name = name
        if lock_dir is None:
            lock_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        self.lock_dir = os.path.abspath(lock_dir)
        self.lock_file = os.path.join(self.lock_dir, f"{name}.pid")
        self._lock_fd = None
        self._pid = os.getpid()
    
    def acquire(self) -> bool:
        """获取单实例锁。成功返回True，已有实例运行返回False。"""
        os.makedirs(self.lock_dir, exist_ok=True)
        
        # 检查是否已有锁文件
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                old_pid = data.get("pid", 0)
                old_start = data.get("start_time", "")
                
                # 验证旧进程是否还在运行
                if self._is_process_running(old_pid):
                    print(f"[单实例锁] 已有统帅实例在运行 (PID={old_pid}, 启动于{old_start})")
                    return False
                else:
                    print(f"[单实例锁] 发现残留锁文件(PID={old_pid}已退出)，清理后继续")
                    os.remove(self.lock_file)
            except (json.JSONDecodeError, KeyError, OSError):
                # 锁文件损坏，清理
                print("[单实例锁] 锁文件损坏，清理后继续")
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass
        
        # 创建锁文件（Windows下用排他模式）
        try:
            # Windows: 使用os.O_CREAT | os.O_EXCL确保原子创建
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            self._lock_fd = fd
            data = {
                "pid": self._pid,
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "name": self.name
            }
            os.write(fd, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
            os.fsync(fd)
            print(f"[单实例锁] 获取成功，PID={self._pid}")
            return True
        except FileExistsError:
            # 竞态条件：另一个进程刚创建了锁文件
            print("[单实例锁] 另一个实例刚刚启动，退出")
            return False
        except Exception as e:
            print(f"[单实例锁] 创建锁文件失败: {e}")
            return False
    
    def release(self):
        """释放锁"""
        if self._lock_fd is not None:
            try:
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                print(f"[单实例锁] 已释放，PID={self._pid}")
        except OSError as e:
            print(f"[单实例锁] 删除锁文件失败: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行（跨平台）"""
        if pid <= 0:
            return False
        try:
            # Windows: 用tasklist检查
            if sys.platform == "win32":
                import subprocess
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            else:
                # Unix: 发送信号0
                os.kill(pid, 0)
                return True
        except Exception:
            return False
    
    def __enter__(self):
        if not self.acquire():
            sys.exit(1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


def get_running_instance(name: str = "openmanus") -> dict:
    """获取当前运行的实例信息"""
    lock_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    lock_file = os.path.join(lock_dir, f"{name}.pid")
    if not os.path.exists(lock_file):
        return None
    try:
        with open(lock_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    # 测试
    lock = SingleInstance("test")
    if lock.acquire():
        print("获取锁成功，按Ctrl+C退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            lock.release()
    else:
        print("已有实例在运行")
