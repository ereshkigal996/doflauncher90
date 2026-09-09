#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNF90 Python版控制器
对应Go版 DNF90Control.exe

用法:
  python main.py start [--rebuild]
  python main.py stop [--keep-database]
  python main.py status
  python main.py build [--force]
  python main.py check [--skip-database] [--skip-ports] [--client]
  python main.py launch-client [--client-directory PATH] [--multi-instance] [--username NAME --password-stdin]
  python main.py account register --username NAME --password-stdin
  python main.py account login --username NAME --password-stdin
  python main.py account list

项目发现从当前目录和可执行文件目录开始。
设置 DNF90_PROJECT_ROOT 环境变量可覆盖。
"""

import os
import sys
import argparse
from typing import Optional

# 修复Windows命令行中文编码问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except Exception:
            pass

# 确保可以导入core和modules模块
if getattr(sys, 'frozen', False):
    # PyInstaller打包后的路径
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_path)

from core.paths import discover_paths
from core.controller import Controller, CheckOptions


def print_usage():
    """打印用法"""
    print(__doc__)


def run_cli(args: list) -> int:
    """
    运行CLI命令
    对应Go版 runCLI()
    """
    if not args:
        print_usage()
        return 2
    
    if args[0] in ("-h", "--help", "help"):
        print_usage()
        return 0
    
    # 发现项目路径
    paths, err = discover_paths()
    if err:
        print(f"FAILED: {err}", file=sys.stderr)
        return 1
    
    # 创建控制器
    controller = Controller(paths, sys.stdout, sys.stderr)
    
    # 解析命令
    command = args[0].lower()
    
    try:
        if command == "start":
            parser = argparse.ArgumentParser(prog="start", add_help=False)
            parser.add_argument("--rebuild", action="store_true", default=False)
            parsed, _ = parser.parse_known_args(args[1:])
            ok, err = controller.start(parsed.rebuild)
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        elif command == "stop":
            parser = argparse.ArgumentParser(prog="stop", add_help=False)
            parser.add_argument("--keep-database", action="store_true", default=False)
            parsed, _ = parser.parse_known_args(args[1:])
            ok, err = controller.stop(parsed.keep_database)
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        elif command == "status":
            ok, err = controller.status()
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        elif command == "build":
            parser = argparse.ArgumentParser(prog="build", add_help=False)
            parser.add_argument("--force", action="store_true", default=True)
            parsed, _ = parser.parse_known_args(args[1:])
            ok, err = controller.build(parsed.force)
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        elif command == "check":
            parser = argparse.ArgumentParser(prog="check", add_help=False)
            parser.add_argument("--skip-database", action="store_true", default=False)
            parser.add_argument("--skip-ports", action="store_true", default=False)
            parser.add_argument("--client", action="store_true", default=False)
            parsed, _ = parser.parse_known_args(args[1:])
            options = CheckOptions(
                skip_database=parsed.skip_database,
                skip_ports=parsed.skip_ports,
                check_client=parsed.client
            )
            ok, err = controller.check(options)
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        elif command == "launch-client":
            parser = argparse.ArgumentParser(prog="launch-client", add_help=False)
            parser.add_argument("--client-directory", default="")
            parser.add_argument("--multi-instance", action="store_true", default=False)
            parser.add_argument("--username", default="")
            parser.add_argument("--password-stdin", action="store_true", default=False)
            parsed, _ = parser.parse_known_args(args[1:])
            
            password = ""
            if parsed.username and parsed.password_stdin:
                password = sys.stdin.readline().strip()
            elif parsed.password_stdin and not parsed.username:
                print("FAILED: --password-stdin requires --username", file=sys.stderr)
                return 1
            elif parsed.username and not parsed.password_stdin:
                print("FAILED: launch-client with --username requires --password-stdin", file=sys.stderr)
                return 1
            
            ok, err = controller.launch_client(
                parsed.client_directory,
                parsed.multi_instance,
                parsed.username,
                password
            )
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        elif command == "account":
            ok, err = controller.account(args[1:])
            if not ok:
                print(f"FAILED: {err}", file=sys.stderr)
                return 1
            return 0
        
        else:
            print(f"unknown command: {command}\n", file=sys.stderr)
            print_usage()
            return 2
    
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"FAILED: unexpected error: {e}", file=sys.stderr)
        return 1


def main():
    """主入口"""
    sys.exit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
