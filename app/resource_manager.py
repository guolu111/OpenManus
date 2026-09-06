# -*- coding: utf-8 -*-
"""
resource_manager.py · 全局资源锁与Chrome实例隔离
====================================================
P0核心稳定性 - 解决多角色并行调用时的Chrome Profile冲突和端口冲突问题

设计原则（来自智谱工程优化建议）：
- ResourceManager单例类，维护Browser实例池或信号量
- 并行模式下强制限制同时运行的Browser数量（设为1-2）
- 确保launch_persistent_context启动的Chrome实例在任务期间独占
- 任务结束后清理或挂起，避免资源争抢

经验包参考：
- bridge使用launch_persistent_context启动Chrome实例，独占一个User Data Directory
- MultiRoleOrchestrator支持并行模式，如果两个角色同时调用需要浏览器的工具，
  且没有全局锁机制，会尝试写入同一个Profile或产生端口冲突，导致进程崩溃或数据污染
"""
import asyncio
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager


class ResourceManager:
    """全局资源管理器（单例模式）
    
    管理Browser实例、Chrome Profile、端口等稀缺资源的并发访问。
    确保多角色并行调用时不会产生资源冲突。
    """
    
    _instance: Optional["ResourceManager"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_concurrent_browsers: int = 1):
        """初始化资源管理器
        
        Args:
            max_concurrent_browsers: 最大并发浏览器数量，默认1（最安全，避免Profile冲突）
        """
        if self._initialized:
            return
        self._initialized = True
        
        self.max_concurrent_browsers = max_concurrent_browsers
        self._browser_semaphore = asyncio.Semaphore(max_concurrent_browsers)
        self._profile_locks: Dict[str, asyncio.Lock] = {}
        self._port_locks: Dict[int, asyncio.Lock] = {}
        self._active_resources: Dict[str, Dict[str, Any]] = {}
        self._resource_lock = asyncio.Lock()
        
        print(f"  [ResourceManager] 初始化完成，最大并发浏览器: {max_concurrent_browsers}")
    
    @classmethod
    def get_instance(cls) -> "ResourceManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @asynccontextmanager
    async def acquire_browser(self, purpose: str = "default", timeout: float = 300.0):
        """获取浏览器资源（信号量控制并发数）
        
        Args:
            purpose: 用途描述（用于日志）
            timeout: 超时时间（秒），默认300秒
        
        Yields:
            dict: 包含resource_id和acquired_time的字典
        
        Example:
            async with resource_manager.acquire_browser("角色A跑批") as res:
                # 执行需要浏览器的任务
                pass
        """
        resource_id = f"browser_{purpose}_{int(time.time() * 1000)}"
        start_time = time.time()
        
        try:
            # 等待信号量（控制并发数）
            await asyncio.wait_for(self._browser_semaphore.acquire(), timeout=timeout)
            
            async with self._resource_lock:
                self._active_resources[resource_id] = {
                    "type": "browser",
                    "purpose": purpose,
                    "acquired_time": time.time(),
                }
            
            print(f"  [ResourceManager] ✓ 获取浏览器资源: {purpose} (等待{time.time()-start_time:.1f}s)")
            
            yield {
                "resource_id": resource_id,
                "acquired_time": start_time,
                "purpose": purpose,
            }
        finally:
            # 释放信号量
            self._browser_semaphore.release()
            
            async with self._resource_lock:
                if resource_id in self._active_resources:
                    del self._active_resources[resource_id]
            
            print(f"  [ResourceManager] ✓ 释放浏览器资源: {purpose} (使用{time.time()-start_time:.1f}s)")
    
    @asynccontextmanager
    async def acquire_profile(self, profile_path: str, timeout: float = 300.0):
        """获取Chrome Profile独占锁
        
        确保同一个Profile不会被多个任务同时写入，避免数据污染。
        
        Args:
            profile_path: Chrome Profile路径
            timeout: 超时时间（秒）
        
        Example:
            async with resource_manager.acquire_profile("/path/to/profile"):
                # 启动使用该Profile的浏览器
                pass
        """
        if profile_path not in self._profile_locks:
            self._profile_locks[profile_path] = asyncio.Lock()
        
        lock = self._profile_locks[profile_path]
        start_time = time.time()
        
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            print(f"  [ResourceManager] ✓ 获取Profile锁: {profile_path[-30:]} (等待{time.time()-start_time:.1f}s)")
            yield
        finally:
            lock.release()
            print(f"  [ResourceManager] ✓ 释放Profile锁: {profile_path[-30:]} (使用{time.time()-start_time:.1f}s)")
    
    @asynccontextmanager
    async def acquire_port(self, port: int, timeout: float = 60.0):
        """获取端口独占锁
        
        确保同一个端口不会被多个服务同时绑定。
        
        Args:
            port: 端口号
            timeout: 超时时间（秒）
        """
        if port not in self._port_locks:
            self._port_locks[port] = asyncio.Lock()
        
        lock = self._port_locks[port]
        start_time = time.time()
        
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            print(f"  [ResourceManager] ✓ 获取端口锁: {port} (等待{time.time()-start_time:.1f}s)")
            yield
        finally:
            lock.release()
            print(f"  [ResourceManager] ✓ 释放端口锁: {port} (使用{time.time()-start_time:.1f}s)")
    
    async def get_active_resources(self) -> Dict[str, Dict[str, Any]]:
        """获取当前活跃的资源列表（用于监控和调试）"""
        async with self._resource_lock:
            return dict(self._active_resources)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取资源管理器统计信息"""
        async with self._resource_lock:
            return {
                "max_concurrent_browsers": self.max_concurrent_browsers,
                "active_browsers": len([r for r in self._active_resources.values() if r["type"] == "browser"]),
                "active_profiles": len(self._profile_locks),
                "active_ports": len(self._port_locks),
                "active_resources": dict(self._active_resources),
            }


# 全局便捷函数
def init_resource_manager(max_concurrent_browsers: int = 1) -> ResourceManager:
    """初始化全局资源管理器（应用启动时调用）"""
    return ResourceManager(max_concurrent_browsers=max_concurrent_browsers)


def get_resource_manager() -> ResourceManager:
    """获取全局资源管理器实例"""
    return ResourceManager.get_instance()


# 全局网络超时控制（应用启动时第一行调用）
def setup_global_timeout(timeout_seconds: int = 180):
    """设置全局网络超时
    
    P0核心稳定性 - 防止长回复导致的线程阻塞和网络IO僵尸化
    
    经验包参考：
    - 长回复需要至少180秒超时
    - 必须同时设置socket.setdefaulttimeout，否则urllib的timeout可能不生效
    - 网络波动下如果没有全局超时，底层HTTP连接可能无限期挂起，导致线程池耗尽
    
    Args:
        timeout_seconds: 超时秒数，默认180秒（经验包验证的长回复所需时间）
    """
    import socket
    socket.setdefaulttimeout(timeout_seconds)
    print(f"  [GlobalTimeout] 全局网络超时已设置: {timeout_seconds}秒")
