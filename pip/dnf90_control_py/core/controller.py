# -*- coding: utf-8 -*-
"""
主控制器模块
对应Go版 controller.go
"""

import os
import sys
import json
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List
from datetime import datetime

from core.paths import ProjectPaths, discover_paths, ensure_directories
from core.config import InstanceConfig, load_instance_config
from modules.process_manager import ProcessManager, ProcessState
from modules.mysql_manager import MySQLManager
from modules.account_manager import AccountManager


@dataclass
class CheckOptions:
    """检查选项"""
    skip_database: bool = False
    skip_ports: bool = False
    check_client: bool = False


@dataclass
class ServerStatus:
    """服务端状态"""
    mysql_status: str = "STOPPED"
    server_status: str = "STOPPED"
    mysql_pid: int = 0
    server_pid: int = 0
    local_ip: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class Controller:
    """
    DNF90主控制器
    对应Go版 Controller
    """
    
    def __init__(self, paths: ProjectPaths, stdout=None, stderr=None):
        self.paths = paths
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.process_mgr = ProcessManager(paths.project_root)
        self.mysql_mgr = MySQLManager(paths)
        self.account_mgr = AccountManager(paths, self.mysql_mgr)
        self.config: Optional[InstanceConfig] = None
    
    def log(self, message: str):
        """输出日志"""
        print(message, file=self.stdout)
    
    def error(self, message: str):
        """输出错误"""
        print(f"FAILED: {message}", file=self.stderr)
    
    def load_config(self) -> Tuple[bool, Optional[str]]:
        """加载配置"""
        config, err = load_instance_config(self.paths.instance)
        if err:
            return False, err
        self.config = config
        return True, None
    
    def start(self, rebuild: bool = False) -> Tuple[bool, Optional[str]]:
        """
        启动服务端
        对应Go版 controller.start()
        """
        self.log("Starting DNF90 server...")
        
        # 1. 确保目录存在
        ok, err = ensure_directories(self.paths)
        if not ok:
            return False, err
        
        # 2. 加载配置
        ok, err = self.load_config()
        if not ok:
            return False, err
        
        # 3. 加载MySQL配置
        ok, err = self.mysql_mgr.load_config()
        if not ok:
            return False, err
        
        # 4. 获取本地IP
        local_ip = self.process_mgr.get_local_ip()
        self.log(f"Using local LAN IPv4 for 90cn game channels: {local_ip}")
        
        # 5. 检查资源文件
        ok, err = self._check_assets()
        if not ok:
            return False, err
        
        # 6. 启动MySQL
        self.log("Starting MySQL...")
        ok, err = self.mysql_mgr.start(wait=True, timeout=60)
        if not ok:
            return False, f"MySQL start failed: {err}"
        self.log("MySQL started successfully")
        
        # 7. 启动服务端
        self.log("Starting DNF90Server...")
        ok, err = self._start_server()
        if not ok:
            # 停止MySQL
            self.mysql_mgr.stop()
            return False, f"Server start failed: {err}"
        self.log("DNF90Server started successfully")
        
        self.log("Server started successfully!")
        return True, None
    
    def stop(self, keep_database: bool = False) -> Tuple[bool, Optional[str]]:
        """
        停止服务端
        对应Go版 controller.stop()
        """
        self.log("Stopping DNF90 server...")
        
        # 1. 停止服务端
        self.log("Stopping DNF90Server...")
        ok, err = self._stop_server()
        if not ok:
            self.log(f"Warning: server stop warning: {err}")
        self.log("DNF90Server stopped")
        
        # 2. 停止MySQL
        if not keep_database:
            self.log("Stopping MySQL...")
            ok, err = self.mysql_mgr.stop()
            if not ok:
                self.log(f"Warning: MySQL stop warning: {err}")
            self.log("MySQL stopped")
        
        self.log("Server stopped successfully!")
        return True, None
    
    def status(self) -> Tuple[bool, Optional[str]]:
        """
        查看状态
        对应Go版 controller.status()
        """
        # 加载配置
        self.load_config()
        self.mysql_mgr.load_config()
        
        # 获取本地IP
        local_ip = self.process_mgr.get_local_ip()
        self.log(f"Using local LAN IPv4 for 90cn game channels: {local_ip}")
        
        # 检查资源
        self._check_assets(log=True)
        
        # MySQL状态
        mysql_state = self.mysql_mgr.get_status()
        self.log(f"MySQL: {mysql_state.status}")
        
        # 服务端状态
        server_running = self._is_server_running()
        self.log(f"Server: {'RUNNING' if server_running else 'STOPPED'}")
        
        if not server_running:
            return False, "server is not running"
        
        return True, None
    
    def check(self, options: CheckOptions) -> Tuple[bool, Optional[str]]:
        """
        环境检查
        对应Go版 controller.check()
        """
        self.log("Running environment checks...")
        errors = []
        
        # 1. 检查项目结构
        ok, err = ensure_directories(self.paths)
        if not ok:
            errors.append(f"directory check failed: {err}")
        
        # 2. 检查配置
        ok, err = self.load_config()
        if not ok:
            errors.append(f"config check failed: {err}")
        
        # 3. 检查核心程序
        core_exes = [
            ("DNF90Server.exe", self.paths.server_exe),
            ("DNF90Control.exe", self.paths.control_exe),
            ("DNF90Doctor.exe", self.paths.doctor_exe),
        ]
        for name, path in core_exes:
            if not os.path.isfile(path):
                errors.append(f"missing executable: {name}")
        
        # 4. 检查资源文件
        ok, err = self._check_assets()
        if not ok:
            errors.append(f"asset check failed: {err}")
        
        # 5. 检查数据库
        if not options.skip_database:
            if self.config and self.config.database.mode == "portable":
                if not os.path.isfile(self.paths.mysqld_exe):
                    errors.append("missing mysqld.exe")
        
        # 6. 检查端口
        if not options.skip_ports and self.config:
            ports_to_check = [
                ("channel", self.config.server.channel_listen),
                ("admin", self.config.server.admin_listen),
            ]
            if self.config.database.mode == "portable":
                ports_to_check.append(("mysql", f"{self.config.database.host}:{self.config.database.port}"))
            
            for name, addr in ports_to_check:
                if ':' in addr:
                    host, port_str = addr.rsplit(':', 1)
                    try:
                        port = int(port_str)
                        if self.process_mgr.is_port_in_use(port, host):
                            errors.append(f"port {port} ({name}) already in use")
                    except ValueError:
                        pass
        
        # 7. 检查客户端
        if options.check_client and self.config:
            client_dir = self.config.client.directory
            if not client_dir or not os.path.isdir(client_dir):
                errors.append("client directory not configured or not found")
            elif not os.path.isfile(os.path.join(client_dir, "DNF.exe")):
                errors.append("DNF.exe not found in client directory")
        
        if errors:
            self.log("Check failed with errors:")
            for err in errors:
                self.log(f"  - {err}")
            return False, "; ".join(errors)
        
        self.log("All checks passed!")
        return True, None
    
    def build(self, force: bool = True) -> Tuple[bool, Optional[str]]:
        """
        编译服务端（需要Go环境，Python版暂不支持）
        """
        return False, "build command requires Go toolchain, not supported in Python version"
    
    def launch_client(self, client_directory: str = "", multi_instance: bool = False,
                      username: str = "", password: str = "") -> Tuple[bool, Optional[str]]:
        """
        启动客户端
        对应Go版 controller.launchClient()
        """
        # 确定客户端目录
        if not client_directory and self.config:
            client_directory = self.config.client.directory
        
        if not client_directory or not os.path.isdir(client_directory):
            return False, "client directory not configured"
        
        dnf_exe = os.path.join(client_directory, "DNF.exe")
        if not os.path.isfile(dnf_exe):
            return False, f"DNF.exe not found: {dnf_exe}"
        
        # 构建启动参数
        args = []
        if multi_instance:
            args.append("-multi-instance")
        if username:
            args.extend(["-username", username])
        if password:
            # 注意：真实实现中应该使用安全方式传递密码
            args.extend(["-password", password])
        
        # 启动客户端
        pid, err = self.process_mgr.start_process(
            dnf_exe,
            args=args,
            working_dir=client_directory,
            wait=False
        )
        
        if err:
            return False, f"launch client failed: {err}"
        
        self.log(f"Client launched (PID: {pid})")
        return True, None
    
    def account(self, args: List[str]) -> Tuple[bool, Optional[str]]:
        """
        账号管理子命令
        对应Go版 controller.account()
        """
        if not args:
            return False, "account command requires subcommand: register/login/list"
        
        subcmd = args[0].lower()
        
        if subcmd == "register":
            return self._account_register(args[1:])
        elif subcmd == "login":
            return self._account_login(args[1:])
        elif subcmd == "list":
            return self._account_list()
        else:
            return False, f"unknown account subcommand: {subcmd}"
    
    def _account_register(self, args: List[str]) -> Tuple[bool, Optional[str]]:
        """账号注册"""
        # 简单解析参数
        username = ""
        password = ""
        i = 0
        while i < len(args):
            if args[i] == "--username" and i + 1 < len(args):
                username = args[i + 1]
                i += 2
            elif args[i] == "--password-stdin":
                # 从stdin读取密码
                password = sys.stdin.readline().strip()
                i += 1
            else:
                i += 1
        
        if not username or not password:
            return False, "register requires --username and --password-stdin"
        
        # 加载配置
        self.load_config()
        self.mysql_mgr.load_config()
        
        return self.account_mgr.register(username, password)
    
    def _account_login(self, args: List[str]) -> Tuple[bool, Optional[str]]:
        """账号登录验证"""
        username = ""
        password = ""
        i = 0
        while i < len(args):
            if args[i] == "--username" and i + 1 < len(args):
                username = args[i + 1]
                i += 2
            elif args[i] == "--password-stdin":
                password = sys.stdin.readline().strip()
                i += 1
            else:
                i += 1
        
        if not username or not password:
            return False, "login requires --username and --password-stdin"
        
        # 加载配置
        self.load_config()
        self.mysql_mgr.load_config()
        
        ok, msg, account = self.account_mgr.login(username, password)
        if ok and account:
            self.log(f"Login successful: {account.username} (ID: {account.account_id})")
        return ok, msg
    
    def _account_list(self) -> Tuple[bool, Optional[str]]:
        """列出账号"""
        # 加载配置
        self.load_config()
        self.mysql_mgr.load_config()
        
        accounts, err = self.account_mgr.list_accounts()
        if err:
            return False, err
        
        self.log(f"Found {len(accounts)} accounts:")
        for acc in accounts:
            self.log(f"  - {acc.username} ({acc.state}, last login: {acc.last_login_at})")
        
        return True, None
    
    def _check_assets(self, log: bool = False) -> Tuple[bool, Optional[str]]:
        """检查资源文件"""
        assets = [
            ("Script.pvf", self.paths.runtime_data + "/Script.pvf", True),
            ("channel_info.etc", self.paths.channel_asset, True),
        ]
        
        for name, path, required in assets:
            if os.path.isfile(path):
                if log:
                    self.log(f"Asset OK: {name}")
            elif required:
                return False, f"missing asset: {name} ({path})"
        
        return True, None
    
    def _start_server(self) -> Tuple[bool, Optional[str]]:
        """启动服务端进程"""
        if not os.path.isfile(self.paths.server_exe):
            return False, f"server executable not found: {self.paths.server_exe}"
        
        # 启动服务端
        pid, err = self.process_mgr.start_process(
            self.paths.server_exe,
            working_dir=self.paths.runtime_root,
            wait=False
        )
        
        if err:
            return False, err
        
        # 保存进程状态
        state = ProcessState(
            pid=pid,
            name="DNF90Server.exe",
            exe_path=self.paths.server_exe,
            start_time=datetime.now().isoformat(),
            status="RUNNING"
        )
        self.process_mgr.save_process_state(self.paths.process_state, state)
        
        # 等待服务端就绪（简单等待）
        time.sleep(3)
        
        return True, None
    
    def _stop_server(self) -> Tuple[bool, Optional[str]]:
        """停止服务端进程"""
        # 加载进程状态
        state, err = self.process_mgr.load_process_state(self.paths.process_state)
        if err or not state or state.pid == 0:
            # 尝试按名称查找
            processes = self.process_mgr.find_process_by_name("DNF90Server.exe")
            if processes:
                state = ProcessState(pid=processes[0].pid, name="DNF90Server.exe")
            else:
                return True, None  # 已经停止
        
        # 停止进程
        ok, err = self.process_mgr.stop_process(state.pid, force=True)
        if not ok:
            return False, err
        
        # 更新状态
        state.status = "STOPPED"
        state.pid = 0
        self.process_mgr.save_process_state(self.paths.process_state, state)
        
        return True, None
    
    def _is_server_running(self) -> bool:
        """检查服务端是否在运行"""
        state, _ = self.process_mgr.load_process_state(self.paths.process_state)
        if state and state.pid > 0:
            if self.process_mgr.is_process_running(state.pid):
                return True
        
        processes = self.process_mgr.find_process_by_name("DNF90Server.exe")
        return len(processes) > 0
