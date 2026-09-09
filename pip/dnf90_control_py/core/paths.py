# -*- coding: utf-8 -*-
"""
路径发现和项目根目录识别模块
对应Go版 paths.go
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class ProjectPaths:
    """项目路径集合"""
    project_root: str = ""
    go_server_root: str = ""
    runtime_root: str = ""
    runtime_bin: str = ""
    runtime_config: str = ""
    runtime_configs: str = ""
    runtime_data: str = ""
    runtime_logs: str = ""
    runtime_state: str = ""
    instance: str = ""
    instance_example: str = ""
    asset_manifest: str = ""
    client_manifest: str = ""
    mysql_manifest: str = ""
    vc_runtime_manifest: str = ""
    vc_runtime_root: str = ""
    channel_asset: str = ""
    server_exe: str = ""
    doctor_exe: str = ""
    launcher_exe: str = ""
    control_exe: str = ""
    process_state: str = ""
    binary_install_state: str = ""
    mysql_root: str = ""
    mysql_server: str = ""
    mysql_data: str = ""
    mysql_config: str = ""
    mysql_pid_file: str = ""
    mysqld_exe: str = ""
    mysql_process_state: str = ""
    mysql_install_state: str = ""
    mysql_data_state: str = ""
    mysql_legacy_data_state: str = ""


def is_regular_file(path: str) -> bool:
    """检查是否为普通文件"""
    return os.path.isfile(path)


def is_project_root(root: str) -> bool:
    """
    检查是否为DNF90项目根目录
    对应Go版 isProjectRoot()
    
    必须同时存在：
    1. runtime/templates/instance.example.json
    2. runtime/assets/manifest.json
    """
    file1 = os.path.join(root, "runtime", "templates", "instance.example.json")
    file2 = os.path.join(root, "runtime", "assets", "manifest.json")
    return is_regular_file(file1) and is_regular_file(file2)


def has_go_server_source(paths: ProjectPaths) -> bool:
    """检查是否包含go-server源代码"""
    return is_regular_file(os.path.join(paths.go_server_root, "go.mod"))


def new_project_paths(root: str) -> ProjectPaths:
    """
    创建项目路径集合
    对应Go版 newProjectPaths()
    """
    root = os.path.normpath(root)
    runtime_root = os.path.join(root, "runtime")
    
    return ProjectPaths(
        project_root=root,
        go_server_root=os.path.join(root, "go-server"),
        runtime_root=runtime_root,
        runtime_bin=os.path.join(runtime_root, "bin"),
        runtime_config=os.path.join(runtime_root, "config"),
        runtime_configs=os.path.join(runtime_root, "configs"),
        runtime_data=os.path.join(runtime_root, "data", "dnf"),
        runtime_logs=os.path.join(runtime_root, "logs"),
        runtime_state=os.path.join(runtime_root, "state"),
        instance=os.path.join(runtime_root, "config", "instance.json"),
        instance_example=os.path.join(runtime_root, "templates", "instance.example.json"),
        asset_manifest=os.path.join(runtime_root, "assets", "manifest.json"),
        client_manifest=os.path.join(runtime_root, "assets", "client-compatibility.json"),
        mysql_manifest=os.path.join(runtime_root, "assets", "mysql-portable.json"),
        vc_runtime_manifest=os.path.join(runtime_root, "assets", "vcruntime-app-local.json"),
        vc_runtime_root=os.path.join(runtime_root, "vendor", "vcruntime", "x64"),
        channel_asset=os.path.join(runtime_root, "assets", "channel_info.etc"),
        server_exe=os.path.join(runtime_root, "bin", "DNF90Server.exe"),
        doctor_exe=os.path.join(runtime_root, "bin", "DNF90Doctor.exe"),
        launcher_exe=os.path.join(runtime_root, "bin", "DNF90Launcher.exe"),
        control_exe=os.path.join(runtime_root, "bin", "DNF90Control.exe"),
        process_state=os.path.join(runtime_root, "state", "server-process.json"),
        binary_install_state=os.path.join(runtime_root, "state", "binary-install.json"),
        mysql_root=os.path.join(runtime_root, "mysql"),
        mysql_server=os.path.join(runtime_root, "mysql", "server"),
        mysql_data=os.path.join(runtime_root, "mysql", "data"),
        mysql_config=os.path.join(runtime_root, "config", "mysql.ini"),
        mysql_pid_file=os.path.join(runtime_root, "state", "mysql.pid"),
        mysqld_exe=os.path.join(runtime_root, "mysql", "server", "bin", "mysqld.exe"),
        mysql_process_state=os.path.join(runtime_root, "state", "mysql-process.json"),
        mysql_install_state=os.path.join(runtime_root, "mysql", "server", ".dnf90-install.json"),
        mysql_data_state=os.path.join(runtime_root, "mysql", "data-state.json"),
        mysql_legacy_data_state=os.path.join(runtime_root, "mysql", "data", ".dnf90-data.json"),
    )


def discover_paths() -> Tuple[Optional[ProjectPaths], Optional[str]]:
    """
    发现项目路径
    对应Go版 discoverPaths()
    
    查找顺序：
    1. 环境变量 DNF90_PROJECT_ROOT
    2. 当前工作目录向上查找
    3. 可执行文件所在目录向上查找
    """
    # 1. 检查环境变量
    env_root = os.environ.get("DNF90_PROJECT_ROOT", "").strip()
    if env_root:
        try:
            root = os.path.abspath(env_root)
            if is_project_root(root):
                return new_project_paths(root), None
            return None, f"DNF90_PROJECT_ROOT is not a DNF90 project: {root}"
        except Exception as e:
            return None, f"resolve DNF90_PROJECT_ROOT: {e}"
    
    # 2. 收集起始目录
    starts: List[str] = []
    
    # 当前工作目录
    try:
        cwd = os.getcwd()
        starts.append(cwd)
    except Exception:
        pass
    
    # 可执行文件所在目录
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(__file__)
        starts.append(os.path.dirname(exe_path))
    except Exception:
        pass
    
    # 3. 向上查找项目根目录
    seen = set()
    for start in starts:
        try:
            current = os.path.abspath(start)
        except Exception:
            continue
        
        while True:
            key = os.path.normpath(current).lower()
            if key not in seen:
                seen.add(key)
                if is_project_root(current):
                    return new_project_paths(current), None
            
            parent = os.path.dirname(current)
            if parent == current:  # 到达根目录
                break
            current = parent
    
    return None, "cannot find DNF90 project root; set DNF90_PROJECT_ROOT"


def ensure_directories(paths: ProjectPaths) -> Tuple[bool, Optional[str]]:
    """
    确保所有必需目录存在
    对应Go版 ensureDirectories()
    """
    dirs_to_create = [
        paths.runtime_root,
        paths.runtime_bin,
        paths.runtime_config,
        paths.runtime_configs,
        os.path.join(paths.runtime_configs, "dnf"),
        os.path.join(paths.runtime_configs, "servergroup"),
        paths.runtime_data,
        paths.runtime_logs,
        paths.runtime_state,
        paths.mysql_root,
    ]
    
    for dir_path in dirs_to_create:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            return False, f"create runtime directory {dir_path}: {e}"
    
    return True, None
