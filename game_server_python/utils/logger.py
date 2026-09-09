"""
日志工具模块
提供统一的日志记录功能
"""

import os
import sys
import time
import threading
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


# 日志级别名称映射
LEVEL_NAMES = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO",
    LogLevel.WARNING: "WARNING",
    LogLevel.ERROR: "ERROR",
    LogLevel.CRITICAL: "CRITICAL",
}

# 日志级别颜色（ANSI转义码）
LEVEL_COLORS = {
    LogLevel.DEBUG: "\033[36m",     # 青色
    LogLevel.INFO: "\033[32m",      # 绿色
    LogLevel.WARNING: "\033[33m",   # 黄色
    LogLevel.ERROR: "\033[31m",     # 红色
    LogLevel.CRITICAL: "\033[35m",  # 紫色
}

RESET_COLOR = "\033[0m"


class Logger:
    """日志记录器"""
    
    def __init__(self, name: str = "GameServer", log_dir: str = "logs"):
        self.name = name
        self.log_dir = log_dir
        self.min_level = LogLevel.DEBUG
        self.show_console = True
        self.show_color = True
        self.write_file = True
        
        self._lock = threading.Lock()
        self._file_handle = None
        self._current_date = ""
        
        # 确保日志目录存在
        if self.write_file:
            self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir, exist_ok=True)
            except Exception as e:
                print(f"[Logger] 创建日志目录失败: {e}")
                self.write_file = False
    
    def _get_log_file_path(self) -> str:
        """获取日志文件路径"""
        current_date = datetime.now().strftime("%Y%m%d")
        if current_date != self._current_date:
            self._current_date = current_date
            self._close_file()
        
        return os.path.join(self.log_dir, f"{self.name}_{current_date}.log")
    
    def _open_file(self):
        """打开日志文件"""
        if not self.write_file:
            return
        
        try:
            log_path = self._get_log_file_path()
            self._file_handle = open(log_path, 'a', encoding='utf-8')
        except Exception as e:
            print(f"[Logger] 打开日志文件失败: {e}")
            self.write_file = False
    
    def _close_file(self):
        """关闭日志文件"""
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None
    
    def _format_message(self, level: LogLevel, message: str) -> str:
        """格式化日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_name = LEVEL_NAMES.get(level, "UNKNOWN")
        return f"[{timestamp}] [{level_name}] [{self.name}] {message}"
    
    def log(self, level: LogLevel, message: str):
        """记录日志"""
        if level.value < self.min_level.value:
            return
        
        formatted = self._format_message(level, message)
        
        # 控制台输出
        if self.show_console:
            with self._lock:
                if self.show_color and sys.stdout.isatty():
                    color = LEVEL_COLORS.get(level, "")
                    print(f"{color}{formatted}{RESET_COLOR}")
                else:
                    print(formatted)
        
        # 文件输出
        if self.write_file:
            with self._lock:
                try:
                    if not self._file_handle:
                        self._open_file()
                    
                    if self._file_handle:
                        self._file_handle.write(formatted + "\n")
                        self._file_handle.flush()
                except Exception as e:
                    print(f"[Logger] 写入日志文件失败: {e}")
    
    def debug(self, message: str):
        """记录调试日志"""
        self.log(LogLevel.DEBUG, message)
    
    def info(self, message: str):
        """记录信息日志"""
        self.log(LogLevel.INFO, message)
    
    def warning(self, message: str):
        """记录警告日志"""
        self.log(LogLevel.WARNING, message)
    
    def error(self, message: str):
        """记录错误日志"""
        self.log(LogLevel.ERROR, message)
    
    def critical(self, message: str):
        """记录严重错误日志"""
        self.log(LogLevel.CRITICAL, message)
    
    def set_level(self, level: LogLevel):
        """设置最低日志级别"""
        self.min_level = level
    
    def set_console_output(self, enabled: bool):
        """设置是否输出到控制台"""
        self.show_console = enabled
    
    def set_file_output(self, enabled: bool):
        """设置是否输出到文件"""
        self.write_file = enabled
        if enabled:
            self._ensure_log_dir()
        else:
            self._close_file()
    
    def close(self):
        """关闭日志记录器"""
        self._close_file()


# 全局日志记录器实例
_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """获取全局日志记录器实例"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def init_logger(name: str = "GameServer", log_dir: str = "logs") -> Logger:
    """初始化全局日志记录器"""
    global _logger
    _logger = Logger(name, log_dir)
    return _logger


# 便捷函数
def debug(message: str):
    """记录调试日志"""
    get_logger().debug(message)

def info(message: str):
    """记录信息日志"""
    get_logger().info(message)

def warning(message: str):
    """记录警告日志"""
    get_logger().warning(message)

def error(message: str):
    """记录错误日志"""
    get_logger().error(message)

def critical(message: str):
    """记录严重错误日志"""
    get_logger().critical(message)
