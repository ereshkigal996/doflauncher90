# -*- coding: utf-8 -*-

"""

DNF轮回 - 简易启动器

版本: 2.9.7 正式版

"""

import os

import sys

import json

import shutil

import subprocess

import threading

import time

import socket

import traceback

from datetime import datetime

# 程序版本号（正式版本号）
APP_VERSION = "2.9.7"

# ========== 性能优化：配置缓存 ==========
class ConfigCache:
    """配置文件缓存，避免重复读取文件"""
    _cache = {}
    _cache_time = {}
    _cache_ttl = 10  # 缓存有效期10秒
    
    @classmethod
    def read_json(cls, file_path):
        """读取JSON文件，带缓存"""
        import json
        current_time = datetime.now().timestamp()
        
        # 检查缓存是否有效
        if file_path in cls._cache and file_path in cls._cache_time:
            if current_time - cls._cache_time[file_path] < cls._cache_ttl:
                return cls._cache[file_path]
        
        # 读取文件并更新缓存
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cls._cache[file_path] = data
            cls._cache_time[file_path] = current_time
            return data
        except:
            return None
    
    @classmethod
    def invalidate(cls, file_path=None):
        """使缓存失效"""
        if file_path:
            cls._cache.pop(file_path, None)
            cls._cache_time.pop(file_path, None)
        else:
            cls._cache.clear()
            cls._cache_time.clear()

# ========== 性能优化：服务端状态缓存 ==========
class ServerStatusCache:
    """服务端状态缓存，避免频繁检查端口"""
    _status = None
    _check_time = 0
    _cache_ttl = 3  # 缓存有效期3秒
    
    @classmethod
    def get_status(cls, check_func):
        """获取服务端状态，带缓存"""
        current_time = datetime.now().timestamp()
        
        if cls._status is not None and current_time - cls._check_time < cls._cache_ttl:
            return cls._status
        
        cls._status = check_func()
        cls._check_time = current_time
        return cls._status
    
    @classmethod
    def invalidate(cls):
        """使状态缓存失效"""
        cls._status = None
        cls._check_time = 0

# ========== 性能优化：高效日志系统 ==========
class EfficientLogger:
    """高效日志系统，减少UI更新频率"""
    _logs = []
    _max_logs = 500  # 最大保留日志数
    _pending_ui_update = False
    _ui_widget = None
    
    @classmethod
    def set_ui_widget(cls, widget):
        """设置UI显示组件"""
        cls._ui_widget = widget
    
    @classmethod
    def log(cls, message):
        """记录日志（自动将路径转换为Windows反斜杠格式）"""
        # 自动将路径中的正斜杠转换为反斜杠（Windows标准格式）
        message = message.replace('/', '\\')
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        cls._logs.append(log_entry)
        
        # 限制日志数量，避免内存占用过大
        if len(cls._logs) > cls._max_logs:
            cls._logs = cls._logs[-cls._max_logs:]
        
        # 延迟UI更新，避免频繁重绘
        if cls._ui_widget and not cls._pending_ui_update:
            cls._pending_ui_update = True
            QTimer.singleShot(50, cls._flush_ui)
    
    @classmethod
    def _flush_ui(cls):
        """批量更新UI"""
        if cls._ui_widget:
            try:
                cls._ui_widget.setPlainText("\n".join(cls._logs))
                # 滚动到底部
                scrollbar = cls._ui_widget.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            except:
                pass
        cls._pending_ui_update = False
    
    @classmethod
    def get_all_logs(cls):
        """获取所有日志"""
        return cls._logs.copy()
    
    @classmethod
    def clear(cls):
        """清空日志"""
        cls._logs = []
        if cls._ui_widget:
            cls._ui_widget.clear()

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,

                             QWidget, QLabel, QPushButton, QTextEdit, QFileDialog,

                             QMessageBox, QSizePolicy, QFrame, QLineEdit, QStackedWidget,

                             QProgressBar, QGroupBox, QMenu, QAction, QTableWidget,
                             QTableWidgetItem, QHeaderView, QInputDialog, QDialog,
                             QCheckBox, QSpinBox, QRadioButton)

from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal, QSharedMemory

from PyQt5.QtGui import QFont, QIcon

# 单实例运行互斥锁标识
SINGLE_INSTANCE_KEY = "DNF_Launcher_2_9_Single_Instance_Lock"


def show_frameless_warning(parent, title, message):
    """显示系统默认样式的警告弹窗"""
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtGui import QFont
    
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setStandardButtons(QMessageBox.Ok)
    
    # 设置按钮文字为中文
    ok_button = msg_box.button(QMessageBox.Ok)
    if ok_button:
        ok_button.setText("确定")
    
    # 设置字体
    font = QFont("Noto Sans SC", 10)
    msg_box.setFont(font)
    
    msg_box.exec_()


def show_frameless_confirm(parent, title, message):
    """显示自定义确认弹窗（深色主题），返回True表示Yes，False表示No"""
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget
    from PyQt5.QtCore import Qt, QPoint
    
    # 自定义可拖动的对话框
    class ConfirmDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.dragging = False
            self.drag_position = QPoint()
            self.result = False
        
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        
        def mouseMoveEvent(self, event):
            if self.dragging and event.buttons() == Qt.LeftButton:
                self.move(event.globalPos() - self.drag_position)
                event.accept()
        
        def mouseReleaseEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.dragging = False
                event.accept()
    
    dialog = ConfirmDialog(parent)
    dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
    dialog.setAttribute(Qt.WA_TranslucentBackground)
    # 宽度不变，高度加大一些
    dialog.setFixedSize(340, 160)
    
    # 主布局
    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    
    # 圆角容器（主窗体，保留描边）
    container = QWidget()
    container.setStyleSheet("""
        background-color: #202020;
        border: 1px solid #4a4a4a;
        border-radius: 6px;
    """)
    main_layout.addWidget(container)
    
    layout = QVBoxLayout(container)
    layout.setContentsMargins(15, 24, 15, 12)
    layout.setSpacing(10)
    
    # 消息内容（放到一行，自动换行，取消容器描边）
    clean_message = message.replace('\n', ' ').replace('\r', ' ')
    while '  ' in clean_message:
        clean_message = clean_message.replace('  ', ' ')
    msg_label = QLabel(clean_message)
    msg_label.setStyleSheet("color: #ffffff; font-size: 13px; font-family: 'Noto Sans SC', 'Microsoft YaHei'; line-height: 1.0; background-color: transparent; border: none;")
    msg_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    msg_label.setWordWrap(True)
    layout.addWidget(msg_label)
    
    # 按钮区域
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(8)
    btn_layout.addStretch()
    
    # 否按钮（在左，恢复描边）
    no_btn = QPushButton("否")
    no_btn.setStyleSheet("""
        QPushButton {
            background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;
            border-radius: 6px; padding: 8px 24px; font-weight: bold; font-size: 13px;
            font-family: 'Noto Sans SC', 'Microsoft YaHei';
        }
        QPushButton:hover { background-color: #3a3a3a; border-color: #5a5a5a; }
        QPushButton:pressed { background-color: #1a1a1a; }
    """)
    no_btn.clicked.connect(dialog.reject)
    btn_layout.addWidget(no_btn)
    
    # 是按钮（在右，恢复描边）
    yes_btn = QPushButton("是")
    yes_btn.setStyleSheet("""
        QPushButton {
            background-color: #1a2a4a; color: #ffffff; border: 1px solid #4a90d9;
            border-radius: 6px; padding: 8px 24px; font-weight: bold; font-size: 13px;
            font-family: 'Noto Sans SC', 'Microsoft YaHei';
        }
        QPushButton:hover { background-color: #2a3a5a; border-color: #5aa0e9; }
        QPushButton:pressed { background-color: #0a1a3a; }
    """)
    yes_btn.clicked.connect(dialog.accept)
    btn_layout.addWidget(yes_btn)
    
    btn_layout.addStretch()
    layout.addLayout(btn_layout)
    
    result = dialog.exec_()
    return result == QDialog.Accepted


