"""
进程管理模块
负责服务端进程的启动、停止、监控
"""

import os
import sys
import time
import json
import signal
import subprocess
import threading
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ProcessStatus(Enum):
    """进程状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ProcessInfo:
    """进程信息"""
    name: str = ""
    pid: int = 0
    executable: str = ""
    arguments: List[str] = field(default_factory=list)
    working_dir: str = ""
    status: ProcessStatus = ProcessStatus.STOPPED
    start_time: float = 0
    stop_time: float = 0
    exit_code: Optional[int] = None
    stdout_path: str = ""
    stderr_path: str = ""
    user_data: Dict[str, Any] = field(default_factory=dict)


class ProcessManager:
    """进程管理器"""
    
    def __init__(self, state_dir: str = "state", logs_dir: str = "logs"):
        self.state_dir = state_dir
        self.logs_dir = logs_dir
        self._processes: Dict[str, ProcessInfo] = {}
        self._subprocesses: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        
        # 确保目录存在
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录存在"""
        for dir_path in [self.state_dir, self.logs_dir]:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    print(f"[ProcessManager] 创建目录失败: {dir_path}, 错误: {e}")
    
    def start_process(
        self,
        name: str,
        executable: str,
        arguments: List[str] = None,
        working_dir: str = "",
        env: Dict[str, str] = None,
    ) -> Tuple[bool, str]:
        """启动进程"""
        if arguments is None:
            arguments = []
        
        with self._lock:
            # 检查进程是否已在运行
            if name in self._processes:
                info = self._processes[name]
                if info.status == ProcessStatus.RUNNING or info.status == ProcessStatus.STARTING:
                    return False, f"进程 {name} 已在运行中"
            
            # 检查可执行文件是否存在
            if not os.path.exists(executable):
                return False, f"可执行文件不存在: {executable}"
            
            # 构建命令
            cmd = [executable] + arguments
            
            # 准备环境变量
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # 准备工作目录
            cwd = working_dir if working_dir else os.path.dirname(executable)
            
            # 准备日志文件
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            stdout_path = os.path.join(self.logs_dir, f"{name}-{timestamp}.stdout.log")
            stderr_path = os.path.join(self.logs_dir, f"{name}-{timestamp}.stderr.log")
            
            try:
                # 打开日志文件
                stdout_file = open(stdout_path, 'w', encoding='utf-8')
                stderr_file = open(stderr_path, 'w', encoding='utf-8')
                
                # 启动进程
                proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    env=process_env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                )
                
                # 保存进程信息
                info = ProcessInfo(
                    name=name,
                    pid=proc.pid,
                    executable=executable,
                    arguments=arguments,
                    working_dir=cwd,
                    status=ProcessStatus.STARTING,
                    start_time=time.time(),
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )
                
                self._processes[name] = info
                self._subprocesses[name] = proc
                
                # 保存状态文件
                self._save_state(name)
                
                print(f"[ProcessManager] 进程启动成功: {name} (PID: {proc.pid})")
                print(f"[ProcessManager] 命令: {' '.join(cmd)}")
                print(f"[ProcessManager] 工作目录: {cwd}")
                print(f"[ProcessManager] 标准输出: {stdout_path}")
                print(f"[ProcessManager] 标准错误: {stderr_path}")
                
                # 启动监控线程
                self._start_monitor()
                
                return True, f"进程 {name} 启动成功 (PID: {proc.pid})"
                
            except Exception as e:
                print(f"[ProcessManager] 进程启动失败: {name}, 错误: {e}")
                return False, f"进程启动失败: {e}"
    
    def stop_process(self, name: str, force: bool = False, timeout: int = 30) -> Tuple[bool, str]:
        """停止进程"""
        with self._lock:
            if name not in self._processes:
                return False, f"进程 {name} 不存在"
            
            info = self._processes[name]
            if info.status != ProcessStatus.RUNNING and info.status != ProcessStatus.STARTING:
                return False, f"进程 {name} 未在运行中"
            
            proc = self._subprocesses.get(name)
            if not proc:
                return False, f"进程 {name} 的子进程对象不存在"
            
            # 更新状态
            info.status = ProcessStatus.STOPPING
            
            try:
                if force:
                    # 强制终止
                    proc.kill()
                else:
                    # 优雅终止
                    if sys.platform == 'win32':
                        proc.terminate()
                    else:
                        proc.send_signal(signal.SIGTERM)
                    
                    # 等待进程退出
                    try:
                        proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        print(f"[ProcessManager] 进程 {name} 优雅终止超时，强制终止")
                        proc.kill()
                        proc.wait(timeout=5)
                
                # 更新状态
                info.status = ProcessStatus.STOPPED
                info.stop_time = time.time()
                info.exit_code = proc.returncode
                
                # 移除子进程对象
                if name in self._subprocesses:
                    del self._subprocesses[name]
                
                # 保存状态
                self._save_state(name)
                
                print(f"[ProcessManager] 进程停止成功: {name} (退出码: {info.exit_code})")
                return True, f"进程 {name} 停止成功"
                
            except Exception as e:
                print(f"[ProcessManager] 进程停止失败: {name}, 错误: {e}")
                info.status = ProcessStatus.ERROR
                return False, f"进程停止失败: {e}"
    
    def get_process_info(self, name: str) -> Optional[ProcessInfo]:
        """获取进程信息"""
        with self._lock:
            return self._processes.get(name)
    
    def is_running(self, name: str) -> bool:
        """检查进程是否在运行"""
        info = self.get_process_info(name)
        if not info:
            return False
        return info.status == ProcessStatus.RUNNING
    
    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """获取所有进程信息"""
        with self._lock:
            return self._processes.copy()
    
    def _start_monitor(self):
        """启动监控线程"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print("[ProcessManager] 进程监控线程已启动")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                with self._lock:
                    for name, proc in list(self._subprocesses.items()):
                        if name not in self._processes:
                            continue
                        
                        info = self._processes[name]
                        
                        # 检查进程是否已退出
                        if proc.poll() is not None:
                            info.status = ProcessStatus.STOPPED
                            info.stop_time = time.time()
                            info.exit_code = proc.returncode
                            
                            print(f"[ProcessManager] 检测到进程退出: {name} (退出码: {info.exit_code})")
                            
                            # 保存状态
                            self._save_state(name)
                            
                            # 移除子进程对象
                            del self._subprocesses[name]
                        
                        # 更新STARTING状态为RUNNING（启动后2秒）
                        elif info.status == ProcessStatus.STARTING:
                            if time.time() - info.start_time > 2:
                                info.status = ProcessStatus.RUNNING
                                print(f"[ProcessManager] 进程启动完成: {name}")
                
                # 每秒检查一次
                time.sleep(1)
                
            except Exception as e:
                print(f"[ProcessManager] 监控循环异常: {e}")
                time.sleep(1)
    
    def _save_state(self, name: str):
        """保存进程状态到文件"""
        if name not in self._processes:
            return
        
        info = self._processes[name]
        state_file = os.path.join(self.state_dir, f"{name}-process.json")
        
        try:
            state_data = {
                'name': info.name,
                'pid': info.pid,
                'executable': info.executable,
                'arguments': info.arguments,
                'working_dir': info.working_dir,
                'status': info.status.value,
                'start_time': info.start_time,
                'stop_time': info.stop_time,
                'exit_code': info.exit_code,
                'stdout_path': info.stdout_path,
                'stderr_path': info.stderr_path,
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[ProcessManager] 保存状态失败: {name}, 错误: {e}")
    
    def stop_all(self, force: bool = False):
        """停止所有进程"""
        print("[ProcessManager] 正在停止所有进程...")
        with self._lock:
            names = list(self._processes.keys())
        
        for name in names:
            self.stop_process(name, force=force)
        
        self._monitoring = False
        print("[ProcessManager] 所有进程已停止")
    
    def close(self):
        """关闭进程管理器"""
        self.stop_all(force=True)
        self._monitoring = False


# 全局进程管理器实例
_process_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    """获取全局进程管理器实例"""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager


def init_process_manager(state_dir: str = "state", logs_dir: str = "logs") -> ProcessManager:
    """初始化全局进程管理器"""
    global _process_manager
    _process_manager = ProcessManager(state_dir, logs_dir)
    return _process_manager
