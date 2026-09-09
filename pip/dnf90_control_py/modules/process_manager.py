# -*- coding: utf-8 -*-
"""
Windows进程管理模块
对应Go版 process_windows.go
"""

import os
import json
import time
import subprocess
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime


@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    exe_path: str
    start_time: str
    cmd_line: str = ""


@dataclass
class ProcessState:
    """进程状态（对应server-process.json）"""
    pid: int = 0
    name: str = ""
    exe_path: str = ""
    start_time: str = ""
    status: str = ""  # running / stopped
    log_file: str = ""


class ProcessManager:
    """进程管理器"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
    
    def find_process_by_name(self, process_name: str) -> List[ProcessInfo]:
        """按名称查找进程"""
        results = []
        try:
            # 使用tasklist命令
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {process_name}', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and process_name.lower() in line.lower():
                        parts = line.strip('"').split('","')
                        if len(parts) >= 2:
                            pid = int(parts[1])
                            results.append(ProcessInfo(
                                pid=pid,
                                name=parts[0],
                                exe_path="",
                                start_time=""
                            ))
        except Exception:
            pass
        return results
    
    def is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0 and str(pid) in result.stdout
        except Exception:
            return False
    
    def start_process(self, exe_path: str, args: List[str] = None, 
                      working_dir: str = None, wait: bool = False,
                      timeout: int = 30) -> Tuple[Optional[int], Optional[str]]:
        """
        启动进程
        返回: (pid, error)
        """
        if not os.path.isfile(exe_path):
            return None, f"executable not found: {exe_path}"
        
        try:
            cmd = [exe_path]
            if args:
                cmd.extend(args)
            
            if wait:
                result = subprocess.run(
                    cmd,
                    cwd=working_dir or self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return result.returncode, result.stderr if result.returncode != 0 else None
            else:
                # 后台启动，不等待
                proc = subprocess.Popen(
                    cmd,
                    cwd=working_dir or self.project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                return proc.pid, None
        except subprocess.TimeoutExpired:
            return None, "process start timeout"
        except Exception as e:
            return None, f"start process failed: {e}"
    
    def stop_process(self, pid: int, force: bool = False, timeout: int = 30) -> Tuple[bool, Optional[str]]:
        """
        停止进程
        """
        if not self.is_process_running(pid):
            return True, None  # 已经停止
        
        try:
            if force:
                result = subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid)],
                    capture_output=True, text=True, timeout=timeout
                )
            else:
                result = subprocess.run(
                    ['taskkill', '/PID', str(pid)],
                    capture_output=True, text=True, timeout=timeout
                )
            
            if result.returncode == 0:
                # 等待进程退出
                start = time.time()
                while time.time() - start < timeout:
                    if not self.is_process_running(pid):
                        return True, None
                    time.sleep(0.5)
                return False, "process did not exit in time"
            else:
                return False, result.stderr or "taskkill failed"
        except Exception as e:
            return False, f"stop process failed: {e}"
    
    def save_process_state(self, state_file: str, state: ProcessState) -> Tuple[bool, Optional[str]]:
        """保存进程状态到JSON文件"""
        try:
            data = {
                "pid": state.pid,
                "name": state.name,
                "exePath": state.exe_path,
                "startTime": state.start_time,
                "status": state.status,
                "logFile": state.log_file,
            }
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True, None
        except Exception as e:
            return False, f"save process state failed: {e}"
    
    def load_process_state(self, state_file: str) -> Tuple[Optional[ProcessState], Optional[str]]:
        """从JSON文件加载进程状态"""
        if not os.path.isfile(state_file):
            return None, "state file not found"
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = ProcessState(
                pid=data.get("pid", 0),
                name=data.get("name", ""),
                exe_path=data.get("exePath", ""),
                start_time=data.get("startTime", ""),
                status=data.get("status", ""),
                log_file=data.get("logFile", ""),
            )
            return state, None
        except Exception as e:
            return None, f"load process state failed: {e}"
    
    def get_local_ip(self) -> str:
        """获取本地局域网IP"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        """检查端口是否被占用"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
