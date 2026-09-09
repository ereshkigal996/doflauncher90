#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将Python版控制器打包为exe
使用PyInstaller打包
"""

import os
import sys
import subprocess


def build_exe():
    """打包为exe"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_dir, "main.py")
    output_dir = os.path.join(project_dir, "dist")
    build_dir = os.path.join(project_dir, "build")
    
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not installed, installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # 打包命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "DNF90ControlPy",
        "--clean",
        "--noconfirm",
        "--distpath", output_dir,
        "--workpath", build_dir,
        main_script
    ]
    
    print(f"Building exe...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=project_dir)
    
    if result.returncode == 0:
        exe_path = os.path.join(output_dir, "DNF90ControlPy.exe")
        if os.path.isfile(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\nBuild successful!")
            print(f"Output: {exe_path}")
            print(f"Size: {size_mb:.2f} MB")
            return True
    else:
        print(f"\nBuild failed with code: {result.returncode}")
        return False


if __name__ == "__main__":
    build_exe()
