# -*- coding: utf-8 -*-
"""
便携版MySQL管理模块
对应Go版 portable_mysql.go
"""

import os
import json
import time
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from datetime import datetime

from core.paths import ProjectPaths
from modules.process_manager import ProcessManager, ProcessState


@dataclass
class MySQLConfig:
    """MySQL配置"""
    host: str = "127.0.0.1"
    port: int = 13306
    name: str = "dnf_local"
    user: str = "root"
    password: str = ""
    data_dir: str = ""
    base_dir: str = ""


@dataclass
class MySQLState:
    """MySQL状态"""
    status: str = "STOPPED"  # STOPPED / STARTING / RUNNING
    pid: int = 0
    port: int = 13306
    data_dir: str = ""
    start_time: str = ""
    error: str = ""


class MySQLManager:
    """便携版MySQL管理器"""
    
    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self.process_mgr = ProcessManager(paths.project_root)
        self.config = MySQLConfig()
    
    def load_config(self) -> Tuple[bool, Optional[str]]:
        """从instance.json加载MySQL配置"""
        try:
            config_path = self.paths.instance
            if not os.path.isfile(config_path):
                return False, f"config not found: {config_path}"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            db = data.get("database", {})
            self.config.host = db.get("host", "127.0.0.1")
            self.config.port = db.get("port", 13306)
            self.config.name = db.get("name", "dnf_local")
            self.config.user = db.get("user", "root")
            self.config.password = db.get("password", "")
            self.config.data_dir = self.paths.mysql_data
            self.config.base_dir = self.paths.mysql_server
            
            return True, None
        except Exception as e:
            return False, f"load mysql config failed: {e}"
    
    def is_installed(self) -> bool:
        """检查MySQL是否已安装"""
        return (os.path.isfile(self.paths.mysqld_exe) and 
                os.path.isfile(self.paths.mysql_install_state))
    
    def is_data_initialized(self) -> bool:
        """检查数据目录是否已初始化"""
        return (os.path.isdir(self.paths.mysql_data) and 
                os.path.isfile(os.path.join(self.paths.mysql_data, "auto.cnf")))
    
    def check_health(self, timeout: int = 30) -> Tuple[bool, Optional[str]]:
        """
        检查MySQL健康状态
        尝试连接MySQL
        """
        import socket
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    result = s.connect_ex((self.config.host, self.config.port))
                    if result == 0:
                        return True, None
            except Exception:
                pass
            time.sleep(1)
        
        return False, f"MySQL not responding on {self.config.host}:{self.config.port}"
    
    def start(self, wait: bool = True, timeout: int = 60) -> Tuple[bool, Optional[str]]:
        """
        启动MySQL
        """
        # 检查是否已在运行
        if self.is_running():
            return True, "MySQL already running"
        
        # 检查mysqld是否存在
        if not os.path.isfile(self.paths.mysqld_exe):
            return False, f"mysqld not found: {self.paths.mysqld_exe}"
        
        # 检查数据目录
        if not self.is_data_initialized():
            ok, err = self.initialize_data()
            if not ok:
                return False, f"data init failed: {err}"
        
        try:
            # 构建启动参数
            args = [
                f"--basedir={self.paths.mysql_server}",
                f"--datadir={self.paths.mysql_data}",
                f"--port={self.config.port}",
                f"--bind-address={self.config.host}",
                "--skip-name-resolve",
                "--skip-networking=0",
            ]
            
            # 启动MySQL
            pid, err = self.process_mgr.start_process(
                self.paths.mysqld_exe,
                args=args,
                working_dir=self.paths.mysql_root,
                wait=False
            )
            
            if err:
                return False, f"start mysqld failed: {err}"
            
            # 保存进程状态
            state = ProcessState(
                pid=pid,
                name="mysqld.exe",
                exe_path=self.paths.mysqld_exe,
                start_time=datetime.now().isoformat(),
                status="STARTING"
            )
            self.process_mgr.save_process_state(self.paths.mysql_process_state, state)
            
            if wait:
                # 等待MySQL就绪
                ok, err = self.check_health(timeout)
                if ok:
                    state.status = "RUNNING"
                    self.process_mgr.save_process_state(self.paths.mysql_process_state, state)
                    return True, None
                else:
                    return False, f"MySQL start timeout: {err}"
            
            return True, None
            
        except Exception as e:
            return False, f"start MySQL failed: {e}"
    
    def stop(self, keep_database: bool = False, timeout: int = 30) -> Tuple[bool, Optional[str]]:
        """
        停止MySQL
        """
        # 加载进程状态
        state, err = self.process_mgr.load_process_state(self.paths.mysql_process_state)
        if err or not state:
            # 尝试按名称查找
            processes = self.process_mgr.find_process_by_name("mysqld.exe")
            if processes:
                state = ProcessState(pid=processes[0].pid, name="mysqld.exe")
            else:
                return True, "MySQL not running"
        
        if state.pid == 0:
            return True, "MySQL not running"
        
        # 停止进程
        ok, err = self.process_mgr.stop_process(state.pid, force=True, timeout=timeout)
        if not ok:
            return False, f"stop MySQL failed: {err}"
        
        # 更新状态
        state.status = "STOPPED"
        state.pid = 0
        self.process_mgr.save_process_state(self.paths.mysql_process_state, state)
        
        return True, None
    
    def initialize_data(self) -> Tuple[bool, Optional[str]]:
        """
        初始化MySQL数据目录
        """
        if self.is_data_initialized():
            return True, "already initialized"
        
        try:
            # 确保数据目录存在
            os.makedirs(self.paths.mysql_data, exist_ok=True)
            
            # 运行mysqld --initialize
            args = [
                f"--basedir={self.paths.mysql_server}",
                f"--datadir={self.paths.mysql_data}",
                "--initialize-insecure",
                "--console",
            ]
            
            result = subprocess.run(
                [self.paths.mysqld_exe] + args,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return False, f"initialize failed: {result.stderr}"
            
            # 保存安装状态
            install_state = {
                "installedAt": datetime.now().isoformat(),
                "version": "8.0",
                "dataDir": self.paths.mysql_data,
            }
            with open(self.paths.mysql_install_state, 'w', encoding='utf-8') as f:
                json.dump(install_state, f, ensure_ascii=False, indent=2)
            
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "initialize timeout"
        except Exception as e:
            return False, f"initialize failed: {e}"
    
    def is_running(self) -> bool:
        """检查MySQL是否在运行"""
        # 先检查进程状态文件
        state, _ = self.process_mgr.load_process_state(self.paths.mysql_process_state)
        if state and state.pid > 0:
            if self.process_mgr.is_process_running(state.pid):
                return True
        
        # 按名称查找
        processes = self.process_mgr.find_process_by_name("mysqld.exe")
        return len(processes) > 0
    
    def get_status(self) -> MySQLState:
        """获取MySQL状态"""
        state = MySQLState()
        state.port = self.config.port
        state.data_dir = self.paths.mysql_data
        
        if self.is_running():
            state.status = "RUNNING"
            proc_state, _ = self.process_mgr.load_process_state(self.paths.mysql_process_state)
            if proc_state:
                state.pid = proc_state.pid
                state.start_time = proc_state.start_time
        else:
            state.status = "STOPPED"
        
        return state
    
    def backup_data(self, backup_dir: str = None) -> Tuple[bool, Optional[str]]:
        """备份MySQL数据目录"""
        if not backup_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.paths.mysql_root, f"data_old_{timestamp}")
        
        try:
            if os.path.exists(self.paths.mysql_data):
                shutil.copytree(self.paths.mysql_data, backup_dir)
                return True, backup_dir
            return False, "data directory not found"
        except Exception as e:
            return False, f"backup failed: {e}"
    
    def execute_query(self, query: str, database: str = None) -> Tuple[Optional[list], Optional[str]]:
        """
        执行SQL查询（需要mysql客户端）
        """
        mysql_exe = os.path.join(self.paths.mysql_server, "bin", "mysql.exe")
        if not os.path.isfile(mysql_exe):
            return None, "mysql client not found"
        
        try:
            args = [
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                f"--user={self.config.user}",
            ]
            if self.config.password:
                args.append(f"--password={self.config.password}")
            if database:
                args.append(database)
            args.extend(["-e", query])
            
            result = subprocess.run(
                [mysql_exe] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return None, result.stderr
            
            # 解析结果
            rows = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    rows.append(line.split('\t'))
            
            return rows, None
            
        except Exception as e:
            return None, f"query failed: {e}"