def show_frameless_error(parent, title, message):
    """显示无边框圆角错误弹窗"""
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget

    dialog = QDialog(parent)
    dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
    dialog.setAttribute(Qt.WA_TranslucentBackground)
    dialog.setMinimumWidth(320)

    # 主布局
    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # 圆角容器
    container = QWidget()
    container.setStyleSheet("""
        background-color: #202020;
        border: 1px solid #4a4a4a;
        border-radius: 8px;
    """)
    main_layout.addWidget(container)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)

    title_label = QLabel(title)
    title_label.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
    title_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_label)

    msg_label = QLabel(message)
    msg_label.setStyleSheet("color: #ffffff; font-size: 13px; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
    msg_label.setAlignment(Qt.AlignCenter)
    msg_label.setWordWrap(True)
    layout.addWidget(msg_label)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    ok_btn = QPushButton("确定")
    ok_btn.setStyleSheet("""
        QPushButton {
            background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;
            border-radius: 4px; padding: 8px 24px; font-weight: bold; font-size: 13px;
            font-family: 'Noto Sans SC', 'Microsoft YaHei';
        }
        QPushButton:pressed { background-color: #1a1a1a; border-color: #ff4444; color: #ff4444; }
    """)
    ok_btn.clicked.connect(dialog.accept)
    btn_layout.addWidget(ok_btn)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    dialog.exec_()



class PvfCheckWindow(QWidget):
    """独立的PVF校验窗口 - 用于比对和同步服务端与客户端的Script.pvf（圆角窗口）"""
    
    def __init__(self, server_path, client_path, parent=None):
        super().__init__(parent)
        self.server_path = server_path
        self.client_path = client_path
        self.result = None  # 'server' / 'client' / None
        self.selected_version = None  # 记录用户选择的版本
        self.dragging = False  # 窗口拖动状态
        self.drag_position = QPoint()
        self.server_pvf = os.path.join(server_path, "runtime", "data", "dnf", "Script.pvf")
        self.client_pvf = os.path.join(client_path, "Script.pvf")
        
        self.init_ui()
        self.check_pvf_files()
    
    def init_ui(self):
        """初始化UI（圆角无边框窗口）"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 480)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 圆角容器（实现圆角效果）
        container = QWidget()
        container.setObjectName("roundedContainer")
        container.setStyleSheet("""
            #roundedContainer {
                background-color: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
        """)
        main_layout.addWidget(container)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: #252525; border-bottom: 1px solid #3a3a3a; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        
        title_label = QLabel("PVF 文件校验")
        title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; color: #888888; font-size: 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #3a3a3a; color: #ffffff; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        container_layout.addWidget(title_bar)
        
        # 内容区域
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(12)
        
        # 提示信息
        tip_label = QLabel("检测到服务端与客户端的 Script.pvf 文件不一致，请选择要使用的版本：")
        tip_label.setStyleSheet("color: #ffd700; font-size: 12px; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
        tip_label.setWordWrap(True)
        content_layout.addWidget(tip_label)
        
        # 服务端PVF信息
        server_group = QGroupBox("服务端版本")
        server_group.setStyleSheet("""
            QGroupBox { color: #4a90d9; font-size: 12px; font-weight: bold; border: 1px solid #2a4a6a; border-radius: 6px; margin-top: 10px; padding-top: 15px; background-color: #1a2030; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: #cccccc; font-size: 11px; background-color: transparent; border: none; }
        """)
        server_layout = QVBoxLayout(server_group)
        self.server_path_label = QLabel("路径: 加载中...")
        self.server_path_label.setWordWrap(True)
        self.server_size_label = QLabel("文件大小: -")
        self.server_time_label = QLabel("修改时间: -")
        server_layout.addWidget(self.server_path_label)
        server_layout.addWidget(self.server_size_label)
        server_layout.addWidget(self.server_time_label)
        content_layout.addWidget(server_group)
        
        # 客户端PVF信息
        client_group = QGroupBox("客户端版本")
        client_group.setStyleSheet("""
            QGroupBox { color: #d94a4a; font-size: 12px; font-weight: bold; border: 1px solid #6a2a2a; border-radius: 6px; margin-top: 10px; padding-top: 15px; background-color: #301a1a; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: #cccccc; font-size: 11px; background-color: transparent; border: none; }
        """)
        client_layout = QVBoxLayout(client_group)
        self.client_path_label = QLabel("路径: 加载中...")
        self.client_path_label.setWordWrap(True)
        self.client_size_label = QLabel("文件大小: -")
        self.client_time_label = QLabel("修改时间: -")
        client_layout.addWidget(self.client_path_label)
        client_layout.addWidget(self.client_size_label)
        client_layout.addWidget(self.client_time_label)
        content_layout.addWidget(client_group)
        
        # 差异提示
        self.diff_label = QLabel("")
        self.diff_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.diff_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.diff_label)
        
        content_layout.addStretch()
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.server_btn = QPushButton("使用服务端版本")
        self.server_btn.setFixedHeight(40)
        self.server_btn.setCursor(Qt.PointingHandCursor)
        self.server_btn.setStyleSheet("""
            QPushButton { background-color: #1a2a4a; color: #ffffff; border: 1px solid #4a90d9; border-radius: 6px; font-weight: bold; font-size: 12px; font-family: 'Noto Sans SC', 'Microsoft YaHei'; }
            QPushButton:hover { background-color: #2a3a5a; border-color: #6ab0ff; }
            QPushButton:pressed { background-color: #0a1a3a; }
            QPushButton:disabled { background-color: #2a2a2a; color: #666666; border-color: #3a3a3a; }
        """)
        self.server_btn.clicked.connect(lambda: self.select_version("server"))
        btn_layout.addWidget(self.server_btn)
        
        self.client_btn = QPushButton("使用客户端版本")
        self.client_btn.setFixedHeight(40)
        self.client_btn.setCursor(Qt.PointingHandCursor)
        self.client_btn.setStyleSheet("""
            QPushButton { background-color: #4a1a1a; color: #ffffff; border: 1px solid #d94a4a; border-radius: 6px; font-weight: bold; font-size: 12px; font-family: 'Noto Sans SC', 'Microsoft YaHei'; }
            QPushButton:hover { background-color: #5a2a2a; border-color: #ff6a6a; }
            QPushButton:pressed { background-color: #3a0a0a; }
            QPushButton:disabled { background-color: #2a2a2a; color: #666666; border-color: #3a3a3a; }
        """)
        self.client_btn.clicked.connect(lambda: self.select_version("client"))
        btn_layout.addWidget(self.client_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setFixedWidth(80)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #cccccc; border: 1px solid #4a4a4a; border-radius: 6px; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background-color: #3a3a3a; color: #ffffff; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        
        content_layout.addLayout(btn_layout)
        
        # 进度条（替换时显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #2a2a2a; border: 1px solid #4a4a4a; border-radius: 4px; text-align: center; color: #ffffff; font-size: 11px; }
            QProgressBar::chunk { background-color: #4a90d9; border-radius: 3px; }
        """)
        content_layout.addWidget(self.progress_bar)
        
        container_layout.addWidget(content)
    
    def get_file_info(self, file_path):
        """获取文件信息（大小、修改时间）"""
        if not os.path.exists(file_path):
            return None
        stat = os.stat(file_path)
        size_mb = stat.st_size / (1024 * 1024)
        if size_mb >= 1:
            size_str = f"{size_mb:.2f} MB"
        else:
            size_str = f"{stat.st_size / 1024:.2f} KB"
        time_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {"size": size_str, "time": time_str, "size_bytes": stat.st_size, "mtime": stat.st_mtime}
    
    def check_pvf_files(self):
        """检查PVF文件并显示信息"""
        # 服务端PVF
        self.server_path_label.setText(f"路径: {self.server_pvf}")
        server_info = self.get_file_info(self.server_pvf)
        if server_info:
            self.server_size_label.setText(f"文件大小: {server_info['size']}")
            self.server_time_label.setText(f"修改时间: {server_info['time']}")
        else:
            self.server_size_label.setText("文件大小: 文件不存在")
            self.server_time_label.setText("修改时间: -")
            self.server_btn.setEnabled(False)
        
        # 客户端PVF
        self.client_path_label.setText(f"路径: {self.client_pvf}")
        client_info = self.get_file_info(self.client_pvf)
        if client_info:
            self.client_size_label.setText(f"文件大小: {client_info['size']}")
            self.client_time_label.setText(f"修改时间: {client_info['time']}")
        else:
            self.client_size_label.setText("文件大小: 文件不存在")
            self.client_time_label.setText("修改时间: -")
            self.client_btn.setEnabled(False)
        
        # 显示差异
        if server_info and client_info:
            if server_info["size_bytes"] != client_info["size_bytes"] or server_info["mtime"] != client_info["mtime"]:
                self.diff_label.setText("⚠ 文件大小或修改时间不一致")
                self.diff_label.setStyleSheet("color: #ffd700; font-size: 11px;")
            else:
                self.diff_label.setText("✓ 文件完全一致，无需替换")
                self.diff_label.setStyleSheet("color: #4ade80; font-size: 11px;")
                self.server_btn.setEnabled(False)
                self.client_btn.setEnabled(False)
    
    def select_version(self, version):
        """选择版本并执行替换"""
        self.selected_version = version  # 记录用户选择
        self.server_btn.setEnabled(False)
        self.client_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        if version == "server":
            # 用服务端PVF替换客户端PVF
            src = self.server_pvf
            dst = self.client_pvf
            self.diff_label.setText("正在用服务端版本替换客户端版本...")
        else:
            # 用客户端PVF替换服务端PVF
            src = self.client_pvf
            dst = self.server_pvf
            self.diff_label.setText("正在用客户端版本替换服务端版本...")
        
        self.diff_label.setStyleSheet("color: #4a90d9; font-size: 11px;")
        
        # 在后台线程中执行复制
        self.copy_thread = CopyFileThread(src, dst)
        self.copy_thread.progress.connect(self.on_copy_progress)
        self.copy_thread.finished.connect(self.on_copy_finished)
        self.copy_thread.start()
    
    def on_copy_progress(self, value):
        """复制进度更新"""
        self.progress_bar.setValue(value)
    
    def on_copy_finished(self, success, message):
        """复制完成"""
        self.progress_bar.setValue(100)
        if success:
            self.diff_label.setText(f"✓ {message}")
            self.diff_label.setStyleSheet("color: #4ade80; font-size: 11px;")
            self.result = self.selected_version
            # 延迟关闭
            QTimer.singleShot(1000, self.close)
        else:
            self.diff_label.setText(f"✗ {message}")
            self.diff_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")
            self.server_btn.setEnabled(True)
            self.client_btn.setEnabled(True)
    
    def mousePressEvent(self, event):
        """支持拖动窗口"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """拖动窗口"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """结束拖动"""
        self.dragging = False



class ArchiveManagerWindow(QMainWindow):
    """存档管理独立窗口（增强版：多版本、备注）"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("存档管理")
        self.setFixedSize(520, 450)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.dragging = False
        self.drag_position = QPoint()
        self.init_ui()
        self.refresh_backup_list()
    
    def init_ui(self):
        """初始化UI"""
        central = QWidget()
        central.setObjectName("archiveContainer")
        central.setStyleSheet("""
            #archiveContainer {
                background-color: #202020;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet("background-color: #1a1a1a; border-bottom: 1px solid #333333; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        title_layout.setSpacing(0)
        
        title_label = QLabel("存档管理")
        title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #ffffff; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #e81123; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
        
        # 内容区域
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(10)
        
        # 备份列表
        list_label = QLabel("备份列表：")
        list_label.setStyleSheet("color: #cccccc; font-size: 13px; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
        content_layout.addWidget(list_label)
        
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(3)
        self.backup_table.setHorizontalHeaderLabels(["备份时间", "备注", "大小"])
        self.backup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.backup_table.setSelectionMode(QTableWidget.SingleSelection)
        self.backup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.backup_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                gridline-color: #333333;
                font-size: 12px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
                alternate-background-color: #1e1e1e;
                selection-background-color: #2a4a7a;
                selection-color: #ffffff;
            }
            QTableWidget QWidget {
                background-color: #1a1a1a;
            }
            QTableWidget::item {
                background-color: #1a1a1a;
                color: #ffffff;
                border: none;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #2a4a7a;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #252525;
            }
            QTableWidget::corner {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
            }
            QHeaderView {
                background-color: #2a2a2a;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #3a3a3a;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #353535;
            }
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #1a1a1a;
            }
            QScrollBar:horizontal {
                background-color: #1a1a1a;
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4a4a4a;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5a5a5a;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: #1a1a1a;
            }
        """)
        # 确保viewport背景色是深色的
        self.backup_table.viewport().setStyleSheet("background-color: #1a1a1a;")
        self.backup_table.horizontalHeader().setStretchLastSection(True)
        self.backup_table.setColumnWidth(0, 150)
        self.backup_table.setColumnWidth(1, 200)
        content_layout.addWidget(self.backup_table)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        # 新建备份按钮
        new_backup_btn = QPushButton("新建备份")
        new_backup_btn.setMinimumHeight(36)
        new_backup_btn.setCursor(Qt.PointingHandCursor)
        new_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a4a7a; color: #ffffff; border: 1px solid #4a90d9;
                border-radius: 4px; font-weight: bold; font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
            QPushButton:hover { background-color: #2a5a8a; }
            QPushButton:pressed { background-color: #0a3a6a; }
        """)
        new_backup_btn.clicked.connect(self.do_new_backup)
        btn_layout.addWidget(new_backup_btn)
        
        # 恢复按钮
        restore_btn = QPushButton("恢复选中")
        restore_btn.setMinimumHeight(36)
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;
                border-radius: 4px; font-weight: bold; font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
            QPushButton:hover { background-color: #3a3a3a; border-color: #5a5a5a; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)
        restore_btn.clicked.connect(self.do_restore_selected)
        btn_layout.addWidget(restore_btn)
        
        # 编辑备注按钮
        edit_note_btn = QPushButton("编辑备注")
        edit_note_btn.setMinimumHeight(36)
        edit_note_btn.setCursor(Qt.PointingHandCursor)
        edit_note_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;
                border-radius: 4px; font-weight: bold; font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
            QPushButton:hover { background-color: #3a3a3a; border-color: #5a5a5a; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)
        edit_note_btn.clicked.connect(self.do_edit_note)
        btn_layout.addWidget(edit_note_btn)
        
        # 删除按钮
        delete_btn = QPushButton("删除选中")
        delete_btn.setMinimumHeight(36)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a1a1a; color: #ffffff; border: 1px solid #d94a4a;
                border-radius: 4px; font-weight: bold; font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
            QPushButton:hover { background-color: #5a2a2a; }
            QPushButton:pressed { background-color: #3a0a0a; }
        """)
        delete_btn.clicked.connect(self.do_delete_selected)
        btn_layout.addWidget(delete_btn)
        
        content_layout.addLayout(btn_layout)
        
        # 刷新按钮
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        # 自动备份设置按钮
        auto_backup_btn = QPushButton("自动备份设置")
        auto_backup_btn.setMinimumHeight(32)
        auto_backup_btn.setCursor(Qt.PointingHandCursor)
        auto_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a; color: #cccccc; border: 1px solid #3a3a3a;
                border-radius: 4px; font-size: 12px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
            QPushButton:hover { background-color: #3a3a3a; color: #ffffff; }
        """)
        auto_backup_btn.clicked.connect(self.do_auto_backup_settings)
        refresh_layout.addWidget(auto_backup_btn)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a; color: #cccccc; border: 1px solid #3a3a3a;
                border-radius: 4px; font-size: 12px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
            QPushButton:hover { background-color: #3a3a3a; color: #ffffff; }
        """)
        refresh_btn.clicked.connect(self.refresh_backup_list)
        refresh_layout.addWidget(refresh_btn)
        
        content_layout.addLayout(refresh_layout)
        
        layout.addWidget(content)
    
    def refresh_backup_list(self):
        """刷新备份列表"""
        if not self.main_window or not hasattr(self.main_window, 'backup_dir'):
            return
        
        backup_dir = self.main_window.backup_dir
        if not os.path.exists(backup_dir):
            self.backup_table.setRowCount(0)
            return
        
        backups = [d for d in os.listdir(backup_dir)
                   if d.startswith("backup_") and os.path.isdir(os.path.join(backup_dir, d))]
        backups.sort(reverse=True)
        
        self.backup_table.setRowCount(len(backups))
        for row, backup_name in enumerate(backups):
            backup_path = os.path.join(backup_dir, backup_name)
            
            # 备份时间
            time_str = backup_name.replace("backup_", "").replace("_", " ")
            try:
                dt = datetime.strptime(backup_name.replace("backup_", ""), "%Y%m%d_%H%M%S")
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
            
            # 备注
            note = ""
            info_file = os.path.join(backup_path, "backup_info.json")
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                        note = info.get('note', '')
                except:
                    pass
            
            # 大小
            size = self.get_dir_size(backup_path)
            size_str = self.format_size(size)
            
            # 设置表格项
            self.backup_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.backup_table.setItem(row, 1, QTableWidgetItem(note))
            self.backup_table.setItem(row, 2, QTableWidgetItem(size_str))
            
            # 存储备份名称到第一项的data中
            self.backup_table.item(row, 0).setData(Qt.UserRole, backup_name)
    
    def get_dir_size(self, path):
        """获取目录大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    
    def format_size(self, size):
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f} MB"
        else:
            return f"{size/(1024*1024*1024):.2f} GB"
    
    def get_selected_backup(self):
        """获取选中的备份名称"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            return None
        item = self.backup_table.item(current_row, 0)
        if item:
            return item.data(Qt.UserRole)
        return None
    
    def do_new_backup(self):
        """新建备份"""
        self.close()
        if self.main_window:
            self.main_window.do_backup()
    
    def do_restore_selected(self):
        """恢复选中的备份"""
        backup_name = self.get_selected_backup()
        if not backup_name:
            show_frameless_warning(self, "提示", "请先选择要恢复的备份！")
            return
        
        if self.main_window and self.main_window.is_server_running():
            show_frameless_warning(
                self, "错误",
                "检测到服务端正在运行！\n恢复数据前必须先停止服务端。\n\n请先点击'停止服务'按钮，然后再进行数据恢复。"
            )
            return
        
        if not show_frameless_confirm(
            self, "确认恢复",
            f"数据恢复将覆盖当前所有数据！\n\n即将恢复备份：{backup_name}\n\n此操作不可撤销，确定要继续吗？"
        ):
            return
        
        self.close()
        if self.main_window:
            self.main_window.do_restore_specific(backup_name)
    
    def do_edit_note(self):
        """编辑备注"""
        backup_name = self.get_selected_backup()
        if not backup_name:
            show_frameless_warning(self, "提示", "请先选择要编辑备注的备份！")
            return
        
        backup_dir = self.main_window.backup_dir
        backup_path = os.path.join(backup_dir, backup_name)
        info_file = os.path.join(backup_path, "backup_info.json")
        
        # 读取当前备注
        current_note = ""
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    current_note = info.get('note', '')
            except:
                pass
        
        # 弹出输入框
        note, ok = QInputDialog.getText(self, "编辑备注", "请输入备份备注：", text=current_note)
        if ok:
            # 保存备注
            info = {}
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                except:
                    pass
            info['note'] = note
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            self.refresh_backup_list()
    
    def do_delete_selected(self):
        """删除选中的备份"""
        backup_name = self.get_selected_backup()
        if not backup_name:
            show_frameless_warning(self, "提示", "请先选择要删除的备份！")
            return
        
        if not show_frameless_confirm(
            self, "确认删除",
            f"确定要删除备份：{backup_name}吗？\n\n此操作不可撤销！"
        ):
            return
        
        backup_dir = self.main_window.backup_dir
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            import shutil
            shutil.rmtree(backup_path)
            self.refresh_backup_list()
        except Exception as e:
            show_frameless_error(self, "错误", f"删除备份失败：{str(e)}")
    
    def do_auto_backup_settings(self):
        """自动备份设置"""
        if not self.main_window:
            return
        
        # 创建设置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("自动备份设置")
        dialog.setFixedSize(380, 340)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #202020;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
                background-color: transparent;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #4a90d9;
                border: 1px solid #4a90d9;
            }
            QRadioButton {
                color: #ffffff;
                font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
                background-color: transparent;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
                background-color: #1a1a1a;
            }
            QRadioButton::indicator:checked {
                background-color: #4a90d9;
                border: 1px solid #4a90d9;
            }
            QSpinBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #2a2a2a;
                border: none;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #3a3a3a;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #5a5a5a;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 启用自动备份
        enabled_check = QCheckBox("启用自动备份")
        enabled_check.setChecked(getattr(self.main_window, 'auto_backup_enabled', False))
        layout.addWidget(enabled_check)
        
        # 备份模式
        mode_label = QLabel("备份模式：")
        layout.addWidget(mode_label)
        
        mode_layout = QHBoxLayout()
        scheduled_radio = QRadioButton("定时备份")
        on_close_radio = QRadioButton("关闭服务端时备份")
        
        current_mode = getattr(self.main_window, 'auto_backup_mode', 'scheduled')
        if current_mode == 'on_close':
            on_close_radio.setChecked(True)
        else:
            scheduled_radio.setChecked(True)
        
        mode_layout.addWidget(scheduled_radio)
        mode_layout.addWidget(on_close_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # 备份间隔（仅定时模式显示）
        interval_layout = QHBoxLayout()
        interval_label = QLabel("备份间隔（分钟）：")
        interval_spin = QSpinBox()
        interval_spin.setRange(1, 10080)  # 最大7天
        interval_spin.setValue(getattr(self.main_window, 'auto_backup_interval', 60))
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(interval_spin)
        layout.addLayout(interval_layout)
        
        # 最大保留数量
        max_count_layout = QHBoxLayout()
        max_count_label = QLabel("最大保留数量：")
        max_count_spin = QSpinBox()
        max_count_spin.setRange(1, 100)
        max_count_spin.setValue(getattr(self.main_window, 'auto_backup_max_count', 10))
        max_count_layout.addWidget(max_count_label)
        max_count_layout.addWidget(max_count_spin)
        layout.addLayout(max_count_layout)
        
        # 提示文字
        hint_label = QLabel("提示：定时备份仅在程序运行时生效；\n关闭服务端时备份会在关闭窗口前自动执行，\n备份完成前窗口不会关闭。\n备份完成后会自动清理超过最大保留数量的旧备份。")
        hint_label.setStyleSheet("color: #888888; font-size: 11px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a4a7a;
                color: #ffffff;
                border: 1px solid #4a90d9;
            }
            QPushButton:hover {
                background-color: #2a5a8a;
            }
        """)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            # 保存设置
            self.main_window.auto_backup_enabled = enabled_check.isChecked()
            self.main_window.auto_backup_interval = interval_spin.value()
            self.main_window.auto_backup_max_count = max_count_spin.value()
            # 保存备份模式
            if on_close_radio.isChecked():
                self.main_window.auto_backup_mode = 'on_close'
            else:
                self.main_window.auto_backup_mode = 'scheduled'
            self.main_window.save_config()
            
            # 重启自动备份定时器
            if hasattr(self.main_window, 'restart_auto_backup_timer'):
                self.main_window.restart_auto_backup_timer()
            
            show_frameless_warning(self, "提示", "自动备份设置已保存！")
    
    def mousePressEvent(self, event):
        """鼠标按下事件（拖动窗口）"""
        if event.button() == Qt.LeftButton and event.y() < 36:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件（拖动窗口）"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.dragging = False



class CopyFileThread(QThread):
    """文件复制后台线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, src, dst):
        super().__init__()
        self.src = src
        self.dst = dst
    
    def run(self):
        try:
            if not os.path.exists(self.src):
                self.finished.emit(False, "源文件不存在")
                return
            
            file_size = os.path.getsize(self.src)
            copied = 0
            chunk_size = 1024 * 1024  # 1MB
            
            with open(self.src, 'rb') as f_src:
                with open(self.dst, 'wb') as f_dst:
                    while True:
                        chunk = f_src.read(chunk_size)
                        if not chunk:
                            break
                        f_dst.write(chunk)
                        copied += len(chunk)
                        progress = int((copied / file_size) * 100)
                        self.progress.emit(progress)
            
            # 复制修改时间
            shutil.copystat(self.src, self.dst)
            
            self.finished.emit(True, "文件替换成功")
        except Exception as e:
            self.finished.emit(False, f"文件替换失败: {str(e)}")


class ServerCheckThread(QThread):
    """服务端状态检查后台线程（性能优化：避免阻塞UI线程导致启动卡顿）"""
    finished = pyqtSignal(bool)  # True: 服务端在运行, False: 服务端未运行
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
    
    def run(self):
        try:
            # 先检查进程
            if not self.main_window.is_server_running():
                self.finished.emit(False)
                return
            
            # 进程在运行，检查服务端端口7001
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)  # 减少超时时间为1秒
                    result = s.connect_ex(("127.0.0.1", 7001))
                    if result == 0:
                        self.finished.emit(True)
                        return
            except:
                pass
            
            # 端口未开放，检查数据库
            if not self.main_window.db_manager and self.main_window.server_path:
                self.main_window.db_manager = DatabaseManager(self.main_window.server_path)
            
            if self.main_window.db_manager:
                ready = self.main_window.db_manager.check_ready()
                self.finished.emit(ready)
            else:
                self.finished.emit(False)
                
        except Exception as e:
            self.finished.emit(False)



def get_app_dir():

    if getattr(sys, 'frozen', False):

        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))


# 账号保管文件加密密钥（启动器内置，只有启动器能解密）
ACCOUNT_ENCRYPT_KEY = b"DNF90_Launcher_Account_Key_2024"


def xor_encrypt(data, key):
    """简单XOR加密"""
    key_len = len(key)
    return bytes([data[i] ^ key[i % key_len] for i in range(len(data))])


def save_account_to_file(username, password):
    """保存账号密码到加密文件"""
    try:
        import base64
        app_dir = get_app_dir()
        account_file = os.path.join(app_dir, "acc.dat")
        
        # 构造账号数据
        account_data = json.dumps({
            "username": username,
            "password": password,
            "saved_at": datetime.now().isoformat()
        })
        
        # XOR加密
        encrypted = xor_encrypt(account_data.encode('utf-8'), ACCOUNT_ENCRYPT_KEY)
        # Base64编码
        encoded = base64.b64encode(encrypted)
        
        with open(account_file, 'wb') as f:
            f.write(encoded)
        
        return True
    except Exception as e:
        return False


def load_account_from_file():
    """从加密文件读取账号密码"""
    try:
        import base64
        app_dir = get_app_dir()
        account_file = os.path.join(app_dir, "acc.dat")
        
        if not os.path.exists(account_file):
            return None, None
        
        with open(account_file, 'rb') as f:
            encoded = f.read()
        
        # Base64解码
        encrypted = base64.b64decode(encoded)
        # XOR解密
        decrypted = xor_encrypt(encrypted, ACCOUNT_ENCRYPT_KEY)
        account_data = json.loads(decrypted.decode('utf-8'))
        
        return account_data.get("username"), account_data.get("password")
    except Exception as e:
        return None, None


def write_error_log(error_type, error_message, traceback_info=None):
    """写入错误日志（只有出现错误时才生成文件）"""
    try:
        import traceback
        app_dir = get_app_dir()
        error_log_file = os.path.join(app_dir, "error.log")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_content = "=" * 60 + "\n"
        log_content += f"[错误时间] {timestamp}\n"
        log_content += f"[错误类型] {error_type}\n"
        log_content += f"[错误信息] {error_message}\n"
        
        if traceback_info:
            log_content += f"[堆栈信息]\n{traceback_info}\n"
        
        log_content += "=" * 60 + "\n\n"
        
        # 追加写入错误日志
        with open(error_log_file, 'a', encoding='utf-8') as f:
            f.write(log_content)
        
        return True
    except Exception as e:
        return False


# 运行日志记录器
class RuntimeLogger:
    """程序运行日志记录器，程序关闭时输出到文件"""
    _instance = None
    _logs = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def log(cls, message):
        """记录运行日志（自动将路径转换为Windows反斜杠格式）"""
        # 自动将路径中的正斜杠转换为反斜杠（Windows标准格式）
        message = message.replace('/', '\\')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cls._logs.append(f"[{timestamp}] {message}")
    
    @classmethod
    def save_to_file(cls):
        """程序关闭时保存运行日志到文件"""
        try:
            if not cls._logs:
                return False
            
            app_dir = get_app_dir()
            runtime_log_file = os.path.join(app_dir, "runtime.log")
            
            log_content = "=" * 60 + "\n"
            log_content += f"程序运行日志 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            log_content += "=" * 60 + "\n\n"
            
            for log_entry in cls._logs:
                log_content += log_entry + "\n"
            
            log_content += "\n" + "=" * 60 + "\n"
            log_content += f"程序关闭时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            log_content += "=" * 60 + "\n"
            
            with open(runtime_log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return True
        except Exception as e:
            return False
    
    @classmethod
    def clear(cls):
        """清空日志"""
        cls._logs = []


# ========== 自定义密码框：最后一位明文 ==========
class LastCharPasswordEdit(QLineEdit):
    """密码框，最后一位显示明文，其他显示密文"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._real_password = ""
        self._mask_char = "•"  # 密文字符
        self._show_last_char = True  # 是否显示最后一位明文
        
        # 设置正常显示模式（我们自己控制显示内容）
        self.setEchoMode(QLineEdit.Normal)
        
        # 连接文本变化信号
        self.textChanged.connect(self._on_text_changed)
    
    def _on_text_changed(self, text):
        """处理文本变化"""
        # 阻止信号，避免递归
        self.blockSignals(True)
        
        # 如果文本为空，清空真实密码
        if not text:
            self._real_password = ""
            self.blockSignals(False)
            return
        
        # 判断是输入还是删除
        if len(text) > len(self._real_password):
            # 输入：新增的字符就是最后一位
            added_char = text[-1]
            self._real_password += added_char
        elif len(text) < len(self._real_password):
            # 删除：从真实密码中移除对应位置
            # 计算删除了多少字符
            diff = len(self._real_password) - len(text)
            self._real_password = self._real_password[:-diff] if diff > 0 else self._real_password
        
        # 更新显示内容
        self._update_display()
        
        self.blockSignals(False)
    
    def _update_display(self):
        """更新显示内容"""
        if not self._real_password:
            self.setText("")
            return
        
        if self._show_last_char and len(self._real_password) > 0:
            # 显示最后一位明文，其他显示密文
            display = self._mask_char * (len(self._real_password) - 1) + self._real_password[-1]
        else:
            # 全部显示密文
            display = self._mask_char * len(self._real_password)
        
        # 直接设置文本，不触发textChanged
        QLineEdit.setText(self, display)
        
        # 将光标移到末尾
        self.setCursorPosition(len(display))
    
    def text(self):
        """返回真实密码"""
        return self._real_password
    
    def setText(self, text):
        """设置密码"""
        self._real_password = text or ""
        self._update_display()
    
    def setMaskChar(self, char):
        """设置密文字符"""
        self._mask_char = char
        self._update_display()
    
    def setShowLastChar(self, show):
        """设置是否显示最后一位明文"""
        self._show_last_char = show
        self._update_display()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 处理全选
        if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self.selectAll()
            return
        
        # 处理删除键
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.hasSelectedText():
                # 有选中文本时，删除选中部分
                start = self.selectionStart()
                end = start + len(self.selectedText())
                self._real_password = self._real_password[:start] + self._real_password[end:]
                self._update_display()
                self.setCursorPosition(start)
                return
            elif event.key() == Qt.Key_Backspace and self.cursorPosition() > 0:
                # 退格删除
                pos = self.cursorPosition()
                self._real_password = self._real_password[:pos-1] + self._real_password[pos:]
                self._update_display()
                self.setCursorPosition(pos - 1)
                return
            elif event.key() == Qt.Key_Delete and self.cursorPosition() < len(self._real_password):
                # 删除键
                pos = self.cursorPosition()
                self._real_password = self._real_password[:pos] + self._real_password[pos+1:]
                self._update_display()
                self.setCursorPosition(pos)
                return
        
        # 其他键交给父类处理
        super().keyPressEvent(event)


# ========== 数据库抽象层：自动支持MySQL和SQLite ==========
class DatabaseManager:
    """数据库管理类，根据instance.json配置自动选择MySQL或SQLite"""
    
    def __init__(self, server_path):
        self.server_path = server_path
        self.config = None
        self.db_mode = None
        self._load_config()
    
    def _load_config(self):
        """加载数据库配置（同时支持原版和Python版服务端路径）"""
        try:
            # 优先尝试Python版服务端路径（根目录下的instance.json）
            config_file = os.path.join(self.server_path, "instance.json")
            if not os.path.exists(config_file):
                # 如果不存在，尝试原版服务端路径（runtime/config/instance.json）
                config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            
            self.config = ConfigCache.read_json(config_file)
            if self.config:
                db_config = self.config.get("database", {})
                self.db_mode = db_config.get("mode", "portable")
        except:
            self.config = None
            self.db_mode = "portable"
    
    def is_sqlite(self):
        """判断是否为SQLite模式（优先从配置文件读取，其次从instance.json读取）"""
        # 1. 优先从启动器配置文件读取数据库模式
        try:
            import sys
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(os.path.abspath(__file__))
            
            config_file = os.path.join(app_dir, "config.lau")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                db_mode = config.get('db_mode', '')
                if db_mode:
                    return db_mode == "sqlite"
        except:
            pass
        
        # 2. 如果配置文件中没有，严格根据instance.json的mode配置判断
        if self.db_mode == "sqlite":
            return True
        
        # 3. 都没有的话，默认返回False（MySQL模式）
        return False
    
    def get_sqlite_path(self):
        """获取SQLite数据库文件路径"""
        if self.config:
            db_config = self.config.get("database", {})
            db_path = db_config.get("path", "data/dnf90.db")
            return os.path.join(self.server_path, "runtime", db_path)
        return os.path.join(self.server_path, "runtime", "data", "dnf90.db")
    
    def check_ready(self):
        """检查数据库是否就绪"""
        if self.is_sqlite():
            # SQLite模式：检查数据库文件是否存在且可访问
            db_path = self.get_sqlite_path()
            if not os.path.exists(db_path):
                return False
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dnf_login_accounts'")
                result = cursor.fetchone()
                conn.close()
                return result is not None
            except:
                return False
        else:
            # MySQL模式：检查端口是否开放
            if self.config:
                db_config = self.config.get("database", {})
                host = db_config.get("host", "127.0.0.1")
                port = db_config.get("port", 13306)
                return self._check_port_open(host, port, timeout=2)
            return False
    
    def _check_port_open(self, host, port, timeout=2):
        """检查端口是否开放"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
                return result == 0
        except:
            return False
    
    def verify_account(self, username, password):
        """验证账号密码"""
        import bcrypt
        
        if self.is_sqlite():
            return self._verify_sqlite(username, password)
        else:
            return self._verify_mysql(username, password)
    
    def _verify_sqlite(self, username, password):
        """SQLite模式验证账号"""
        try:
            import sqlite3
            import bcrypt
            
            db_path = self.get_sqlite_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT password_hash FROM dnf_login_accounts WHERE username = ? AND state = 'active'",
                (username,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                stored_hash = result[0]
                if isinstance(stored_hash, bytes):
                    stored_hash = stored_hash.decode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    return True, "登录成功"
                else:
                    return False, "密码错误"
            else:
                return False, "账号不存在或已禁用"
        except Exception as e:
            import traceback
            write_error_log("SQLite登录验证异常", str(e), traceback.format_exc())
            return False, "验证失败: {}".format(str(e))
    
    def _verify_mysql(self, username, password):
        """MySQL模式验证账号"""
        try:
            import pymysql
            import bcrypt
            
            db_config = self.config["database"]
            conn = pymysql.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                database=db_config["name"],
                charset="utf8mb4"
            )
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT password_hash FROM dnf_login_accounts WHERE username = %s AND state = 'active'",
                (username,)
            )
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                stored_hash = result[0]
                if isinstance(stored_hash, bytes):
                    stored_hash = stored_hash.decode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    return True, "登录成功"
                else:
                    return False, "密码错误"
            else:
                return False, "账号不存在或已禁用"
        except Exception as e:
            import traceback
            write_error_log("MySQL登录验证异常", str(e), traceback.format_exc())
            return False, "验证失败: {}".format(str(e))
    
    def register_account(self, username, password):
        """注册账号"""
        if self.is_sqlite():
            return self._register_sqlite(username, password)
        else:
            return self._register_mysql(username, password)
    
    def _register_sqlite(self, username, password):
        """SQLite模式注册账号"""
        try:
            import sqlite3
            import bcrypt
            import uuid
            import re
            
            # 验证账号格式
            if not username or len(username) < 4 or len(username) > 20:
                return False, "账号长度必须为4-20个字符"
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                return False, "账号只能包含字母、数字和下划线"
            
            # 验证密码格式
            if not password or len(password) < 8 or len(password) > 72:
                return False, "密码长度必须为8-72个字符"
            
            db_path = self.get_sqlite_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查账号是否已存在
            cursor.execute(
                "SELECT account_id FROM dnf_login_accounts WHERE username = ?",
                (username,)
            )
            if cursor.fetchone():
                conn.close()
                return False, "账号已存在"
            
            # 创建新账号
            account_id = "dnf:{}".format(uuid.uuid4().hex)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                """INSERT INTO dnf_login_accounts
                   (account_id, username, password_hash, state, created_at, updated_at, last_login_at)
                   VALUES (?, ?, ?, 'active', ?, ?, ?)""",
                (account_id, username, password_hash, now, now, now)
            )
            conn.commit()
            conn.close()
            
            return True, "账号 {} 注册成功".format(username)
        except Exception as e:
            import traceback
            write_error_log("SQLite账号注册异常", str(e), traceback.format_exc())
            return False, "注册失败: {}".format(str(e))
    
    def _register_mysql(self, username, password):
        """MySQL模式注册账号"""
        try:
            import pymysql
            import bcrypt
            import uuid
            import re
            
            # 验证账号格式
            if not username or len(username) < 4 or len(username) > 20:
                return False, "账号长度必须为4-20个字符"
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                return False, "账号只能包含字母、数字和下划线"
            
            # 验证密码格式
            if not password or len(password) < 8 or len(password) > 72:
                return False, "密码长度必须为8-72个字符"
            
            db_config = self.config["database"]
            conn = pymysql.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                database=db_config["name"],
                charset="utf8mb4"
            )
            cursor = conn.cursor()
            
            # 检查账号是否已存在
            cursor.execute(
                "SELECT account_id FROM dnf_login_accounts WHERE username = %s",
                (username,)
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return False, "账号已存在"
            
            # 创建新账号
            account_id = "dnf:{}".format(uuid.uuid4().hex)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                """INSERT INTO dnf_login_accounts
                   (account_id, username, password_hash, state, created_at, updated_at, last_login_at)
                   VALUES (%s, %s, %s, 'active', %s, %s, %s)""",
                (account_id, username, password_hash, now, now, now)
            )
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True, "账号 {} 注册成功".format(username)
        except Exception as e:
            import traceback
            write_error_log("MySQL账号注册异常", str(e), traceback.format_exc())
            return False, "注册失败: {}".format(str(e))


class TitleBar(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setObjectName("titleBar")

        self.setFixedHeight(32)

        self.parent_window = parent

        self.dragging = False

        self.drag_position = QPoint()

        self.back_btn = None  # 返回按钮

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)


        # 左侧返回按钮（默认隐藏，在非路径页面时显示）
        self.back_btn = QPushButton("←")

        self.back_btn.setObjectName("navBtn")

        self.back_btn.setFixedSize(45, 32)

        self.back_btn.setCursor(Qt.PointingHandCursor)

        self.back_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; "
            "color: #ffffff; font-size: 14px; font-weight: bold; }"
        )

        self.back_btn.clicked.connect(self.go_back)

        self.back_btn.setVisible(False)

        layout.addWidget(self.back_btn)


        # 标题文字（已移除，保留占位）
        self.title_label = QLabel("")

        self.title_label.setObjectName("titleLabel")

        self.title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; font-family: 'Noto Sans SC', 'Microsoft YaHei';")

        self.title_label.setAlignment(Qt.AlignCenter)

        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(self.title_label)


        # 右侧容器（关闭按钮，移至最右侧）

        right_container = QWidget()

        right_layout = QHBoxLayout(right_container)

        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.setSpacing(0)

        right_container.setFixedWidth(45)


        # 关闭按钮
        self.close_btn = QPushButton("✕")

        self.close_btn.setObjectName("closeBtn")

        self.close_btn.setFixedSize(45, 32)

        self.close_btn.setCursor(Qt.PointingHandCursor)

        self.close_btn.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")

        self.close_btn.clicked.connect(self.close_window)

        right_layout.addWidget(self.close_btn)


        layout.addWidget(right_container)

    

    def go_back(self):

        """返回上一页面"""
        # 记录用户操作到状态栏
        if hasattr(self.parent_window, 'update_status_bar'):
            self.parent_window.update_status_bar("点击返回")

        if hasattr(self.parent_window, 'stacked_widget'):

            current = self.parent_window.stacked_widget.currentWidget()

            if current == self.parent_window.login_page:

                # 当前在登录页面 → 返回主菜单
                self.parent_window.switch_to_main()

            elif current == self.parent_window.main_page:

                # 当前在主菜单 → 切换到路径设置（保留已输入的路径）
                self.parent_window.switch_to_path_setup(clear_input=False)

            else:

                # 其他页面 → 切换到主菜单
                self.parent_window.switch_to_main()

    

    def set_back_button_visible(self, visible):

        """设置返回按钮可见性（返回按钮已移除，此方法为空操作）"""

        if self.back_btn is not None:

            if visible:

                self.back_btn.show()

            else:

                self.back_btn.hide()

    

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = True

            self.drag_position = event.globalPos() - self.parent_window.frameGeometry().topLeft()

            event.accept()

    

    def mouseDoubleClickEvent(self, event):

        """双击标题栏最小化程序"""

        if event.button() == Qt.LeftButton:

            self.parent_window.showMinimized()

            event.accept()

    

    def mouseMoveEvent(self, event):

        if self.dragging and event.buttons() & Qt.LeftButton:

            self.parent_window.move(event.globalPos() - self.drag_position)

            event.accept()

    

    def mouseReleaseEvent(self, event):

        self.dragging = False

    

    def show_minimized(self):

        self.parent_window.showMinimized()

    

    def minimize_window(self):

        """最小化窗口"""

        self.parent_window.showMinimized()


    def close_window(self):

        """关闭窗口"""

        self.parent_window.close()



class PathSetupPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.main_window = parent

        self.init_ui()

    

    def init_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(20, 15, 20, 15)

        layout.setSpacing(10)

        

        # 客户端路径输入区域

        client_layout = QHBoxLayout()

        client_layout.setSpacing(8)

        

        self.client_path_input = QLineEdit()

        self.client_path_input.setPlaceholderText("请输入或选择DNF客户端目录路径")

        self.client_path_input.setMinimumHeight(36)

        self.client_path_input.setStyleSheet("font-size: 12px;")

        client_layout.addWidget(self.client_path_input)

        

        client_browse_btn = QPushButton("浏览")

        client_browse_btn.setMinimumHeight(36)

        client_browse_btn.setMaximumHeight(36)

        client_browse_btn.setMinimumWidth(70)

        client_browse_btn.clicked.connect(self.browse_client_path)

        client_layout.addWidget(client_browse_btn)

        

        layout.addLayout(client_layout)

        # 客户端路径提示文字
        client_desc = QLabel("请选择 dnf.exe 所在目录")
        client_desc.setStyleSheet("color: #888888; font-size: 11px; line-height: 1.2;")
        client_desc.setAlignment(Qt.AlignLeft)
        client_desc.setWordWrap(True)
        layout.addWidget(client_desc)

        

        # 服务端路径输入区域

        self.path_input = QLineEdit()

        self.path_input.setPlaceholderText("请输入或选择服务端目录路径")

        self.path_input.setMinimumHeight(36)

        self.path_input.setStyleSheet("font-size: 12px;")

        layout.addWidget(self.path_input)

        

        # 鎻愮璇紙绉诲叆鏈嶅姟绔矾寰勬鍜屾寜閽箣闂达級

        desc = QLabel("请选择服务端根目录（包含 runtime、deploy 等文件夹）")

        desc.setStyleSheet("color: #888888; font-size: 11px; line-height: 1.2;")

        desc.setAlignment(Qt.AlignLeft)

        desc.setWordWrap(True)

        layout.addWidget(desc)

        

        # 底部按钮行：确认 + 浏览（服务端的浏览按钮）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 确认按钮（103）
        confirm_btn = QPushButton("确认")
        confirm_btn.setMinimumHeight(40)
        confirm_btn.clicked.connect(self.confirm_path)
        btn_layout.addWidget(confirm_btn)
        
        server_browse_btn = QPushButton("浏览")
        server_browse_btn.setMinimumHeight(40)
        server_browse_btn.clicked.connect(self.browse_server_path)
        btn_layout.addWidget(server_browse_btn)
        
        layout.addLayout(btn_layout)

        # 安装客户端补丁按钮（104）：初始模式，始终显示"安装客户端补丁"
        self.install_patch_btn = QPushButton("安装客户端补丁")
        self.install_patch_btn.setMinimumHeight(38)
        self.install_patch_btn.clicked.connect(self.on_install_patch_clicked)
        layout.addWidget(self.install_patch_btn)

        # 操作历史/错误提示区域（继承自主页面操作日志样式）
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setMinimumHeight(100)
        self.history_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_text.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.history_text, 1)

        # 从共享日志数据中读取历史记录
        if hasattr(self.main_window, 'shared_logs'):
            for log_msg in self.main_window.shared_logs:
                self.history_text.append(log_msg)

        layout.addStretch()

    

    def browse_server_path(self):

        dir_path = QFileDialog.getExistingDirectory(self, "閫夋嫨鏈嶅姟绔洰褰")

        if dir_path:

            self.path_input.setText(dir_path)

    

    def browse_client_path(self):

        dir_path = QFileDialog.getExistingDirectory(self, "选择DNF客户端目录")

        if dir_path:

            self.client_path_input.setText(dir_path)

    def add_history(self, message, is_error=False):
        """向操作历史添加消息（使用共享日志）"""
        if is_error:
            self.main_window.log(f"[错误] {message}")
        else:
            self.main_window.log(message)

    def confirm_path(self):

        path = self.path_input.text().strip()

        if not path:

            self.add_history("请输入服务端路径！", is_error=True)

            return

        if not os.path.exists(path):

            self.add_history("服务端路径不存在！", is_error=True)

            return

        # 验证服务端目录结构完整性
        if hasattr(self.main_window, 'validate_server_path'):
            valid, msg = self.main_window.validate_server_path(path)
            if not valid:
                self.add_history("路径验证失败: {}".format(msg), is_error=True)
                self.add_history("请确认服务端目录包含 dnf90_server.exe 等必要文件", is_error=True)
                return
            self.add_history("服务端路径验证通过")

        # 检查管理员权限
        if hasattr(self.main_window, 'is_admin') and not self.main_window.is_admin():
            self.add_history("提示: 建议以管理员身份运行，否则可能导致服务端启动失败")

        

        client_path = self.client_path_input.text().strip()

        # 验证客户端路径
        if client_path:
            if not os.path.exists(client_path):
                self.add_history("客户端路径不存在！", is_error=True)
                return
            dnf_exe = os.path.join(client_path, "DNF.exe")
            if not os.path.exists(dnf_exe):
                self.add_history("客户端目录中未找到 DNF.exe，请确认路径是否正确", is_error=True)
                return
            self.add_history("客户端路径验证通过")

        # 保存路径（恢复底板简单模式）
        self.main_window.server_path = path
        self.main_window.client_path = client_path

        # 初始化数据库管理器（自动支持MySQL和SQLite）
        self.main_window.db_manager = DatabaseManager(path)

        self.main_window.save_config()

        self.add_history("路径配置已保存")

        self.main_window.switch_to_main()


    def on_install_patch_clicked(self):
        """安装补丁按钮点击事件（104）：初始模式，直接开始安装补丁"""
        self.start_install_patch()


    def start_install_patch(self):
        """启动安装客户端补丁"""
        server_path = self.path_input.text().strip()
        client_path = self.client_path_input.text().strip()

        if not server_path:
            self.add_history("请先设置服务端路径！", is_error=True)
            return

        if not client_path:
            self.add_history("请先设置客户端路径！", is_error=True)
            return

        if not os.path.exists(server_path):
            self.add_history("服务端路径不存在！", is_error=True)
            return

        if not os.path.exists(client_path):
            self.add_history("客户端路径不存在！", is_error=True)
            return

        self.add_history("开始安装客户端补丁...")

        # 保存路径（避免用户忘记点击确认）
        self.main_window.server_path = server_path
        self.main_window.client_path = client_path
        self.main_window.save_config()

        # 切换到安装页面
        self.main_window.start_install_patch(server_path, client_path)



class MainMenuPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.main_window = parent

        self.init_ui()

    

    def init_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(20, 15, 20, 15)

        layout.setSpacing(12)

        # 当前账号信息（和服务端路径文字风格一致）
        self.current_account_label = QLabel("当前账号: 未登录")
        self.current_account_label.setStyleSheet(
            "color: #a0a0a0; font-size: 11px;"
        )
        self.current_account_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.current_account_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #333333;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 两列网格布局
        from PyQt5.QtWidgets import QGridLayout

        grid_layout = QGridLayout()

        grid_layout.setSpacing(10)


        # 左侧列：运行GM工具、数据迁移
        gm_btn = QPushButton("运行GM工具")

        gm_btn.setMinimumHeight(40)

        gm_btn.clicked.connect(self.run_gmtool)

        grid_layout.addWidget(gm_btn, 0, 0)


        migrate_btn = QPushButton("存档管理")

        migrate_btn.setMinimumHeight(40)

        migrate_btn.clicked.connect(self.main_window.show_migrate_dialog)

        self.migrate_btn = migrate_btn

        grid_layout.addWidget(migrate_btn, 1, 0)


        # 右侧列：登录、停止服务
        login_btn = QPushButton("启动服务")

        login_btn.setMinimumHeight(40)

        login_btn.clicked.connect(self.handle_login_button)

        self.login_btn = login_btn

        grid_layout.addWidget(login_btn, 0, 1)


        stop_btn = QPushButton("停止服务")

        stop_btn.setMinimumHeight(40)

        stop_btn.clicked.connect(self.run_stop)

        stop_btn.setEnabled(False)

        self.stop_btn = stop_btn

        grid_layout.addWidget(stop_btn, 1, 1)


        layout.addLayout(grid_layout)


        # 日志区域（高度继续增加，底边延伸至状态栏上边界）
        self.status_text = QTextEdit()

        self.status_text.setReadOnly(True)

        self.status_text.setMinimumHeight(200)

        self.status_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.status_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.status_text.setFrameShape(QFrame.NoFrame)

        layout.addWidget(self.status_text, 1)

    

    def log(self, message):
        """使用共享日志方法"""
        self.main_window.log(message)

    def update_current_account(self, username=None):
        """更新当前账号信息"""
        if username:
            self.current_account_label.setText("当前账号: {}".format(username))
        else:
            self.current_account_label.setText("当前账号: 未登录")

    

    def run_login(self):

        try:
            # 记录用户操作到状态栏
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar("点击登录")

            launcher_exe = os.path.join(self.main_window.server_path, "runtime", "bin", "DNF90Launcher.exe")

            if os.path.exists(launcher_exe):

                self.log("正在启动一键登录...")

                os.environ['DNF_RESIDENT_CHANNEL_ID'] = '19'

                subprocess.Popen([launcher_exe], cwd=self.main_window.server_path)

            else:

                self.log(f"错误: 未找到 {launcher_exe}")

                show_frameless_error(self, "错误", f"未找到启动器:\n{launcher_exe}")

        except Exception as e:

            self.log(f"启动失败: {e}")

            show_frameless_error(self, "错误", f"启动失败:\n{e}")

    

    def handle_login_button(self):
        """处理账号登录/启动服务按钮点击事件"""
        # 记录用户操作到状态栏
        if hasattr(self.main_window, 'update_status_bar'):
            action = "启动服务" if self.login_btn.text() == "启动服务" else "账号登录"
            self.main_window.update_status_bar(f"点击{action}")

        if self.login_btn.text() == "启动服务":
            # 先进行PVF校验
            self.check_pvf_and_start_server()
        else:
            # 正常切换到登录页面
            self.main_window.switch_to_login()
    
    def check_pvf_and_start_server(self):
        """PVF校验后启动服务端"""
        server_path = self.main_window.server_path
        client_path = self.main_window.client_path
        
        # 检查路径是否配置
        if not server_path or not client_path:
            self.log("错误: 请先配置服务端和客户端路径")
            return
        
        server_pvf = os.path.join(server_path, "runtime", "data", "dnf", "Script.pvf")
        client_pvf = os.path.join(client_path, "Script.pvf")
        
        # 检查PVF文件是否存在
        server_exists = os.path.exists(server_pvf)
        client_exists = os.path.exists(client_pvf)
        
        if not server_exists and not client_exists:
            self.log("警告: 服务端和客户端均未找到 Script.pvf 文件，直接启动服务端")
            self.start_server_after_pvf_check()
            return
        elif not server_exists:
            self.log("警告: 服务端未找到 Script.pvf 文件，直接启动服务端")
            self.start_server_after_pvf_check()
            return
        elif not client_exists:
            self.log("警告: 客户端未找到 Script.pvf 文件，直接启动服务端")
            self.start_server_after_pvf_check()
            return
        
        # 比对文件大小和修改时间
        server_stat = os.stat(server_pvf)
        client_stat = os.stat(client_pvf)
        
        if server_stat.st_size == client_stat.st_size and server_stat.st_mtime == client_stat.st_mtime:
            self.log("PVF文件校验通过，服务端与客户端版本一致")
            self.start_server_after_pvf_check()
        else:
            self.log("检测到PVF文件不一致，打开PVF校验窗口...")
            # 显示独立的PVF校验窗口
            self.pvf_window = PvfCheckWindow(server_path, client_path, self)
            self.pvf_window.show()
            # 窗口关闭后继续启动服务端
            self.pvf_window.destroyed.connect(self.start_server_after_pvf_check)
    
    def start_server_after_pvf_check(self):
        """PVF校验完成后启动服务端"""
        # 如果按钮状态不是"启动服务"，说明可能已经在启动中或已启动
        if self.login_btn.text() != "启动服务":
            return
        
        self.log("正在启动服务...")
        QApplication.processEvents()
        self.login_btn.setEnabled(False)
        self.login_btn.setText("启动中...")
        # 显示进度条
        if hasattr(self.main_window, 'show_progress'):
            self.main_window.show_progress(True)
            self.main_window.set_progress(0, "启动中")

        if self.main_window.start_server_and_wait():
            self.log("服务启动成功")
            self.login_btn.setText("账号登录")
            self.stop_btn.setEnabled(True)
            # 隐藏进度条
            if hasattr(self.main_window, 'show_progress'):
                self.main_window.show_progress(False)
        else:
            self.log("错误: 服务启动失败，请检查服务端目录配置")
            self.login_btn.setText("启动服务")
            # 隐藏进度条
            if hasattr(self.main_window, 'show_progress'):
                self.main_window.show_progress(False)
        self.login_btn.setEnabled(True)

    def run_gmtool(self):

        try:
            # 记录用户操作到状态栏
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar("点击GM工具")

            # 获取launcher.exe所在目录
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(os.path.abspath(__file__))

            module_dir = os.path.join(app_dir, "module")
            gm_exe = os.path.join(module_dir, "gmtool.exe")

            if os.path.exists(gm_exe):

                self.log("正在启动GM工具...")

                subprocess.Popen([gm_exe], cwd=module_dir)

            else:

                self.log(f"错误: 未找到 {gm_exe}")

                show_frameless_error(self, "错误", f"未找到GM工具:\n{gm_exe}")

        except Exception as e:

            self.log(f"启动失败: {e}")

            show_frameless_error(self, "错误", f"启动失败:\n{e}")

    

    def run_stop(self):
        """停止服务 - 开启关闭服务端时备份时，先关闭服务端再执行自动备份；否则直接停止服务"""
        try:
            # 记录用户操作到状态栏
            if hasattr(self.main_window, 'update_status_bar'):
                self.main_window.update_status_bar("点击停止服务")

            # 检查是否开启了"关闭服务端时备份"功能
            auto_backup_mode = getattr(self.main_window, 'auto_backup_mode', '')
            auto_backup_enabled = getattr(self.main_window, 'auto_backup_enabled', False)
            
            if auto_backup_enabled and auto_backup_mode == 'on_close':
                # 新逻辑：禁用关闭按钮，先关闭服务端，再执行自动备份
                self.log("开始关闭服务端并自动备份...")
                
                # 禁用关闭按钮
                if hasattr(self.main_window, 'title_bar') and hasattr(self.main_window.title_bar, 'close_btn'):
                    self.main_window.title_bar.close_btn.setEnabled(False)
                    self.log("关闭按钮已禁用，备份完成前无法关闭窗口")
                
                # 禁用停止服务按钮，防止重复点击
                self.stop_btn.setEnabled(False)
                self.stop_btn.setText("停止中...")
                
                # 记录标记：服务端关闭后需要执行自动备份
                self.main_window._backup_after_stop = True
                
                # 执行停止服务逻辑（测试版：直接终止dnf90_server.exe进程）
                self.log("  正在终止 dnf90_server.exe 进程...")
                try:
                    result = subprocess.run(
                        ["taskkill", "/F", "/IM", "dnf90_server.exe"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.log("  dnf90_server.exe 进程已终止")
                    else:
                        self.log("  dnf90_server.exe 进程未运行或终止失败")
                except Exception as e:
                    self.log("  终止进程时出错: {}".format(e))
                
                # 延迟15秒后检查服务端状态，如仍在运行则强制终止进程
                QTimer.singleShot(15000, self.check_after_stop)
                
            else:
                # 未开启"关闭服务端时备份"功能，直接停止服务
                self.log("正在停止服务...")
                
                # 禁用停止服务按钮，防止重复点击
                self.stop_btn.setEnabled(False)
                self.stop_btn.setText("停止中...")
                
                # 显示进度条
                if hasattr(self.main_window, 'show_progress'):
                    self.main_window.show_progress(True)
                    self.main_window.set_progress(0, "停止中")
                
                # 执行停止服务逻辑（测试版：直接终止dnf90_server.exe进程）
                self.log("  正在终止 dnf90_server.exe 进程...")
                try:
                    result = subprocess.run(
                        ["taskkill", "/F", "/IM", "dnf90_server.exe"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.log("  dnf90_server.exe 进程已终止")
                    else:
                        self.log("  dnf90_server.exe 进程未运行或终止失败")
                except Exception as e:
                    self.log("  终止进程时出错: {}".format(e))
                
                # 延迟15秒后检查服务端状态，如仍在运行则强制终止进程
                QTimer.singleShot(15000, self.check_after_stop)
                
        except Exception as e:
            self.log(f"操作失败: {e}")
            # 恢复按钮状态
            self.stop_btn.setText("停止服务")
            self.stop_btn.setEnabled(True)
            if hasattr(self.main_window, 'title_bar') and hasattr(self.main_window.title_bar, 'close_btn'):
                self.main_window.title_bar.close_btn.setEnabled(True)
            show_frameless_error(self, "错误", f"操作失败:\n{e}")

    def check_after_stop(self):
        """停止服务后检查服务端状态，如仍在运行则强制终止进程"""
        # 使服务端状态缓存失效，确保获取最新状态
        ServerStatusCache.invalidate()
        
        if self.main_window.check_mysql_ready():
            self.log("服务仍在运行，尝试强制终止进程...")
            # 强制终止服务端相关进程
            self.force_kill_server_processes()
            # 再等待5秒后检查
            QTimer.singleShot(5000, self.final_check_after_stop)
        else:
            self.log("服务已停止")
            self.login_btn.setText("启动服务")
            self.stop_btn.setText("停止服务")
            self.stop_btn.setEnabled(False)
            # 隐藏进度条
            if hasattr(self.main_window, 'show_progress'):
                self.main_window.show_progress(False)
            
            # 如果设置了备份标记，服务端关闭后执行自动备份
            if getattr(self.main_window, '_backup_after_stop', False):
                self.main_window._backup_after_stop = False
                self.log("服务端已关闭，开始自动备份...")
                self.stop_btn.setText("备份中...")
                # 显示备份进度条
                if hasattr(self.main_window, 'show_progress'):
                    self.main_window.show_progress(True)
                    self.main_window.set_progress(0, "备份中")
                # 执行自动备份
                self.main_window.do_auto_backup()
                # 记录备份完成后的回调标记
                self.main_window._backup_from_stop_button = True

    def force_kill_server_processes(self):
        """强制终止服务端相关进程"""
        try:
            # 需要终止的进程列表（测试版：适配Python版服务端）
            processes_to_kill = [
                "dnf90_server.exe",
                "mysqld.exe"
            ]
            
            for proc_name in processes_to_kill:
                try:
                    result = subprocess.run(
                        ["taskkill", "/F", "/IM", proc_name],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.log(f"  已终止进程: {proc_name}")
                    else:
                        self.log(f"  进程 {proc_name} 未运行或终止失败")
                except Exception as e:
                    self.log(f"  终止进程 {proc_name} 时出错: {e}")
            
            self.log("强制终止进程完成")
            
        except Exception as e:
            self.log(f"强制终止进程失败: {e}")

    def final_check_after_stop(self):
        """最终检查服务端状态"""
        ServerStatusCache.invalidate()
        
        if self.main_window.check_mysql_ready():
            self.log("警告: 服务仍在运行，请手动检查并终止进程")
            self.stop_btn.setText("停止服务")
            self.stop_btn.setEnabled(True)
            # 恢复关闭按钮
            if hasattr(self.main_window, 'title_bar') and hasattr(self.main_window.title_bar, 'close_btn'):
                self.main_window.title_bar.close_btn.setEnabled(True)
        else:
            self.log("服务已停止")
            self.login_btn.setText("启动服务")
            self.stop_btn.setText("停止服务")
            self.stop_btn.setEnabled(False)
            # 隐藏进度条
            if hasattr(self.main_window, 'show_progress'):
                self.main_window.show_progress(False)
            
            # 如果设置了备份标记，服务端关闭后执行自动备份
            if getattr(self.main_window, '_backup_after_stop', False):
                self.main_window._backup_after_stop = False
                self.log("服务端已关闭，开始自动备份...")
                self.stop_btn.setText("备份中...")
                # 显示备份进度条
                if hasattr(self.main_window, 'show_progress'):
                    self.main_window.show_progress(True)
                    self.main_window.set_progress(0, "备份中")
                # 执行自动备份
                self.main_window.do_auto_backup()
                # 记录备份完成后的回调标记
                self.main_window._backup_from_stop_button = True



class LauncherWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.app_dir = get_app_dir()

        self.config_path = os.path.join(self.app_dir, "config.lau")

        self.backup_dir = os.path.join(self.app_dir, "backup")

        os.makedirs(self.backup_dir, exist_ok=True)

        self.server_path = ""

        self.client_path = ""

        self.db_mode = ""  # 数据库模式：mysql或sqlite（从配置文件读取）

        self.scroll_index = 0

        self.title_bar = None

        self.backup_worker = None

        self.auto_backup_timer = None  # 自动备份定时器

        self.current_user = ""

        self.current_password = ""

        # 数据库管理器（自动支持MySQL和SQLite）
        self.db_manager = None

        # 共享日志数据（所有页面共用）
        self.shared_logs = []

        self.load_config()

        self.init_ui()

        # 启动自动备份定时器
        self.restart_auto_backup_timer()

        # 记录程序启动日志
        RuntimeLogger.log("程序启动")
        if self.server_path:
            RuntimeLogger.log(f"服务端路径: {self.server_path}")
        if self.client_path:
            RuntimeLogger.log(f"客户端路径: {self.client_path}")

    

    def show_pvf_check(self):
        """显示PVF文件比对窗口"""
        try:
            if not hasattr(self, 'pvf_window') or self.pvf_window is None:
                self.pvf_window = PvfCheckWindow(self.server_path, self.client_path, self)
            self.pvf_window.show()
            self.pvf_window.raise_()
            self.pvf_window.activateWindow()
        except Exception as e:
            self.log(f"[错误] 显示PVF比对窗口失败: {str(e)}")
    

    def show_archive_manager(self):
        """显示存档管理独立窗口"""
        try:
            if not hasattr(self, 'archive_window') or self.archive_window is None:
                self.archive_window = ArchiveManagerWindow(self)
            self.archive_window.show()
            self.archive_window.raise_()
            self.archive_window.activateWindow()
        except Exception as e:
            self.log(f"[错误] 显示存档管理窗口失败: {str(e)}")
    

    def restart_auto_backup_timer(self):
        """重启自动备份定时器"""
        # 先停止现有的定时器
        if self.auto_backup_timer:
            self.auto_backup_timer.stop()
            self.auto_backup_timer.deleteLater()
            self.auto_backup_timer = None
        
        # 如果启用了自动备份，则启动新的定时器
        if getattr(self, 'auto_backup_enabled', False) and self.server_path:
            interval = getattr(self, 'auto_backup_interval', 60) * 60 * 1000  # 转换为毫秒
            self.auto_backup_timer = QTimer()
            self.auto_backup_timer.timeout.connect(self.do_auto_backup)
            self.auto_backup_timer.start(interval)
            self.log(f"自动备份定时器已启动，间隔：{getattr(self, 'auto_backup_interval', 60)}分钟", internal=True)
    
    def do_auto_backup(self):
        """执行自动备份"""
        try:
            if not self.server_path:
                return
            
            # 如果正在备份，则跳过
            if self.backup_worker and self.backup_worker.isRunning():
                self.log("自动备份跳过：上一次备份尚未完成", internal=True)
                return
            
            self.log("开始自动备份...", internal=True)
            
            # 执行备份
            self.backup_worker = BackupWorker(self.server_path, self.backup_dir, mode='backup')
            self.backup_worker.progress.connect(self.on_auto_backup_progress)
            self.backup_worker.finished.connect(self.on_auto_backup_finished)
            self.backup_worker.start()
            
        except Exception as e:
            self.log(f"[错误] 自动备份失败: {str(e)}", internal=True)
            write_error_log("自动备份失败", str(e), "do_auto_backup方法异常")
    
    def on_auto_backup_progress(self, value, message):
        """自动备份进度更新（仅记录到日志文件，不显示在UI上）"""
        self.log(f"[自动备份 {value}%] {message}", internal=True)
    
    def on_auto_backup_finished(self, success, message):
        """自动备份完成"""
        if success:
            self.log(f"自动备份完成: {message}", internal=True)
            # 备份完成后，清理旧的备份
            self.cleanup_old_backups()
        else:
            self.log(f"自动备份失败: {message}", internal=True)
        
        # 隐藏备份进度条
        if hasattr(self, 'show_progress'):
            self.show_progress(False)
        
        # 如果是从停止服务按钮触发的备份，备份完成后恢复按钮状态
        if getattr(self, '_backup_from_stop_button', False):
            self._backup_from_stop_button = False
            
            # 恢复关闭按钮
            if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'close_btn'):
                self.title_bar.close_btn.setEnabled(True)
            
            # 停止服务按钮保持禁用状态（因为服务端已经关闭了）
            if hasattr(self, 'main_page') and hasattr(self.main_page, 'stop_btn'):
                self.main_page.stop_btn.setText("停止服务")
                self.main_page.stop_btn.setEnabled(False)
            
            if success:
                self.log("自动备份完成，关闭按钮已恢复，停止服务按钮保持禁用")
            else:
                self.log("自动备份失败，关闭按钮已恢复，停止服务按钮保持禁用")
    
    def cleanup_old_backups(self):
        """清理旧的备份（保留最近的N个备份）"""
        try:
            max_count = getattr(self, 'auto_backup_max_count', 10)
            if not os.path.exists(self.backup_dir):
                return
            
            backups = [d for d in os.listdir(self.backup_dir)
                       if d.startswith("backup_") and os.path.isdir(os.path.join(self.backup_dir, d))]
            
            if len(backups) <= max_count:
                return
            
            # 按时间排序（从旧到新）
            backups.sort()
            
            # 删除最旧的备份
            backups_to_delete = backups[:len(backups) - max_count]
            import shutil
            for backup_name in backups_to_delete:
                backup_path = os.path.join(self.backup_dir, backup_name)
                try:
                    shutil.rmtree(backup_path)
                    self.log(f"已清理旧备份: {backup_name}", internal=True)
                except Exception as e:
                    self.log(f"[错误] 清理旧备份失败 {backup_name}: {str(e)}", internal=True)
            
        except Exception as e:
            self.log(f"[错误] 清理旧备份异常: {str(e)}", internal=True)
    
    def closeEvent(self, event):
        """程序关闭事件"""
        try:
            # 检查是否需要在关闭时自动备份
            if (getattr(self, 'auto_backup_enabled', False) and 
                getattr(self, 'auto_backup_mode', 'scheduled') == 'on_close' and
                not getattr(self, '_is_closing_after_backup', False)):
                
                # 只有服务端正在运行时才执行关闭时自动备份
                if self.is_server_running():
                    # 服务端正在运行，先停止服务端再备份
                    self.log("检测到关闭时自动备份已启用，正在停止服务端...")
                    self._is_closing_after_backup = True
                    self._close_after_backup = True
                    event.ignore()
                    
                    # 停止服务端（调用主页面的停止服务方法）
                    if hasattr(self, 'main_page') and self.main_page and hasattr(self.main_page, 'run_stop'):
                        self.main_page.run_stop()
                    
                    # 等待20秒后开始备份（确保服务端已停止）
                    QTimer.singleShot(20000, self._start_close_backup)
                    return
                else:
                    # 服务端未运行，直接关闭窗口，不执行备份
                    self.log("服务端未运行，跳过关闭时自动备份")
            
            # 停止自动备份定时器
            if self.auto_backup_timer:
                self.auto_backup_timer.stop()
            
            # 保存配置
            self.save_config()
            
            # 记录程序关闭日志
            RuntimeLogger.log("程序关闭")
            
            # 保存运行日志到文件
            RuntimeLogger.save_to_file()
                
        except Exception as e:
            pass
        
        event.accept()
    
    def _start_close_backup(self):
        """开始关闭时的自动备份"""
        try:
            if not hasattr(self, 'backup_dir') or not self.backup_dir:
                self.log("备份目录未配置，跳过自动备份")
                self._force_close()
                return
            
            # 启动备份
            self.backup_worker = BackupWorker(self.server_path, self.backup_dir, mode='backup')
            self.backup_worker.progress.connect(self._on_close_backup_progress)
            self.backup_worker.finished.connect(self._on_close_backup_finished)
            self.backup_worker.start()
            
        except Exception as e:
            self.log(f"关闭时自动备份失败: {str(e)}")
            self._force_close()
    
    def _on_close_backup_progress(self, value, message):
        """关闭时备份进度更新"""
        self.log(f"[备份中 {value}%] {message}")
    
    def _on_close_backup_finished(self, success, message):
        """关闭时备份完成"""
        if success:
            self.log(f"自动备份成功: {message}")
        else:
            self.log(f"自动备份失败: {message}")
        
        # 清理旧备份
        if hasattr(self, 'cleanup_old_backups'):
            self.cleanup_old_backups()
        
        # 强制关闭窗口
        QTimer.singleShot(500, self._force_close)
    
    def _force_close(self):
        """强制关闭窗口"""
        try:
            # 停止自动备份定时器
            if self.auto_backup_timer:
                self.auto_backup_timer.stop()
            
            # 保存配置
            self.save_config()
            
            # 记录程序关闭日志
            RuntimeLogger.log("程序关闭")
            
            # 保存运行日志到文件
            RuntimeLogger.save_to_file()
        except Exception as e:
            pass
        
        # 强制关闭
        QApplication.instance().quit()

    

    def load_config(self):
        """加载配置"""
        try:
            # 检查配置文件是否存在
            if not os.path.exists(self.config_path):
                self.log("配置文件不存在，将使用默认配置", internal=True)
                return
            
            # 读取配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载配置
            self.server_path = config.get('server_path', '')
            self.client_path = config.get('client_path', '')
            self.db_mode = config.get('db_mode', '')  # 数据库模式：mysql或sqlite
            
            # 加载自动备份设置
            self.auto_backup_enabled = config.get('auto_backup_enabled', False)
            self.auto_backup_interval = config.get('auto_backup_interval', 60)  # 分钟
            self.auto_backup_max_count = config.get('auto_backup_max_count', 10)  # 最大保留数量
            self.auto_backup_mode = config.get('auto_backup_mode', '')  # 备份模式：scheduled(定时)或on_close(关闭时)，默认不设置
            
            # 初始化数据库管理器（自动支持MySQL和SQLite）
            if self.server_path:
                self.db_manager = DatabaseManager(self.server_path)
                
            # 调试：确认配置已加载
            self.log(f"配置已加载: 服务端路径={self.server_path}", internal=True)
            if self.db_mode:
                self.log(f"数据库模式(配置文件): {self.db_mode}", internal=True)
            if self.auto_backup_enabled:
                self.log(f"自动备份已启用: 间隔={self.auto_backup_interval}分钟, 最大保留={self.auto_backup_max_count}个", internal=True)

        except Exception as e:
            self.server_path = ""
            self.client_path = ""
            self.db_mode = ""
            self.db_manager = None
            self.log(f"[错误] 加载配置失败: {str(e)}", internal=True)
            write_error_log("配置加载失败", str(e), "load_config方法异常")
    
    def _restore_config_from_backup(self):
        """从备份恢复配置文件（技术债务修复）"""
        try:
            backup_path = self.config_path + ".bak"
            if os.path.exists(backup_path):
                self.log("检测到配置备份，正在恢复...", internal=True)
                # 先将损坏的配置文件重命名为损坏文件
                corrupted_path = self.config_path + ".corrupted"
                if os.path.exists(self.config_path):
                    os.rename(self.config_path, corrupted_path)
                # 从备份恢复
                import shutil
                shutil.copy2(backup_path, self.config_path)
                self.log("配置已从备份恢复", internal=True)
                # 重新加载配置
                self.load_config()
            else:
                self.log("无配置备份，重置为默认配置", internal=True)
                # 重置为默认配置
                self.server_path = ""
                self.client_path = ""
                self.db_mode = ""
                self.db_manager = None
        except Exception as e:
            self.log(f"[错误] 从备份恢复配置失败: {str(e)}", internal=True)
            # 恢复失败，重置为默认配置
            self.server_path = ""
            self.client_path = ""
            self.db_mode = ""
            self.db_manager = None

    def save_config(self):
        """保存配置（同时创建登录器和GM工具两个配置文件）"""
        try:
            # 确保db_mode有默认值"mysql"
            if not getattr(self, 'db_mode', ''):
                self.db_mode = "mysql"
            
            config = {
                'server_path': self.server_path,
                'client_path': getattr(self, 'client_path', ''),
                'db_mode': self.db_mode,  # 数据库模式：MySQL或SQLite
                'auto_backup_enabled': getattr(self, 'auto_backup_enabled', False),
                'auto_backup_interval': getattr(self, 'auto_backup_interval', 60),
                'auto_backup_max_count': getattr(self, 'auto_backup_max_count', 10),
                'auto_backup_mode': getattr(self, 'auto_backup_mode', '')  # 备份模式：scheduled(定时)或on_close(关闭时)，默认不设置
            }

            # 写入登录器配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 同时创建GM工具的配置文件（module/config/config.lau）
            try:
                import os
                launcher_dir = os.path.dirname(self.config_path)
                gm_config_dir = os.path.join(launcher_dir, 'module', 'config')
                gm_config_file = os.path.join(gm_config_dir, 'config.lau')
                
                os.makedirs(gm_config_dir, exist_ok=True)
                
                # GM工具配置文件（包含GM工具需要的配置项）
                gm_config = {
                    'server_path': self.server_path,
                    'client_path': getattr(self, 'client_path', ''),
                    'db_mode': self.db_mode,
                    'pvf_path': ''
                }
                
                with open(gm_config_file, 'w', encoding='utf-8') as f:
                    json.dump(gm_config, f, ensure_ascii=False, indent=2)
            except Exception as gm_e:
                # GM配置文件创建失败不影响主流程
                pass
            
            # 调试：确认配置已保存
            if hasattr(self, 'log'):
                self.log(f"配置已保存到: {self.config_path}", internal=True)
                self.log(f"  服务端路径: {self.server_path}", internal=True)
                self.log(f"  客户端路径: {getattr(self, 'client_path', '')}", internal=True)
                if getattr(self, 'db_mode', ''):
                    self.log(f"  数据库模式: {self.db_mode}", internal=True)
                if getattr(self, 'auto_backup_enabled', False):
                    self.log(f"  自动备份: 启用, 间隔={getattr(self, 'auto_backup_interval', 60)}分钟, 最大保留={getattr(self, 'auto_backup_max_count', 10)}个", internal=True)

        except Exception as e:
            # 显示错误信息，便于排查
            if hasattr(self, 'log'):
                self.log(f"[错误] 保存配置失败: {str(e)}", internal=True)
            import traceback
            traceback.print_exc()
            write_error_log("配置保存失败", str(e), "save_config方法异常")

    

    def log(self, message, internal=False):
        """共享日志方法，所有页面共用（性能优化版 + 内部日志过滤 + 路径统一反斜杠）
        
        只记录用户行为，不记录程序自主行为。
        程序自主行为（初始化、配置加载、状态检查等）仅记录到日志文件，不显示在UI上。
        
        Args:
            message: 日志消息
            internal: 是否为内部日志（True时不显示在UI上，仅记录到文件）
        """
        # 自动将路径中的正斜杠转换为反斜杠（Windows标准格式）
        message = normalize_path(message)
        
        # 程序自主行为关键词（不显示在UI上，仅记录到文件）
        # 包括：初始化、配置加载、状态检查、内部调试、性能监控等
        internal_keywords = [
            # 初始化与配置
            "初始化", "程序启动", "程序关闭", "加载配置", "保存配置", "配置已加载",
            "配置已保存", "服务端路径", "客户端路径", "数据库模式", "版本信息",
            # 内部状态检查
            "检查", "检测", "状态", "缓存", "性能", "耗时",
            # 调试与错误详情
            "[调试]", "[警告]", "[错误详情]", "traceback",
            # 进程与端口（内部信息）
            "端口", "进程ID", "工作目录", "控制程序", "[服务端]", 
            "等待服务端启动", "MySQL配置", "MySQL端口", "服务端端口",
            "DNF90Control进程", "检测到服务端就绪信号", "读取配置失败",
            "已被占用", "进程已退出", "退出码", "服务端输出",
            # 资源加载
            "已加载", "加载失败", "加载成功",
            # 内部操作记录
            "自动", "系统", "内部"
        ]
        
        # 用户行为关键词（强制显示在UI上，即使包含内部关键词）
        user_action_keywords = [
            "开始", "启动", "停止", "安装", "备份", "恢复", "迁移",
            "登录", "注册", "点击", "用户", "操作",
            "成功", "失败", "完成", "错误", "警告",
            "正在", "准备"
        ]
        
        # 自动判断是否为内部日志
        is_internal = internal
        
        # 如果消息包含用户行为关键词，则强制显示（除非显式指定internal=True）
        if not internal:
            has_user_action = any(keyword in message for keyword in user_action_keywords)
            if has_user_action:
                is_internal = False
            else:
                # 如果不包含用户行为关键词，检查是否包含内部关键词
                has_internal = any(keyword in message for keyword in internal_keywords)
                if has_internal:
                    is_internal = True
        
        # 内部日志仅记录到运行日志文件，不显示在UI上
        if is_internal:
            RuntimeLogger.log(message)
            return
        
        # 判断是否为用户点击操作（包含"点击"关键词）
        is_click_action = "点击" in message
        
        if is_click_action and not internal:
            # 用户点击操作记录到状态栏，不显示在日志区
            self.update_status_bar(message)
            # 同时记录到运行日志文件
            RuntimeLogger.log(message)
            return
        
        # 程序级操作（如"游戏启动成功"、"服务启动成功"）显示在日志区
        # 使用高效日志系统，减少UI更新频率
        EfficientLogger.log(message)
        
        # 同时记录到运行日志记录器（程序关闭时写入文件）
        RuntimeLogger.log(message)
        
        # 更新所有页面的操作历史（使用批量更新，减少重绘）
        if hasattr(self, 'main_page') and self.main_page and hasattr(self.main_page, 'status_text'):
            self.main_page.status_text.setPlainText("\n".join(EfficientLogger.get_all_logs()))
            scrollbar = self.main_page.status_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        if hasattr(self, 'login_page') and self.login_page and hasattr(self.login_page, 'status_text'):
            self.login_page.status_text.setPlainText("\n".join(EfficientLogger.get_all_logs()))
            scrollbar = self.login_page.status_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        if hasattr(self, 'path_setup_page') and self.path_setup_page and hasattr(self.path_setup_page, 'history_text'):
            self.path_setup_page.history_text.setPlainText("\n".join(EfficientLogger.get_all_logs()))
            scrollbar = self.path_setup_page.history_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    

    def init_ui(self):

        self.setWindowTitle("launcher")

        self.setFixedSize(420, 560)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        # 圆角窗口：透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)

        

        self.setStyleSheet("""

            QMainWindow { background-color: transparent; }

            #titleBar { background-color: #1a1a1a; border-bottom: 1px solid #333333; border-top-left-radius: 6px; border-top-right-radius: 6px; }

            #navBtn { background-color: transparent; border: none; }

            #navBtn:hover { background-color: #333333; }

            #closeBtn { background-color: transparent; border: none; color: #ffffff; }

            #closeBtn:hover { background-color: #e81123; }

            #minimizeBtn { background-color: transparent; border: none; color: #ffffff; }

            #minimizeBtn:hover { background-color: #3a3a3a; }

            QLabel { color: #ffffff; font-family: "Noto Sans SC", "Microsoft YaHei"; }

            QPushButton {

                background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;

                border-radius: 4px; padding: 10px 16px; font-weight: bold; font-size: 14px;

                font-family: "Noto Sans SC", "Microsoft YaHei";

            }

            QPushButton:pressed { background-color: #1a1a1a; border-color: #4a90d9; color: #4a90d9; }

            QPushButton:disabled { background-color: #1a1a1a; border-color: #2a2a2a; color: #555555; }

            #primaryBtn { background-color: #1a1a2e; border-color: #4a90d9; color: #ffffff; }

            #primaryBtn:pressed { background-color: #0a0a1e; border-color: #6ab0ff; color: #6ab0ff; }

            #primaryBtn:disabled { background-color: #0a0a1e; border-color: #1a1a2e; color: #555555; }

            QLineEdit {

                background-color: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px;

                padding: 8px 12px; color: #ffffff; font-size: 12px;

                font-family: "Noto Sans SC", "Microsoft YaHei";

            }

            QLineEdit:focus { border-color: #4a90d9; }

            QTextEdit {

                background-color: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px;

                padding: 8px; color: #88ff88; font-family: "Consolas", "Courier New"; font-size: 11px;

            }

            #scrollLabel { color: #666666; font-size: 11px; font-family: "Noto Sans SC", "Microsoft YaHei"; }

            #glowBar { background-color: #111111; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }

            QStackedWidget { background-color: transparent; }

        """)

        

        central = QWidget()

        # 圆角容器（使用objectName限定样式，不影响子组件）
        central.setObjectName("mainRoundedContainer")
        central.setStyleSheet("""
            #mainRoundedContainer {
                background-color: #202020;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
        """)

        self.setCentralWidget(central)

        

        main_layout = QVBoxLayout(central)

        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.setSpacing(0)

        

        self.title_bar = TitleBar(self)

        main_layout.addWidget(self.title_bar)

        

        # 路径显示

        self.path_label = QLabel()

        self.path_label.setStyleSheet("color: #a0a0a0; font-size: 11px; padding: 10px 20px 6px 20px;")

        self.path_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.path_label.setWordWrap(True)

        self.update_path_label()

        main_layout.addWidget(self.path_label)

        

        # 页面堆叠

        self.stacked_widget = QStackedWidget()

        self.path_setup_page = PathSetupPage(self)

        self.main_page = MainMenuPage(self)

        self.login_page = LoginPage(self)

        self.install_patch_page = InstallPatchPage(self)

        self.db_select_page = DatabaseSelectPage(self)

        self.stacked_widget.addWidget(self.path_setup_page)

        self.stacked_widget.addWidget(self.main_page)

        self.stacked_widget.addWidget(self.login_page)

        self.stacked_widget.addWidget(self.install_patch_page)

        self.stacked_widget.addWidget(self.db_select_page)

        main_layout.addWidget(self.stacked_widget, 1)

        

        # 初始页面

        if self.server_path:

            self.stacked_widget.setCurrentWidget(self.main_page)

            self.main_page.log("系统就绪，等待操作...")

            if self.title_bar:

                self.title_bar.set_back_button_visible(True)

            # 启动器打开时检查服务端状态（简单稳定版，直接在UI线程检测）
            QTimer.singleShot(500, self.check_server_on_startup)

        else:

            self.stacked_widget.setCurrentWidget(self.path_setup_page)

            if self.title_bar:

                self.title_bar.set_back_button_visible(False)

            # 填入已保存的客户端路径

            if hasattr(self, 'client_path') and self.client_path:

                self.path_setup_page.client_path_input.setText(self.client_path)

        

        # 底部光效条

        glow_container = QWidget()

        glow_container.setStyleSheet("background-color: transparent;")

        glow_layout = QHBoxLayout(glow_container)

        glow_layout.setContentsMargins(20, 0, 20, 0)

        glow_bar = QFrame()

        glow_bar.setObjectName("glowBar")

        glow_bar.setFixedHeight(1)

        glow_layout.addWidget(glow_bar)

        main_layout.addWidget(glow_container)

        

        # 状态栏（记录用户操作，替换原版权信息区域）
        status_container = QWidget()
        status_container.setFixedHeight(30)
        status_container.setStyleSheet("background-color: transparent;")
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(20, 2, 20, 2)
        status_layout.setSpacing(8)

        # 操作记录文字（左边）
        self.status_bar_label = QLabel("就绪")
        self.status_bar_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_bar_label.setStyleSheet("color: #aaaaaa; font-size: 12px; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
        status_layout.addWidget(self.status_bar_label)

        status_layout.addStretch()

        # 版本号_发行状态（右边）
        version_label = QLabel(APP_VERSION + "_release")
        version_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        version_label.setStyleSheet("color: #999999; font-size: 12px; font-family: 'Noto Sans SC', 'Microsoft YaHei';")
        status_layout.addWidget(version_label)

        main_layout.addWidget(status_container)

    

    def update_status_bar(self, message):
        """更新状态栏文字（记录用户操作）"""
        if hasattr(self, 'status_bar_label') and self.status_bar_label:
            # 只去掉"点击"字样，保留其他字样
            display_message = message.replace("点击", "").strip()
            self.status_bar_label.setText(display_message)
    
    def show_progress(self, visible=True):
        """显示/隐藏进度条"""
        if hasattr(self, 'status_progress') and self.status_progress:
            self.status_progress.setVisible(visible)
            if not visible:
                self.status_progress.setValue(0)
    
    def set_progress(self, value, message=None):
        """设置进度条值"""
        if hasattr(self, 'status_progress') and self.status_progress:
            self.status_progress.setValue(int(value))
            if message:
                self.status_progress.setFormat(f"{message} {int(value)}%")
            else:
                self.status_progress.setFormat("%p%")

    def update_path_label(self):

        if self.server_path:
            # 转换为Windows标准路径格式（反斜杠）
            win_path = self.server_path.replace('/', '\\')
            self.path_label.setText(f"当前服务端: {win_path}")

        else:

            self.path_label.setText("请先设置服务端和客户端路径")

    

    def switch_to_main(self):

        self.update_path_label()

        self.stacked_widget.setCurrentWidget(self.main_page)

        self.main_page.log("系统就绪，等待操作...")

        # 显示返回按钮（除路径页面外都显示）

        if self.title_bar:

            self.title_bar.set_back_button_visible(True)


    def switch_to_login(self):
        """切换到登录页面"""
        self.update_path_label()
        self.stacked_widget.setCurrentWidget(self.login_page)
        if self.title_bar:
            self.title_bar.set_back_button_visible(True)
        self.main_page.log("进入账号登录页面...")
        # 更新当前账号信息
        if hasattr(self, 'current_user') and self.current_user:
            self.login_page.update_current_account(self.current_user)
        else:
            self.login_page.update_current_account(None)


    def check_server_bin_and_fix_config(self):
        """检测服务端主体程序修改时间（测试版：适配Python版服务端）"""
        try:
            if not self.server_path:
                return
            
            # 测试版：检测Python版服务端 dnf90_server.exe
            server_exe = os.path.join(self.server_path, "dnf90_server.exe")
            
            if not os.path.exists(server_exe):
                return
            
            # 获取修改时间
            mtime = os.path.getmtime(server_exe)
            
            # 计算距今时间（秒）
            time_diff = time.time() - mtime
            one_day = 24 * 60 * 60
            
            if time_diff >= one_day:
                # 修改时间超过1天，不需要检测
                return
            
            self.log("检测到服务端程序近期更新，跳过配置自动检测（测试版）")
            
        except Exception as e:
            self.log("检测服务端程序时出错: {}".format(e))
    
    def check_server_on_startup(self):
        """启动器打开时检查服务端状态（简单稳定版）
        
        优化点：
        1. 不使用后台线程，直接在UI线程检测（检测很快，不会阻塞UI）
        2. 不检测服务端主体程序修改时间，不自动修复配置
        3. 只检测服务端进程是否在运行，然后更新按钮状态
        """
        try:
            if not self.server_path:
                return
            
            # 直接检测服务端进程是否在运行
            is_running = self.is_server_running()
            
            # 更新按钮状态
            if hasattr(self, 'main_page') and self.main_page:
                if is_running:
                    self.main_page.login_btn.setText("账号登录")
                    self.main_page.stop_btn.setEnabled(True)
                    self.log("服务端已在运行", internal=True)
                else:
                    self.main_page.login_btn.setText("启动服务")
                    self.main_page.stop_btn.setEnabled(False)
                    self.log("服务端未启动，点击'启动服务'按钮启动", internal=True)
                    
        except Exception as e:
            # 检测失败不影响程序运行
            self.log(f"服务端状态检测失败: {str(e)}", internal=True)
    
    def on_server_check_finished(self, is_running):
        """服务端状态检查完成回调"""
        if is_running:
            self.log("服务端已在运行", internal=True)
            if hasattr(self, 'main_page') and self.main_page:
                self.main_page.login_btn.setText("账号登录")
                self.main_page.stop_btn.setEnabled(True)
        else:
            self.log("服务端未启动，点击'启动服务'按钮启动", internal=True)
            if hasattr(self, 'main_page') and self.main_page:
                self.main_page.login_btn.setText("启动服务")
                self.main_page.stop_btn.setEnabled(False)

    def _check_port_open(self, host, port, timeout=2):
        """检查端口是否开放（通用工具函数）"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
                return result == 0
        except:
            return False

    def check_mysql_ready(self):
        """检查服务端是否就绪（先检查进程，再检查端口7001，兼容MySQL和SQLite）"""
        try:
            # 首先检查服务端进程是否在运行
            if not self.is_server_running():
                # 进程不在运行，即使端口开放也返回False
                return False
            
            # 进程在运行，检查服务端端口7001（DNF90服务端频道监听端口）
            if self._check_port_open("127.0.0.1", 7001, timeout=2):
                return True
            
            # 如果服务端端口未开放，再检查数据库（兼容旧逻辑）
            if not self.db_manager and self.server_path:
                self.db_manager = DatabaseManager(self.server_path)
            
            if self.db_manager:
                return self.db_manager.check_ready()
            
            return False
        except:
            return False

    def validate_server_path(self, server_path):
        """验证服务端路径是否完整有效（测试版：适配Python版服务端）"""
        if not server_path or not os.path.exists(server_path):
            return False, "服务端路径不存在"
        
        # 测试版：检查Python版服务端的必要文件
        required_files = [
            "dnf90_server.exe",
            "instance.json",
        ]
        
        missing_files = []
        for rel_path in required_files:
            full_path = os.path.join(server_path, rel_path)
            if not os.path.exists(full_path):
                missing_files.append(rel_path)
        
        if missing_files:
            return False, "服务端目录缺少必要文件: {}".format(", ".join(missing_files))
        
        return True, "路径验证通过"

    def is_admin(self):
        """检查是否以管理员身份运行"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

    def start_server_and_wait(self, timeout=60):
        """启动服务端并等待 MySQL 就绪（测试版：适配Python版服务端）"""
        try:
            # 测试版：直接启动Python版服务端 dnf90_server.exe
            server_exe = os.path.join(self.server_path, "dnf90_server.exe")
            config_file = os.path.join(self.server_path, "instance.json")
            
            # 验证服务端文件存在
            if not os.path.exists(server_exe):
                self.log("错误: 未找到 dnf90_server.exe")
                self.log("  路径: {}".format(server_exe))
                return False
            
            # 验证instance.json存在并读取端口配置
            if not os.path.exists(config_file):
                self.log("错误: 未找到 instance.json 配置文件")
                return False
            
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                db_config = config.get("database", {})
                mysql_host = db_config.get("host", "127.0.0.1")
                mysql_port = db_config.get("port", 13306)
                self.log("MySQL配置: {}:{}".format(mysql_host, mysql_port))
            except Exception as e:
                self.log("警告: 读取配置失败 - {}".format(str(e)))
                mysql_host = "127.0.0.1"
                mysql_port = 13306
            
            # 检查管理员权限
            if not self.is_admin():
                self.log("警告: 未以管理员身份运行，可能导致启动失败")
            
            # 检查端口是否已被占用
            if self._check_port_open(mysql_host, mysql_port, timeout=1):
                self.log("提示: 端口{}已被占用，可能MySQL已在运行".format(mysql_port))
            
            # 设置环境变量并启动服务端
            env = os.environ.copy()
            env["DNF90_PROJECT_ROOT"] = self.server_path
            env["DNF_RESIDENT_CHANNEL_ID"] = "19"
            
            self.log("正在启动服务端...")
            self.log("  工作目录: {}".format(self.server_path))
            self.log("  服务端程序: {}".format(server_exe))
            self.log("  配置文件: {}".format(config_file))
            
            # 启动进程（测试版：直接启动dnf90_server.exe，不捕获输出，让它在独立窗口运行）
            try:
                proc = subprocess.Popen(
                    [server_exe, "-c", config_file],
                    cwd=self.server_path,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
                )
                self.log("  进程ID: {}".format(proc.pid))
            except Exception as e:
                self.log("错误: 启动进程失败 - {}".format(str(e)))
                import traceback
                write_error_log("服务端启动失败", str(e), traceback.format_exc())
                return False
            
            # 等待服务端就绪
            start_time = time.time()
            server_ready = False
            
            while time.time() - start_time < timeout:
                # 检查服务端进程是否还在运行
                if proc.poll() is not None:
                    self.log("错误: 服务端进程已退出（退出码: {}）".format(proc.returncode))
                    return False
                
                # 检查服务端端口（7001）是否开放
                if self._check_port_open("127.0.0.1", 7001, timeout=1):
                    self.log("服务端端口7001已开放")
                    server_ready = True
                    break
                
                # 检查MySQL端口
                if self._check_port_open(mysql_host, mysql_port, timeout=1):
                    self.log("MySQL端口已开放")
                
                # 等待1秒后重试
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    self.log("等待服务端启动... ({}秒)".format(elapsed))
                time.sleep(1)
            
            if server_ready:
                self.log("服务端启动成功！")
                return True
            else:
                self.log("警告: 服务端启动超时（{}秒），但进程仍在运行".format(timeout))
                return True  # 进程还在运行，认为启动成功

        except Exception as e:
            import traceback
            self.log("错误: 启动服务端异常 - {}".format(str(e)))
            write_error_log("服务端启动异常", str(e), traceback.format_exc())
            return False

    def verify_account(self, username, password):
        """验证账号（自动支持MySQL和SQLite）"""
        try:
            # 确保数据库管理器已初始化
            if not self.db_manager and self.server_path:
                self.db_manager = DatabaseManager(self.server_path)
            
            if not self.db_manager:
                return False, "未配置服务端路径"
            
            return self.db_manager.verify_account(username, password)
            
        except Exception as e:
            import traceback
            error_msg = "验证失败: {}".format(str(e))
            write_error_log("登录验证异常", str(e), traceback.format_exc())
            return False, error_msg


    def register_account(self, username, password):
        """注册账号（自动支持MySQL和SQLite）"""
        try:
            # 确保数据库管理器已初始化
            if not self.db_manager and self.server_path:
                self.db_manager = DatabaseManager(self.server_path)
            
            if not self.db_manager:
                return False, "未配置服务端路径"
            
            return self.db_manager.register_account(username, password)
            
        except Exception as e:
            import traceback
            error_msg = "注册失败: {}".format(str(e))
            write_error_log("账号注册异常", str(e), traceback.format_exc())
            return False, error_msg


    def launch_game(self, username, password):
        """启动游戏（使用后台线程，不阻塞UI）"""
        self.current_user = username
        self.current_password = password
        self.main_page.log("正在启动游戏（账号: {}）...".format(username))

        # 切换回主菜单
        self.switch_to_main()

        # 更新主页面当前账号信息
        self.main_page.update_current_account(username)

        # 使用后台线程启动游戏
        self.launch_worker = LaunchGameWorker(self.server_path, self.client_path, username, password)
        self.launch_worker.log_message.connect(self.main_page.log)
        self.launch_worker.finished.connect(self.on_launch_finished)
        self.launch_worker.start()

    def on_launch_finished(self, success, message):
        """启动游戏完成回调"""
        if success:
            self.main_page.log("启动完成: {}".format(message))
        else:
            self.main_page.log("启动失败: {}".format(message))
            show_frameless_error(self, "错误", "启动游戏失败:\n{}".format(message))


    def show_migrate_dialog(self):
        """显示存档管理独立窗口"""
        self.show_archive_manager()


    def do_backup(self):
        """数据保护"""
        if self.is_server_running():
            if not show_frameless_confirm(
                self, "警告",
                "检测到服务端正在运行！\n备份正在运行的数据库可能导致数据不一致。\n\n建议先停止服务端再进行备份。\n\n是否继续备份？"
            ):
                return

        self.main_page.migrate_btn.setEnabled(False)
        self.main_page.log("开始数据保护（备份）...")

        self.backup_worker = BackupWorker(self.server_path, self.backup_dir, mode='backup')
        self.backup_worker.progress.connect(self.on_backup_progress)
        self.backup_worker.finished.connect(self.on_backup_finished)
        self.backup_worker.start()


    def do_restore(self):
        """数据恢复（恢复最新备份）"""
        if self.is_server_running():
            show_frameless_warning(
                self, "错误",
                "检测到服务端正在运行！\n恢复数据前必须先停止服务端。\n\n请先点击'停止服务'按钮，然后再进行数据恢复。"
            )
            return

        if not show_frameless_confirm(
            self, "确认恢复",
            "数据恢复将覆盖当前所有数据！\n\n此操作不可撤销，确定要继续吗？"
        ):
            return

        self.main_page.migrate_btn.setEnabled(False)
        self.main_page.log("开始数据恢复...")

        self.backup_worker = BackupWorker(self.server_path, self.backup_dir, mode='restore')
        self.backup_worker.progress.connect(self.on_backup_progress)
        self.backup_worker.finished.connect(self.on_backup_finished)
        self.backup_worker.start()
    
    def do_restore_specific(self, backup_name):
        """数据恢复（恢复指定备份）"""
        if self.is_server_running():
            show_frameless_warning(
                self, "错误",
                "检测到服务端正在运行！\n恢复数据前必须先停止服务端。\n\n请先点击'停止服务'按钮，然后再进行数据恢复。"
            )
            return

        self.main_page.migrate_btn.setEnabled(False)
        self.main_page.log(f"开始恢复指定备份: {backup_name}...")

        self.backup_worker = BackupWorker(self.server_path, self.backup_dir, mode='restore', specific_backup=backup_name)
        self.backup_worker.progress.connect(self.on_backup_progress)
        self.backup_worker.finished.connect(self.on_backup_finished)
        self.backup_worker.start()


    def on_backup_progress(self, value, message):
        """备份进度更新（仅在日志区显示）"""
        self.main_page.log("[{}%] {}".format(value, message))


    def on_backup_finished(self, success, message):
        """备份完成（仅在日志区显示）"""
        self.main_page.migrate_btn.setEnabled(True)

        if success:
            self.main_page.log("成功: {}".format(message))
        else:
            self.main_page.log("失败: {}".format(message))


    def is_server_running(self):
        """检查服务端是否运行（性能优化版：减少重试和超时，避免启动卡顿）
        
        优化点：
        1. 使用CSV格式输出，避免中文编码问题
        2. 减少重试次数为1次（启动时快速检测，后台线程可重试）
        3. 添加短时间缓存，避免频繁调用tasklist
        4. 减少超时时间为2秒
        """
        import time
        
        # 缓存机制：2秒内的重复检测使用缓存结果
        current_time = time.time()
        if hasattr(self, '_server_running_cache') and hasattr(self, '_server_running_cache_time'):
            if current_time - self._server_running_cache_time < 2:
                return self._server_running_cache
        
        try:
            # 需要检查的进程列表（测试版：适配Python版服务端）
            processes_to_check = [
                "dnf90_server.exe",
                "mysqld.exe"
            ]
            
            # 性能优化：启动时只检测1次，避免卡顿
            # 后台线程或用户主动触发时可重试
            max_retries = 1
            for attempt in range(max_retries):
                try:
                    # 使用CSV格式输出，避免中文编码问题
                    # /FO CSV 输出CSV格式，/NH 不显示表头
                    # creationflags=CREATE_NO_WINDOW 避免控制台窗口闪现
                    result = subprocess.run(
                        ["tasklist", "/FO", "CSV", "/NH"],
                        capture_output=True, 
                        timeout=2,  # 减少超时时间为2秒，避免卡顿
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # 处理编码：优先尝试UTF-8，失败则尝试GBK（中文Windows默认编码）
                    try:
                        output = result.stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            output = result.stdout.decode('gbk')
                        except UnicodeDecodeError:
                            output = result.stdout.decode('latin-1')
                    
                    # 检查是否有目标进程在运行
                    for proc_name in processes_to_check:
                        # CSV格式中进程名会被引号包围，如"DNF90Server.exe"
                        if f'"{proc_name}"' in output or proc_name in output:
                            self._server_running_cache = True
                            self._server_running_cache_time = current_time
                            return True
                    
                    # 第一次检测未找到，短暂等待后重试（排除进程启动中的情况）
                    if attempt < max_retries - 1:
                        time.sleep(0.3)
                        continue
                    
                    # 所有重试都未找到进程
                    self._server_running_cache = False
                    self._server_running_cache_time = current_time
                    return False
                    
                except subprocess.TimeoutExpired:
                    # tasklist超时，重试
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    # 超时次数过多，返回False
                    self._server_running_cache = False
                    self._server_running_cache_time = current_time
                    return False
                    
                except Exception as e:
                    # 其他异常，记录错误并重试
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    write_error_log("进程检测失败", str(e), "is_server_running方法异常")
                    self._server_running_cache = False
                    self._server_running_cache_time = current_time
                    return False
            
            self._server_running_cache = False
            self._server_running_cache_time = current_time
            return False
            
        except Exception as e:
            write_error_log("进程检测异常", str(e), "is_server_running外层异常")
            self._server_running_cache = False
            self._server_running_cache_time = current_time
            return False


    def switch_to_install_patch(self):

        self.stacked_widget.setCurrentWidget(self.install_patch_page)

        if self.title_bar:

            self.title_bar.set_back_button_visible(True)


    def switch_to_db_select(self):

        self.stacked_widget.setCurrentWidget(self.db_select_page)

        if self.title_bar:

            self.title_bar.set_back_button_visible(True)


    def start_install_patch(self, server_dir, client_dir):

        """启动安装客户端补丁"""

        self.switch_to_install_patch()

        # 清空日志
        self.install_patch_page.log_text.clear()
        self.install_patch_page.finish_btn.setVisible(False)
        self.install_patch_page.status_label.setStyleSheet("color: #88ff88; font-size: 12px;")

        self.install_patch_thread = InstallPatchThread(server_dir, client_dir)

        self.install_patch_thread.progress.connect(self.install_patch_page.update_progress)

        self.install_patch_thread.status.connect(self.install_patch_page.update_status)

        self.install_patch_thread.log.connect(self.install_patch_page.append_log)

        self.install_patch_thread.need_db_select.connect(self.switch_to_db_select)

        self.install_patch_thread.finished.connect(self.install_patch_page.install_finished)

        self.install_patch_thread.start()

    

    def switch_to_path_setup(self, clear_input=True):

        """

        Args:

            clear_input: 是否清空服务端路径输入（点击重设按钮时为True，返回按钮时为False）

        """

        if clear_input:
            # 点击重设按钮时清空路径
            self.server_path = ""
            self.save_config()
            self.update_path_label()
            self.path_setup_page.path_input.clear()
        else:
            # 点击返回按钮时保留路径，填入输入框
            if self.server_path:
                self.path_setup_page.path_input.setText(self.server_path)

        # 瀹埛绔矾寰勬案涔呬繚鐣欙紝鍙湪鐐瑰嚮娴忚鎸夐挳鏃舵墠浼氭敼鍙?

        if hasattr(self, 'client_path') and self.client_path:

            self.path_setup_page.client_path_input.setText(self.client_path)

        self.stacked_widget.setCurrentWidget(self.path_setup_page)

        # 显示返回按钮

        if self.title_bar:

            self.title_bar.set_back_button_visible(True)

    

def get_resource_path(relative_path):
    """获取资源文件路径（兼容打包后的exe和开发模式）
    
    Args:
        relative_path: 相对路径
        
    Returns:
        资源文件的绝对路径
    """
    try:
        # PyInstaller打包后，资源文件解压到临时目录 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # 开发模式，使用脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def get_app_dir():
    """获取程序所在目录（用于保存配置文件等）
    
    Returns:
        程序所在目录的绝对路径（使用反斜杠）
    """
    if getattr(sys, 'frozen', False):
        # 打包后的exe模式
        path = os.path.dirname(sys.executable)
    else:
        # 开发模式
        path = os.path.dirname(os.path.abspath(__file__))
    
    # 统一为反斜杠
    return path.replace('/', '\\')


def normalize_path(path):
    """将路径统一为Windows反斜杠格式
    
    Args:
        path: 输入路径
        
    Returns:
        统一为反斜杠的路径
    """
    if not path:
        return path
    return path.replace('/', '\\')


def main():
    # 性能监控：记录启动时间
    import time
    startup_start = time.time()

    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # 设置应用名称
        app.setApplicationName("DNF轮回启动器")
        app.setOrganizationName("ereshkigal996")
        
        # 设置应用图标（优先使用打包的资源，其次从exe目录加载）
        try:
            icon_path = get_resource_path("DFO.ico")
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
            else:
                # 从exe所在目录加载
                app_dir = get_app_dir()
                icon_path = os.path.join(app_dir, "DFO.ico")
                if os.path.exists(icon_path):
                    app.setWindowIcon(QIcon(icon_path))
        except:
            pass
        
        font = QFont("Noto Sans SC", 9)
        app.setFont(font)

        window = LauncherWindow()
        
        # 设置高效日志系统的UI组件
        if hasattr(window, 'main_page') and window.main_page and hasattr(window.main_page, 'status_text'):
            EfficientLogger.set_ui_widget(window.main_page.status_text)
        
        window.show()
        
        # 性能监控：输出启动耗时
        startup_time = (time.time() - startup_start) * 1000
        print(f"[性能] 程序启动耗时: {startup_time:.1f}ms")
        
        exit_code = app.exec_()
        
        sys.exit(exit_code)

    except Exception as e:
        try:
            show_frameless_error(None, "程序错误", f"程序运行出错:\n{e}")
        except:
            pass
        sys.exit(1)



class InstallPatchPage(QWidget):
    """安装客户端补丁进度页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(12)

        title = QLabel("安装客户端补丁")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(28)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #4a90d9;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("准备安装...")
        self.status_label.setStyleSheet("color: #88ff88; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # 日志输出
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d0d0d;
                color: #aaaaaa;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                font-size: 10px;
                font-family: Consolas, monospace;
            }
        """)
        layout.addWidget(self.log_text, 1)

        layout.addStretch()

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # 返回按钮
        back_btn = QPushButton("返回")
        back_btn.setMinimumHeight(38)
        back_btn.clicked.connect(self.main_window.switch_to_path_setup)
        btn_layout.addWidget(back_btn)

        # 完成按钮（初始隐藏）
        self.finish_btn = QPushButton("完成")
        self.finish_btn.setMinimumHeight(38)
        self.finish_btn.setVisible(False)
        self.finish_btn.clicked.connect(self.main_window.switch_to_main)
        btn_layout.addWidget(self.finish_btn)

        layout.addLayout(btn_layout)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, text):
        self.status_label.setText(text)

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def install_finished(self, success, message):
        if success:
            self.status_label.setText("安装完成！")
            self.append_log("\n[完成] " + message)
            self.finish_btn.setText("完成")
        else:
            self.status_label.setText("安装失败：" + message)
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 12px;")
            self.append_log("\n[错误] " + message)
            self.finish_btn.setText("返回")
            self.finish_btn.clicked.disconnect()
            self.finish_btn.clicked.connect(self.main_window.switch_to_path_setup)
        self.finish_btn.setVisible(True)


class DatabaseSelectPage(QWidget):
    """数据库选择页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = QLabel("选择数据库模式")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("请选择服务端使用的数据库类型")
        desc.setStyleSheet("color: #888888; font-size: 12px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(15)

        # MySQL 按钮
        mysql_btn = QPushButton("MySQL - 便携数据库")
        mysql_btn.setMinimumHeight(50)
        mysql_btn.clicked.connect(lambda: self.select_database("mysql"))
        layout.addWidget(mysql_btn)

        # SQLite 按钮
        sqlite_btn = QPushButton("SQLite - 本地数据库")
        sqlite_btn.setMinimumHeight(50)
        sqlite_btn.clicked.connect(lambda: self.select_database("sqlite"))
        layout.addWidget(sqlite_btn)

        layout.addStretch()

    def select_database(self, mode):
        """选择数据库模式并继续安装"""
        # 保存数据库模式到安装线程
        self.main_window.install_patch_thread.database_mode = mode
        
        # 保存数据库模式到主窗口配置
        self.main_window.db_mode = mode
        
        # 立即保存配置到文件
        self.main_window.save_config()
        
        mode_text = "MySQL" if mode == "mysql" else "SQLite"
        self.main_window.log(f"已选择数据库模式: {mode_text}")
        self.main_window.log(f"数据库模式已保存到配置文件")
        
        # 切换回安装页面
        self.main_window.switch_to_install_patch()
        
        # 延迟继续安装
        QTimer.singleShot(100, self.main_window.install_patch_thread.continue_after_db_select)


class InstallPatchThread(QThread):
    """安装客户端补丁线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    need_db_select = pyqtSignal()
    finished = pyqtSignal(bool, str)

    def __init__(self, server_dir, client_dir):
        super().__init__()
        self.server_dir = server_dir
        self.client_dir = client_dir
        self.database_mode = None
        self._wait_for_db = False

    def run(self):
        try:
            import shutil
            import subprocess

            # 步骤1：检测进程
            self.progress.emit(5)
            self.status.emit("正在检测游戏进程...")
            self.log.emit("检测 DNF.exe 进程...")

            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq DNF.exe'],
                                  capture_output=True, text=True)
            if 'DNF.exe' in result.stdout:
                self.finished.emit(False, "请先退出 DNF.exe 再安装补丁")
                return

            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq NoPack.exe'],
                                  capture_output=True, text=True)
            if 'NoPack.exe' in result.stdout:
                self.finished.emit(False, "请先退出 NoPack.exe 再安装补丁")
                return

            self.log.emit("进程检测通过")

            # 步骤2：检查发布包完整性
            self.progress.emit(10)
            self.status.emit("正在检查发布包完整性...")
            self.log.emit("检查发布包文件...")

            required_files = [
                r"client-patch\bin\90CN.dll",
                r"client-patch\bin\DNF.exe",
                r"client-patch\bin\ijl15.dll",
                r"client-patch\bin\ijl15_real.dll",
                r"runtime\data\dnf\Script.pvf",
                r"client-lua\bin\90CNLua.dll",
                r"client-lua\bin\lua\init.lua",
                r"client-lua\bin\lua\ai\init.lua",
                r"ImagePacks2\sprite_worldmap.NPK",
                r"ImagePacks2\sprite_worldmap_selectdungeonslot.NPK",
                r"ImagePacks2\sprite_interface2_raid_luke_reward.NPK",
                r"ImagePacks2\sprite_interface2_raid_luke_luke_card_system.NPK",
                r"ImagePacks2\sprite_interface_newstyle_windows_party_raid_areaimg.NPK",
            ]

            for rel_path in required_files:
                full_path = os.path.join(self.server_dir, rel_path)
                if not os.path.exists(full_path):
                    self.finished.emit(False, "发布包缺少文件: " + rel_path)
                    return

            self.log.emit("发布包完整性检查通过")

            # 步骤3：复制客户端EXE和PVF
            self.progress.emit(20)
            self.status.emit("正在复制客户端文件...")
            self.log.emit("复制 DNF.exe...")
            shutil.copy2(os.path.join(self.server_dir, r"client-patch\bin\DNF.exe"),
                        os.path.join(self.client_dir, "DNF.exe"))

            self.log.emit("复制 Script.pvf...")
            shutil.copy2(os.path.join(self.server_dir, r"runtime\data\dnf\Script.pvf"),
                        os.path.join(self.client_dir, "Script.pvf"))

            # 步骤4：复制DLL文件
            self.progress.emit(35)
            self.status.emit("正在复制补丁DLL...")
            dll_files = [
                ("ijl15.dll", r"client-patch\bin"),
                ("ijl15_real.dll", r"client-patch\bin"),
                ("90CN.dll", r"client-patch\bin"),
                ("90CNLua.dll", r"client-lua\bin"),
            ]
            for dll_name, src_dir in dll_files:
                self.log.emit("复制 " + dll_name + "...")
                shutil.copy2(os.path.join(self.server_dir, src_dir, dll_name),
                            os.path.join(self.client_dir, dll_name))

            # 步骤5：创建lua目录并复制
            self.progress.emit(50)
            self.status.emit("正在配置Lua脚本...")
            os.makedirs(os.path.join(self.client_dir, "lua", "ai"), exist_ok=True)
            self.log.emit("复制 lua/init.lua...")
            shutil.copy2(os.path.join(self.server_dir, r"client-lua\bin\lua\init.lua"),
                        os.path.join(self.client_dir, "lua", "init.lua"))
            self.log.emit("复制 lua/ai/init.lua...")
            shutil.copy2(os.path.join(self.server_dir, r"client-lua\bin\lua\ai\init.lua"),
                        os.path.join(self.client_dir, "lua", "ai", "init.lua"))

            # 步骤6：复制ImagePacks2
            self.progress.emit(65)
            self.status.emit("正在复制资源文件...")
            os.makedirs(os.path.join(self.client_dir, "ImagePacks2"), exist_ok=True)
            src_img = os.path.join(self.server_dir, "ImagePacks2")
            dst_img = os.path.join(self.client_dir, "ImagePacks2")
            for item in os.listdir(src_img):
                src_item = os.path.join(src_img, item)
                dst_item = os.path.join(dst_img, item)
                if os.path.isfile(src_item):
                    self.log.emit("复制 ImagePacks2/" + item + "...")
                    shutil.copy2(src_item, dst_item)

            # 步骤7：配置客户端目录
            self.progress.emit(80)
            self.status.emit("正在配置客户端...")
            self.log.emit("调用 control.bat configure-client...")

            control_bat = os.path.join(self.server_dir, r"deploy\windows\control.bat")
            if os.path.exists(control_bat):
                result = subprocess.run([control_bat, 'configure-client', '--directory', self.client_dir],
                                      capture_output=True, text=True, cwd=self.server_dir)
                if result.returncode != 0:
                    self.log.emit("警告: configure-client 返回非零退出码")
                else:
                    self.log.emit("客户端配置完成")
            else:
                self.log.emit("警告: 未找到 control.bat，跳过客户端配置")

            # 步骤8：需要选择数据库
            self.progress.emit(90)
            self.status.emit("请选择数据库模式...")
            self.log.emit("等待用户选择数据库模式...")
            self.need_db_select.emit()

            # 等待数据库选择
            self._wait_for_db = True
            while self._wait_for_db:
                self.msleep(100)

            # 步骤9：配置数据库
            self.progress.emit(95)
            self.status.emit("正在配置数据库...")
            self.log.emit("配置数据库模式: " + self.database_mode)

            if os.path.exists(control_bat):
                if self.database_mode == "mysql":
                    result = subprocess.run([control_bat, 'database', 'select', '--mode', 'mysql', '--prepare'],
                                          capture_output=True, text=True, cwd=self.server_dir)
                else:
                    result = subprocess.run([control_bat, 'database', 'select', '--mode', 'sqlite'],
                                          capture_output=True, text=True, cwd=self.server_dir)

                if result.returncode != 0:
                    self.log.emit("警告: database select 返回非零退出码")
                else:
                    self.log.emit("数据库配置完成")

            self.progress.emit(100)
            self.status.emit("安装完成！")
            self.log.emit("\n客户端补丁安装完成！")
            self.log.emit("客户端目录: " + self.client_dir)
            self.finished.emit(True, "客户端补丁安装完成")

        except Exception as e:
            self.log.emit("异常: " + str(e))
            self.finished.emit(False, str(e))

    def continue_after_db_select(self):
        self._wait_for_db = False


class LoginPage(QWidget):
    """账号登录页面"""
    login_success = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # 当前账号信息（和服务端文字风格一致）
        self.current_account_label = QLabel("当前账号: 未登录")
        self.current_account_label.setStyleSheet(
            "color: #a0a0a0; font-size: 11px;"
        )
        self.current_account_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.current_account_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #333333;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 账号（和服务端路径标签风格一致）
        user_label = QLabel("账号")
        user_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入账号")
        self.username_input.setMinimumHeight(36)
        self.username_input.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.username_input)

        # 账号提示（默认隐藏，点击注册时显示）
        self.username_hint = QLabel("4-20个字符，支持字母、数字、下划线，区分大小写")
        self.username_hint.setStyleSheet("color: #888888; font-size: 10px;")
        self.username_hint.setAlignment(Qt.AlignLeft)
        self.username_hint.setWordWrap(True)
        self.username_hint.setVisible(False)
        layout.addWidget(self.username_hint)

        # 密码
        pass_label = QLabel("密码")
        pass_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        layout.addWidget(pass_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(36)
        self.password_input.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.password_input)

        # 密码提示（默认隐藏，点击注册时显示）
        self.password_hint = QLabel("8-72个字符，UTF-8编码")
        self.password_hint.setStyleSheet("color: #888888; font-size: 10px;")
        self.password_hint.setAlignment(Qt.AlignLeft)
        self.password_hint.setWordWrap(True)
        self.password_hint.setVisible(False)
        layout.addWidget(self.password_hint)

        # 按钮区域（两列布局，和主页面统一）
        from PyQt5.QtWidgets import QGridLayout
        btn_grid = QGridLayout()
        btn_grid.setSpacing(10)

        # 注册按钮
        register_btn = QPushButton("注册")
        register_btn.setObjectName("secondaryBtn")
        register_btn.setMinimumHeight(40)
        register_btn.setCursor(Qt.PointingHandCursor)
        register_btn.clicked.connect(self.register_account)
        btn_grid.addWidget(register_btn, 0, 0)

        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.do_login)
        btn_grid.addWidget(self.login_btn, 0, 1)

        layout.addLayout(btn_grid)

        # 日志区域（和主页面统一，高度继续增加）
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(200)
        self.status_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_text.setFrameShape(QFrame.NoFrame)
        self.status_text.setStyleSheet(
            "QTextEdit { background-color: #1a1a1a; border: 1px solid #3a3a3a; "
            "border-radius: 4px; padding: 8px; color: #88ff88; "
            "font-family: 'Consolas', 'Courier New'; font-size: 11px; }"
        )
        layout.addWidget(self.status_text, 1)

        # 初始化日志
        self.log("系统就绪，请输入账号和密码...")
        
        # 从账号保管文件读取已保存的账号密码
        saved_username, saved_password = load_account_from_file()
        if saved_username and saved_password:
            self.username_input.setText(saved_username)
            self.password_input.setText(saved_password)
            self.log("已自动填充已保存的账号")

    def log(self, message):
        """使用共享日志方法"""
        self.main_window.log(message)

    def update_current_account(self, username=None):
        """更新当前账号信息"""
        if username:
            self.current_account_label.setText("当前账号: {}".format(username))
        else:
            self.current_account_label.setText("当前账号: 未登录")

    def do_login(self):
        """执行登录或返回登录模式"""
        # 如果当前是注册模式（登录按钮显示为"返回登录"），则切换回登录模式
        if self.login_btn.text() == "返回登录":
            self.switch_to_login_mode()
            return

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.log("错误: 请输入账号和密码")
            return

        # 隐藏指令：账密均为iamgod时启动账号管理工具
        if username == "iamgod" and password == "iamgod":
            self.log("检测到管理员指令，正在启动账号管理工具...")
            self.launch_account_manager()
            return

        self.log("正在验证账号: {}...".format(username))
        QApplication.processEvents()

        # 调用主窗口的登录验证
        success, message = self.main_window.verify_account(username, password)

        if success:
            self.log("登录成功: {}".format(message))
            self.update_current_account(username)
            self.login_success.emit(username, password)
            # 保存账号密码到账号保管文件（不显示日志）
            save_account_to_file(username, password)
            # 启动游戏
            self.main_window.launch_game(username, password)
        else:
            self.log("登录失败: {}".format(message))
            self.update_current_account(None)

    def launch_account_manager(self):
        """启动账号管理工具（accmg）"""
        try:
            import subprocess
            
            # 获取launcher.exe所在目录
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(os.path.abspath(__file__))
            
            module_dir = os.path.join(app_dir, "module")
            accmg_exe = os.path.join(module_dir, "accmg.exe")
            
            if os.path.exists(accmg_exe):
                self.log("正在启动账号管理工具: {}".format(accmg_exe))
                # 传递--from-launcher参数，用于accmg验证是从主程序启动的
                subprocess.Popen([accmg_exe, "--from-launcher"], cwd=module_dir)
                self.log("账号管理工具已启动")
            else:
                self.log("错误: 未找到账号管理工具: {}".format(accmg_exe))
                show_frameless_error(self, "错误", "未找到账号管理工具:\n{}".format(accmg_exe))
        except Exception as e:
            self.log("启动账号管理工具失败: {}".format(e))
            show_frameless_error(self, "错误", "启动账号管理工具失败:\n{}".format(e))

    def switch_to_register_mode(self):
        """切换到注册模式"""
        self.username_hint.setVisible(True)
        self.password_hint.setVisible(True)
        self.login_btn.setText("返回登录")
        self.log("已切换到注册模式，请输入账号和密码后点击注册")

    def switch_to_login_mode(self):
        """切换回登录模式"""
        self.username_hint.setVisible(False)
        self.password_hint.setVisible(False)
        self.login_btn.setText("登录")
        self.log("已返回登录模式")

    def register_account(self):
        """注册账号"""
        # 如果还没显示提示，先切换到注册模式
        if not self.username_hint.isVisible():
            self.switch_to_register_mode()
            return

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.log("错误: 请输入账号和密码进行注册")
            return

        self.log("正在注册账号: {}...".format(username))
        QApplication.processEvents()

        success, message = self.main_window.register_account(username, password)

        if success:
            self.log("注册成功: {}".format(message))
            # 注册成功后切换回登录模式
            self.switch_to_login_mode()
        else:
            self.log("注册失败: {}".format(message))


class LaunchGameWorker(QThread):
    """启动游戏工作线程"""
    log_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, server_path, client_path, username, password):
        super().__init__()
        self.server_path = server_path
        self.client_path = client_path
        self.username = username
        self.password = password

    def _check_port_open(self, host, port, timeout=2):
        """检查端口是否开放（不依赖pymysql）"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
                return result == 0
        except:
            return False

    def _get_mysql_config(self):
        """从instance.json获取MySQL配置（同时支持原版和Python版服务端路径）"""
        try:
            # 优先尝试Python版服务端路径
            config_file = os.path.join(self.server_path, "instance.json")
            if not os.path.exists(config_file):
                # 如果不存在，尝试原版服务端路径
                config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            db_config = config.get("database", {})
            return db_config.get("host", "127.0.0.1"), db_config.get("port", 13306)
        except:
            return "127.0.0.1", 13306
    
    def _get_db_mode(self):
        """从instance.json获取数据库模式（mysql或sqlite）（同时支持原版和Python版服务端路径）"""
        try:
            # 优先尝试Python版服务端路径
            config_file = os.path.join(self.server_path, "instance.json")
            if not os.path.exists(config_file):
                # 如果不存在，尝试原版服务端路径
                config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            db_config = config.get("database", {})
            return db_config.get("mode", "portable")
        except:
            return "portable"
    
    def _is_sqlite_mode(self):
        """判断是否为SQLite模式（优先从配置文件读取，其次从instance.json读取）"""
        # 1. 优先从启动器配置文件读取数据库模式
        try:
            # 配置文件位于程序所在目录下的config.lau
            import sys
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(os.path.abspath(__file__))
            
            config_file = os.path.join(app_dir, "config.lau")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                db_mode = config.get('db_mode', '')
                if db_mode:
                    return db_mode == "sqlite"
        except:
            pass
        
        # 2. 如果配置文件中没有，从instance.json读取
        mode = self._get_db_mode()
        if mode == "sqlite":
            return True
        
        # 3. 都没有的话，默认返回False（MySQL模式）
        return False

    def run(self):
        try:
            import time
            
            # 检测服务端类型（原版或Python版）
            server_exe = os.path.join(self.server_path, "dnf90_server.exe")
            control_exe = os.path.join(self.server_path, "runtime", "bin", "DNF90Control.exe")
            is_python_server = os.path.exists(server_exe) and not os.path.exists(control_exe)
            
            if is_python_server:
                self.log_message.emit("检测到Python版服务端")
                # 验证服务端路径
                if not os.path.exists(server_exe):
                    error_msg = "未找到 dnf90_server.exe，请检查服务端路径配置"
                    self.log_message.emit("错误: {}".format(error_msg))
                    self.finished.emit(False, error_msg)
                    return
            else:
                self.log_message.emit("检测到原版服务端")
                # 验证服务端路径
                if not os.path.exists(control_exe):
                    error_msg = "未找到 DNF90Control.exe，请检查服务端路径配置"
                    self.log_message.emit("错误: {}".format(error_msg))
                    self.finished.emit(False, error_msg)
                    return

            # 验证instance.json存在（同时支持两种路径）
            config_file = os.path.join(self.server_path, "instance.json")
            if not os.path.exists(config_file):
                config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            if not os.path.exists(config_file):
                error_msg = "未找到 instance.json 配置文件，服务端目录结构可能不完整"
                self.log_message.emit("错误: {}".format(error_msg))
                self.finished.emit(False, error_msg)
                return

            # 获取数据库配置
            mysql_host, mysql_port = self._get_mysql_config()
            is_sqlite = self._is_sqlite_mode()
            
            # 根据数据库模式选择检查的端口
            if is_sqlite:
                check_host = "127.0.0.1"
                check_port = 7001
                db_type = "SQLite"
            else:
                check_host = mysql_host
                check_port = mysql_port
                db_type = "MySQL"
            
            self.log_message.emit("数据库模式: {} (检查端口: {})".format(db_type, check_port))

            # 检查服务端是否已经启动（用端口检测）
            server_running = self._check_port_open(check_host, check_port, timeout=2)

            if not server_running:
                # 准备环境变量
                env = os.environ.copy()
                env["DNF90_PROJECT_ROOT"] = self.server_path
                env["DNF_RESIDENT_CHANNEL_ID"] = "19"
                
                # 启动服务端
                self.log_message.emit("正在启动服务端...")
                self.log_message.emit("服务端路径: {}".format(self.server_path))
                
                try:
                    if is_python_server:
                        # Python版服务端：直接启动dnf90_server.exe
                        proc = subprocess.Popen(
                            [server_exe, "-c", config_file],
                            cwd=self.server_path,
                            env=env,
                            creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
                        )
                        self.log_message.emit("Python版服务端进程已启动（PID: {}）".format(proc.pid))
                    else:
                        # 原版服务端：使用DNF90Control.exe start
                        log_file_path = os.path.join(os.path.dirname(self.server_path), "server_startup.log")
                        try:
                            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                                proc = subprocess.Popen(
                                    [control_exe, "start"],
                                    cwd=self.server_path,
                                    env=env,
                                    stdout=log_file,
                                    stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                                )
                        except:
                            proc = subprocess.Popen(
                                [control_exe, "start"],
                                cwd=self.server_path,
                                env=env,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                        self.log_message.emit("服务端进程已启动，等待{}就绪...".format(db_type))
                    
                except Exception as e:
                    import traceback
                    error_msg = "服务端启动失败: {}".format(str(e))
                    self.log_message.emit("错误: {}".format(error_msg))
                    write_error_log("服务端启动异常", str(e), traceback.format_exc())
                    self.finished.emit(False, error_msg)
                    return

                # 轮询等待数据库就绪（最多等待60秒）
                max_wait = 60
                start_time = time.time()
                last_log_time = 0
                while time.time() - start_time < max_wait:
                    if self._check_port_open(check_host, check_port, timeout=2):
                        self.log_message.emit("{}已就绪，服务端启动成功".format(db_type))
                        server_running = True
                        break
                    
                    elapsed = int(time.time() - start_time)
                    if elapsed - last_log_time >= 10:
                        self.log_message.emit("等待服务端启动... ({}/{}秒)".format(elapsed, max_wait))
                        last_log_time = elapsed
                    
                    time.sleep(1)
                
                if not server_running:
                    error_msg = "服务端启动超时（{}秒），请检查: 1.是否以管理员身份运行 2.端口{}是否被占用 3.杀毒软件是否拦截".format(max_wait, check_port)
                    self.log_message.emit("错误: {}".format(error_msg))
                    self.finished.emit(False, error_msg)
                    return
            else:
                self.log_message.emit("服务端已在运行")

            # 启动客户端
            self.log_message.emit("正在启动客户端...")

            try:
                if is_python_server:
                    # Python版服务端：生成TCLS启动参数并启动DNF.exe
                    dnf_exe = os.path.join(self.client_path, "DNF.exe")
                    if not os.path.exists(dnf_exe):
                        error_msg = "未找到客户端DNF.exe，请检查客户端路径配置"
                        self.log_message.emit("错误: {}".format(error_msg))
                        self.finished.emit(False, error_msg)
                        return
                    
                    # 从instance.json读取配置，生成TCLS启动参数
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        
                        # 解析频道监听地址
                        channel_listen = cfg.get("server", {}).get("channelListen", "127.0.0.1:7001")
                        if ":" in channel_listen:
                            login_host, channel_port_str = channel_listen.rsplit(":", 1)
                            channel_port = int(channel_port_str)
                        else:
                            login_host = "127.0.0.1"
                            channel_port = 7001
                        
                        # 解析管理监听地址
                        admin_listen = cfg.get("server", {}).get("adminListen", "127.0.0.1:18111")
                        if ":" in admin_listen:
                            admin_host, admin_port_str = admin_listen.rsplit(":", 1)
                            admin_port = int(admin_port_str)
                        else:
                            admin_host = "127.0.0.1"
                            admin_port = 18111
                        
                        admin_token = cfg.get("server", {}).get("adminToken", "")
                        default_account_id = cfg.get("server", {}).get("accountId", "")
                        
                        # 读取其他配置
                        initial_game_port = cfg.get("client", {}).get("initialGamePort", 0)
                        game_outer_token = cfg.get("protocol", {}).get("gameOuterToken", "")
                        hook_create = cfg.get("client", {}).get("hookCreate", True)
                        
                        # 验证账号并获取account_id
                        account_id = default_account_id
                        if self.username and self.password:
                            self.log_message.emit("正在验证账号...")
                            try:
                                import pymysql
                                import bcrypt
                                
                                db_config = cfg.get("database", {})
                                conn = pymysql.connect(
                                    host=db_config.get("host", "127.0.0.1"),
                                    port=db_config.get("port", 13306),
                                    user=db_config.get("user", "root"),
                                    password=db_config.get("password", ""),
                                    database=db_config.get("name", "dnf_local"),
                                    charset="utf8mb4"
                                )
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT account_id, password_hash, state FROM dnf_login_accounts WHERE username = %s",
                                    (self.username,)
                                )
                                result = cursor.fetchone()
                                cursor.close()
                                conn.close()
                                
                                if result:
                                    db_account_id, password_hash, state = result
                                    if state == "active":
                                        if isinstance(password_hash, bytes):
                                            password_hash = password_hash.decode('utf-8')
                                        if bcrypt.checkpw(self.password.encode('utf-8'), password_hash.encode('utf-8')):
                                            account_id = db_account_id
                                            self.log_message.emit("账号验证成功: {}".format(self.username))
                                        else:
                                            self.log_message.emit("警告: 密码错误，使用默认账号")
                                    else:
                                        self.log_message.emit("警告: 账号已禁用，使用默认账号")
                                else:
                                    self.log_message.emit("警告: 账号不存在，使用默认账号")
                            except Exception as e:
                                self.log_message.emit("账号验证异常: {}，使用默认账号".format(str(e)))
                        
                        # 生成TCLS启动参数
                        tcls_argument = "99?{}?{}?{}?{}?01?1?0?0?0?0?1?9n2b1c8r3w7y?0?0?19847".format(
                            login_host,
                            channel_port,
                            initial_game_port,
                            game_outer_token
                        )
                        
                        self.log_message.emit("TCLS参数: {}?{}?{}...".format(login_host, channel_port, initial_game_port))
                        
                        # 设置环境变量
                        env = os.environ.copy()
                        env["DNF_HOOK_CREATE"] = "1" if hook_create else "0"
                        env["DNF_MULTI_CLIENT"] = "0"
                        env["DNF_RESIDENT_CHANNEL_ID"] = "19"
                        
                        # 启动客户端
                        self.log_message.emit("正在启动客户端...")
                        proc = subprocess.Popen(
                            [dnf_exe, tcls_argument],
                            cwd=self.client_path,
                            env=env
                        )
                        
                        client_pid = proc.pid
                        self.log_message.emit("游戏启动成功！(PID: {})".format(client_pid))
                        
                        # 账号绑定：发送HTTP请求到服务端管理接口
                        if account_id:
                            self.log_message.emit("正在绑定客户端账号...")
                            try:
                                import urllib.request
                                import urllib.error
                                
                                bind_url = "http://{}:{}/local/client-account".format(admin_host, admin_port)
                                bind_data = json.dumps({
                                    "pid": client_pid,
                                    "account_id": account_id
                                }).encode('utf-8')
                                
                                request = urllib.request.Request(
                                    bind_url,
                                    data=bind_data,
                                    headers={
                                        'Content-Type': 'application/json',
                                        'X-Admin-Token': admin_token
                                    },
                                    method='POST'
                                )
                                
                                with urllib.request.urlopen(request, timeout=5) as response:
                                    if response.status == 200:
                                        self.log_message.emit("客户端账号绑定成功: AccountID={}".format(account_id))
                                    else:
                                        self.log_message.emit("警告: 账号绑定返回状态码: {}".format(response.status))
                            except Exception as e:
                                self.log_message.emit("警告: 账号绑定失败: {}".format(str(e)))
                        
                        self.finished.emit(True, "游戏启动成功")
                        
                    except Exception as e:
                        import traceback
                        error_msg = "生成TCLS参数失败: {}".format(str(e))
                        self.log_message.emit("错误: {}".format(error_msg))
                        write_error_log("客户端启动异常", str(e), traceback.format_exc())
                        self.finished.emit(False, error_msg)
                else:
                    # 原版服务端：使用DNF90Control.exe launch-client
                    launch_args = [control_exe, "launch-client", "--multi-instance"]
                    if self.client_path and os.path.exists(self.client_path):
                        launch_args.extend(["--client-directory", self.client_path])
                    launch_args.extend(["--username", self.username, "--password-stdin"])

                    proc = subprocess.Popen(
                        launch_args,
                        cwd=self.server_path,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )

                    # 通过标准输入传递密码
                    try:
                        proc.stdin.write((self.password + "\n").encode('utf-8'))
                        proc.stdin.flush()
                        proc.stdin.close()
                    except Exception as e:
                        self.log_message.emit("密码传递提示: {}".format(str(e)))

                    try:
                        stdout, stderr = proc.communicate(timeout=15)
                        if proc.returncode == 0:
                            self.log_message.emit("游戏启动成功！")
                            self.finished.emit(True, "游戏启动成功")
                        else:
                            self.log_message.emit("启动返回码: {}".format(proc.returncode))
                            if stdout:
                                self.log_message.emit("输出: {}".format(stdout.decode('gbk', errors='ignore')[-300:]))
                            if stderr:
                                self.log_message.emit("错误: {}".format(stderr.decode('gbk', errors='ignore')[-300:]))
                            self.finished.emit(False, "启动返回码: {}".format(proc.returncode))
                    except subprocess.TimeoutExpired:
                        self.log_message.emit("启动中...（请检查游戏窗口）")
                        proc.kill()
                        self.finished.emit(True, "启动中")

            except Exception as e:
                import traceback
                self.log_message.emit("客户端启动提示: {}".format(str(e)))
                write_error_log("客户端启动异常", str(e), traceback.format_exc())
                # 备用方案：直接启动DNF.exe
                dnf_exe = os.path.join(self.client_path, "DNF.exe")
                if os.path.exists(dnf_exe):
                    self.log_message.emit("尝试直接启动客户端...")
                    subprocess.Popen([dnf_exe], cwd=self.client_path)
                    self.finished.emit(True, "直接启动客户端")
                else:
                    self.finished.emit(False, "启动失败: {}".format(str(e)))

        except Exception as e:
            import traceback
            write_error_log("游戏启动失败", str(e), traceback.format_exc())
            self.finished.emit(False, "启动失败: {}".format(str(e)))


class BackupWorker(QThread):
    """备份工作线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, source_dir, backup_dir, mode='backup', specific_backup=None):
        super().__init__()
        self.source_dir = source_dir
        self.backup_dir = backup_dir
        self.mode = mode
        self.specific_backup = specific_backup

    def run(self):
        try:
            if self.mode == 'backup':
                self.do_backup()
            else:
                self.do_restore()
        except Exception as e:
            import traceback
            # 写入错误日志
            write_error_log(f"数据{self.mode}异常", str(e), traceback.format_exc())
            self.finished.emit(False, str(e))

    def do_backup(self):
        """执行备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, "backup_{}".format(timestamp))
        os.makedirs(backup_path, exist_ok=True)

        # 1. 备份MySQL数据目录
        mysql_data = os.path.join(self.source_dir, "runtime", "mysql", "data")
        if os.path.exists(mysql_data):
            self.progress.emit(10, "正在备份MySQL数据...")
            dest_mysql = os.path.join(backup_path, "mysql_data")
            self.copy_directory(mysql_data, dest_mysql)

        # 2. 备份SQLite数据库
        sqlite_db = os.path.join(self.source_dir, "runtime", "data", "dnf90.db")
        if os.path.exists(sqlite_db):
            self.progress.emit(60, "正在备份SQLite数据库...")
            shutil.copy2(sqlite_db, os.path.join(backup_path, "dnf90.db"))

        # 3. 备份配置文件
        config_file = os.path.join(self.source_dir, "runtime", "config", "instance.json")
        if os.path.exists(config_file):
            self.progress.emit(80, "正在备份配置文件...")
            shutil.copy2(config_file, os.path.join(backup_path, "instance.json"))

        # 4. 保存备份信息
        info = {
            "backup_time": datetime.now().isoformat(),
            "source_dir": self.source_dir,
            "mysql_data": os.path.exists(mysql_data),
            "sqlite_db": os.path.exists(sqlite_db),
            "config_file": os.path.exists(config_file)
        }
        with open(os.path.join(backup_path, "backup_info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        self.progress.emit(100, "备份完成！")
        self.finished.emit(True, "备份已保存到: {}".format(backup_path))

    def do_restore(self):
        """执行恢复"""
        if not os.path.exists(self.backup_dir):
            self.finished.emit(False, "未找到备份目录")
            return

        # 如果指定了备份，就使用指定的备份；否则就使用最新的备份
        if self.specific_backup:
            selected_backup = self.specific_backup
            backup_path = os.path.join(self.backup_dir, selected_backup)
            if not os.path.exists(backup_path):
                self.finished.emit(False, f"未找到指定备份: {selected_backup}")
                return
        else:
            backups = [d for d in os.listdir(self.backup_dir)
                       if d.startswith("backup_") and os.path.isdir(os.path.join(self.backup_dir, d))]
            if not backups:
                self.finished.emit(False, "未找到任何备份")
                return
            backups.sort(reverse=True)
            selected_backup = backups[0]
            backup_path = os.path.join(self.backup_dir, selected_backup)

        # 1. 恢复MySQL数据目录
        mysql_backup = os.path.join(backup_path, "mysql_data")
        mysql_dest = os.path.join(self.source_dir, "runtime", "mysql", "data")
        if os.path.exists(mysql_backup):
            self.progress.emit(20, "正在恢复MySQL数据...")
            if os.path.exists(mysql_dest):
                old_backup = mysql_dest + "_old_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                os.rename(mysql_dest, old_backup)
            self.copy_directory(mysql_backup, mysql_dest)

        # 2. 恢复SQLite数据库
        sqlite_backup = os.path.join(backup_path, "dnf90.db")
        sqlite_dest = os.path.join(self.source_dir, "runtime", "data", "dnf90.db")
        if os.path.exists(sqlite_backup):
            self.progress.emit(70, "正在恢复SQLite数据库...")
            os.makedirs(os.path.dirname(sqlite_dest), exist_ok=True)
            shutil.copy2(sqlite_backup, sqlite_dest)

        # 3. 恢复配置文件
        config_backup = os.path.join(backup_path, "instance.json")
        config_dest = os.path.join(self.source_dir, "runtime", "config", "instance.json")
        if os.path.exists(config_backup):
            self.progress.emit(90, "正在恢复配置文件...")
            shutil.copy2(config_backup, config_dest)

        self.progress.emit(100, "恢复完成！")
        self.finished.emit(True, "已从备份恢复: {}".format(selected_backup))

    def copy_directory(self, src, dst):
        """复制目录（带进度）"""
        total_files = sum([len(files) for r, d, files in os.walk(src)])
        copied = 0
        os.makedirs(dst, exist_ok=True)

        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            dest_root = os.path.join(dst, rel_path)
            os.makedirs(dest_root, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_root, file)
                shutil.copy2(src_file, dest_file)
                copied += 1
                if copied % 50 == 0:
                    progress = int((copied / total_files) * 100)
                    self.progress.emit(progress, "正在复制文件... ({}/{})".format(copied, total_files))


if __name__ == "__main__":

    main()



