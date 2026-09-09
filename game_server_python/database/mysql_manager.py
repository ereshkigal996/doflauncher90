"""
MySQL进程管理模块
负责便携版MySQL的启动、停止和状态检查
"""

import os
import sys
import time
import socket
import subprocess
import threading
from typing import Optional, Tuple


class MySQLManager:
    """MySQL进程管理器"""
    
    def __init__(self, server_root: str, mysql_config: dict):
        """
        初始化MySQL管理器
        
        Args:
            server_root: 服务端根目录
            mysql_config: MySQL配置字典，包含host, port, user, password等
        """
        self.server_root = server_root
        self.mysql_config = mysql_config
        self.host = mysql_config.get('host', '127.0.0.1')
        self.port = mysql_config.get('port', 13306)
        
        # MySQL相关路径（支持多种目录结构）
        self.mysql_dir = self._find_mysql_dir(server_root)
        self.mysqld_exe = os.path.join(self.mysql_dir, 'server', 'bin', 'mysqld.exe')
        self.mysql_data = os.path.join(self.mysql_dir, 'data')
        
        # 进程相关
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._started_by_manager = False
    
    def _find_mysql_dir(self, server_root: str) -> str:
        """
        检测MySQL目录，支持多种目录结构
        
        优先级：
        1. server_root/runtime/mysql （原版服务端结构）
        2. server_root/mysql （发布目录结构）
        3. 程序所在目录/mysql （打包后结构）
        
        Args:
            server_root: 服务端根目录
            
        Returns:
            str: MySQL目录路径
        """
        candidates = [
            os.path.join(server_root, 'runtime', 'mysql'),
            os.path.join(server_root, 'mysql'),
        ]
        
        # 如果是打包后的程序，也检查程序所在目录
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, 'mysql'))
        
        for candidate in candidates:
            mysqld = os.path.join(candidate, 'server', 'bin', 'mysqld.exe')
            if os.path.exists(mysqld):
                return candidate
        
        # 如果都没找到，返回第一个候选（默认）
        return candidates[0]
    
    def is_installed(self) -> bool:
        """检查MySQL是否已安装"""
        return os.path.exists(self.mysqld_exe) and os.path.exists(self.mysql_data)
    
    def is_running(self, timeout: float = 2.0) -> bool:
        """
        检查MySQL是否正在运行（通过端口检测）
        
        Args:
            timeout: 连接超时时间
            
        Returns:
            bool: MySQL是否正在运行
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def start(self, wait_timeout: int = 30) -> Tuple[bool, str]:
        """
        启动MySQL
        
        Args:
            wait_timeout: 等待MySQL启动的超时时间（秒）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._lock:
            # 检查是否已经在运行
            if self.is_running():
                print("[MySQLManager] MySQL已经在运行中")
                self._started_by_manager = False
                return True, "MySQL已经在运行中"
            
            # 检查MySQL是否已安装
            if not self.is_installed():
                error_msg = f"MySQL未安装，缺少文件: {self.mysqld_exe} 或 {self.mysql_data}"
                print(f"[MySQLManager] 错误: {error_msg}")
                return False, error_msg
            
            print(f"[MySQLManager] 正在启动MySQL...")
            print(f"[MySQLManager] 可执行文件: {self.mysqld_exe}")
            print(f"[MySQLManager] 数据目录: {self.mysql_data}")
            print(f"[MySQLManager] 端口: {self.port}")
            
            try:
                # 启动MySQL（隐藏窗口）
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                self._process = subprocess.Popen(
                    [
                        self.mysqld_exe,
                        f'--datadir={self.mysql_data}',
                        f'--port={self.port}',
                        f'--bind-address={self.host}',
                        '--console'
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                self._started_by_manager = True
                print(f"[MySQLManager] MySQL进程已启动，PID: {self._process.pid}")
                
                # 等待MySQL启动完成
                print(f"[MySQLManager] 等待MySQL启动（最多{wait_timeout}秒）...")
                for i in range(wait_timeout):
                    time.sleep(1)
                    if self.is_running(timeout=1.0):
                        print(f"[MySQLManager] MySQL启动成功！耗时: {i+1}秒")
                        return True, "MySQL启动成功"
                    
                    # 检查进程是否还在运行
                    if self._process.poll() is not None:
                        error_msg = f"MySQL进程意外退出，返回码: {self._process.returncode}"
                        print(f"[MySQLManager] 错误: {error_msg}")
                        # 尝试读取输出
                        try:
                            output = self._process.stdout.read().decode('utf-8', errors='ignore')
                            if output:
                                print(f"[MySQLManager] 进程输出:\n{output[-1000:]}")
                        except Exception:
                            pass
                        return False, error_msg
                
                error_msg = f"MySQL启动超时（{wait_timeout}秒）"
                print(f"[MySQLManager] 错误: {error_msg}")
                return False, error_msg
                
            except Exception as e:
                error_msg = f"启动MySQL失败: {str(e)}"
                print(f"[MySQLManager] 错误: {error_msg}")
                return False, error_msg
    
    def stop(self, wait_timeout: int = 10) -> Tuple[bool, str]:
        """
        停止MySQL
        
        Args:
            wait_timeout: 等待MySQL停止的超时时间（秒）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._lock:
            # 如果不是由管理器启动的，不主动停止
            if not self._started_by_manager:
                print("[MySQLManager] MySQL不是由本管理器启动的，跳过停止")
                return True, "MySQL不是由本管理器启动的"
            
            # 检查是否在运行
            if not self.is_running():
                print("[MySQLManager] MySQL未在运行")
                self._started_by_manager = False
                self._process = None
                return True, "MySQL未在运行"
            
            print("[MySQLManager] 正在停止MySQL...")
            
            # 首先尝试优雅停止（通过进程终止）
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                    print("[MySQLManager] 已发送终止信号")
                except Exception as e:
                    print(f"[MySQLManager] 终止进程失败: {e}")
            
            # 等待进程退出
            for i in range(wait_timeout):
                time.sleep(1)
                if not self.is_running(timeout=1.0):
                    print(f"[MySQLManager] MySQL已停止，耗时: {i+1}秒")
                    self._started_by_manager = False
                    self._process = None
                    return True, "MySQL已停止"
            
            # 如果还在运行，强制终止
            print("[MySQLManager] MySQL未在超时时间内停止，尝试强制终止...")
            if self._process and self._process.poll() is None:
                try:
                    self._process.kill()
                    print("[MySQLManager] 已强制终止进程")
                except Exception as e:
                    print(f"[MySQLManager] 强制终止失败: {e}")
            
            # 再等一下
            time.sleep(2)
            
            if not self.is_running():
                print("[MySQLManager] MySQL已强制停止")
                self._started_by_manager = False
                self._process = None
                return True, "MySQL已强制停止"
            else:
                error_msg = "MySQL停止失败，请手动终止mysqld.exe进程"
                print(f"[MySQLManager] 错误: {error_msg}")
                return False, error_msg
    
    def get_status(self) -> dict:
        """获取MySQL状态"""
        return {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'host': self.host,
            'port': self.port,
            'mysqld_path': self.mysqld_exe,
            'data_path': self.mysql_data,
            'started_by_manager': self._started_by_manager,
            'pid': self._process.pid if self._process else None
        }


# 单例模式
_mysql_manager: Optional[MySQLManager] = None


def init_mysql_manager(server_root: str, mysql_config: dict) -> MySQLManager:
    """初始化MySQL管理器"""
    global _mysql_manager
    _mysql_manager = MySQLManager(server_root, mysql_config)
    return _mysql_manager


def get_mysql_manager() -> Optional[MySQLManager]:
    """获取MySQL管理器实例"""
    return _mysql_manager
