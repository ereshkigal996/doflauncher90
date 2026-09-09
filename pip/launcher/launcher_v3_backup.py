# -*- coding: utf-8 -*-
"""
DNF轮回 - 简易启动器 (重构版)
版本: 3.0.0
支持双服务端：原版Go服务端 + Python版服务端
UI风格：GM工具深色主题
"""

import os
import sys
import json
import shutil
import subprocess
import threading
import time
import socket
from datetime import datetime

from PyQt5.QtWidgets import (QGraphicsOpacityEffect, 
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox, QDialog, QFrame,
    QStackedWidget, QProgressBar, QComboBox, QTextEdit, QFileDialog,
    QSizePolicy, QGroupBox, QGridLayout, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QIcon

# 程序版本号
APP_VERSION = "3.0.0"
APP_NAME = "DNF轮回启动器"

# ========== 通用样式字典 ==========
STYLES = {
    "base_qpushbutton": """
        QPushButton {
            background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;
            border-radius: 4px; padding: 8px 12px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover { background-color: #3a3a3a; border-color: #5a5a5a; }
        QPushButton:pressed { background-color: #4a4a4a; }
        QPushButton:disabled { background-color: #1a1a1a; color: #555555; border-color: #2a2a2a; }
    """,
    "primary": """
        QPushButton {
            background-color: #0078d4; color: #ffffff; border: none;
            border-radius: 4px; font-size: 13px; padding: 6px 16px;
        }
        QPushButton:hover { background-color: #106ebe; }
        QPushButton:pressed { background-color: #005a9e; }
    """,
    "dark": """
        QPushButton {
            background-color: #333333; color: #ffffff; border: none;
            border-radius: 4px; font-size: 14px; font-weight: bold; padding: 8px 16px;
        }
        QPushButton:hover { background-color: #3d3d3d; }
        QPushButton:pressed { background-color: #444444; }
    """,
    "small_label": "color: #888888; font-size: 11px; background-color: transparent;",
    "path_label": "color: #b0b0b0; font-size: 12px; background-color: transparent;",
    "line_edit": """
        QLineEdit {
            background-color: #1a1a1a; color: #ffffff; border: 1px solid #3a3a3a;
            border-radius: 4px; padding: 8px 12px; font-size: 13px; min-height: 24px;
        }
        QLineEdit:focus { border-color: #4a90d9; }
    """,
    "close_btn": """
        QPushButton { background-color: transparent; color: #888888; border: none;
            border-radius: 4px; font-size: 14px; }
    """,
}

# ========== 配置管理 ==========
class ConfigManager:
    """配置管理器 - 带延迟保存，减少IO"""
    _instance = None
    _config = None
    _config_path = None
    _save_timer = None
    _dirty = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is not None:
            return
        self.load_config()
    
    def get_config_dir(self):
        """获取配置文件目录"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    
    def load_config(self):
        """加载配置文件"""
        config_dir = self.get_config_dir()
        self._config_path = os.path.join(config_dir, "launcher.json")
        
        default_config = {
            "server_type": "go",  # go / python
            "go_server_path": "",
            "python_server_path": "",
            "client_path": "",
            "last_account": "",
            "window_geometry": None,
            "settings": {
                "auto_start_server": True,
                "auto_close_after_login": False,
                "theme": "dark"
            }
        }
        
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8-sig') as f:
                    self._config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in self._config:
                        self._config[key] = value
            except Exception as e:
                print(f"配置文件加载失败: {e}")
                self._config = default_config
        else:
            self._config = default_config
    
    def save_config(self):
        """立即保存配置文件"""
        if self._config_path and self._config and self._dirty:
            try:
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=4, ensure_ascii=False)
                self._dirty = False
            except Exception as e:
                print(f"配置文件保存失败: {e}")
    
    def _schedule_save(self):
        """延迟保存，500ms后执行"""
        if self._save_timer is None:
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save_config)
        self._save_timer.start(500)
    
    def get(self, key, default=None):
        """获取配置项"""
        if self._config:
            return self._config.get(key, default)
        return default
    
    def set(self, key, value):
        """设置配置项（延迟保存）"""
        if self._config is not None:
            self._config[key] = value
            self._dirty = True
            self._schedule_save()

# ========== 服务端状态检测 ==========
class ServerStatusChecker:
    """服务端状态检测器"""
    
    @staticmethod
    def check_port(host, port, timeout=2):
        """检查端口是否开放"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    @staticmethod
    def check_go_server():
        """检查Go服务端状态"""
        # Go服务端通常监听7001(频道)和18111(管理)
        return ServerStatusChecker.check_port("127.0.0.1", 7001)
    
    @staticmethod
    def check_python_server():
        """检查Python服务端状态"""
        # Python服务端同样监听7001和18111
        return ServerStatusChecker.check_port("127.0.0.1", 7001)
    
    @staticmethod
    def check_mysql():
        """检查MySQL状态"""
        return ServerStatusChecker.check_port("127.0.0.1", 13306)

# ========== 通用对话框（GM工具风格） ==========
class GMDialog(QDialog):
    """通用对话框 - GM工具深色风格"""
    
    def __init__(self, title="提示", parent=None, show_back=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(400)
        self.dragging = False
        self.drag_position = QPoint()
        self.show_back = show_back
        self.init_ui(title)
    
    def init_ui(self, title):
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet("""
            QWidget#mainContainer {
                background-color: #2a2a2a;
                border-radius: 8px;
            }
            QPushButton#titleBtn {
                background-color: transparent; color: #b0b0b0; border: none;
                font-size: 14px; border-radius: 4px;
            }
            QPushButton#titleBtn:hover {
                background-color: #3a3a3a; color: #ffffff;
            }
            QPushButton#closeBtn {
                background-color: transparent; color: #999999; border: none;
                font-size: 14px; border-radius: 4px;
            }
            QPushButton#closeBtn:hover {
                background-color: #c42b1c; color: #ffffff;
            }
            QPushButton#dangerBtn {
                background-color: #c42b1c; color: #ffffff; border: none;
                border-radius: 4px; font-size: 13px; padding: 6px 16px;
            }
            QPushButton#dangerBtn:hover { background-color: #a5281a; }
            QPushButton#successBtn {
                background-color: #107c10; color: #ffffff; border: none;
                border-radius: 4px; font-size: 13px; padding: 6px 16px;
            }
            QPushButton#successBtn:hover { background-color: #0e6b0e; }
        """)
        
        layout = QVBoxLayout(self.main_container)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)
        
        # 标题行
        title_container = QWidget()
        title_container.setStyleSheet("background-color: transparent; border: none;")
        title_row = QHBoxLayout(title_container)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        
        if self.show_back:
            back_btn = QPushButton("←")
            back_btn.setObjectName("titleBtn")
            back_btn.setFixedSize(28, 24)
            back_btn.setCursor(Qt.PointingHandCursor)
            back_btn.clicked.connect(self.reject)
            title_row.addWidget(back_btn)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            background-color: transparent;
            border: none;
        """)
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(28, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        
        layout.addWidget(title_container)
        
        # 内容区域
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #2a2a2a; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        layout.addWidget(self.content_widget)
        
        # 按钮区域
        self.button_widget = QWidget()
        self.button_widget.setStyleSheet("background-color: #2a2a2a; border: none;")
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(10)
        self.button_layout.addStretch()
        layout.addWidget(self.button_widget)
        
        # 拖动支持 + 双击最小化
        self.main_container.mousePressEvent = self.mousePressEvent
        self.main_container.mouseMoveEvent = self.mouseMoveEvent
        self.main_container.mouseReleaseEvent = self.mouseReleaseEvent
        self.main_container.mouseDoubleClickEvent = self.on_title_double_click
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_container)
    
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
        self.dragging = False
    
    def on_title_double_click(self, event):
        self.showMinimized()
    
    def add_button(self, text, on_click, btn_type="normal"):
        """添加按钮"""
        btn = QPushButton(text)
        if btn_type == "danger":
            btn.setObjectName("dangerBtn")
        elif btn_type == "success":
            btn.setObjectName("successBtn")
        elif btn_type == "primary":
            btn.setStyleSheet("""
                QPushButton { background-color: #0078d4; color: #ffffff; border: none;
                    border-radius: 4px; font-size: 13px; padding: 6px 16px; }
                QPushButton:hover { background-color: #106ebe; }
                QPushButton:pressed { background-color: #005a9e; }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton { background-color: #3a3a3a; color: #e0e0e0;
                    border: 1px solid #555555; border-radius: 4px; font-size: 13px; padding: 6px 16px; }
                QPushButton:hover { background-color: #4a4a4a; border-color: #666666; }
            """)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(32)
        btn.setMinimumWidth(80)
        btn.clicked.connect(on_click)
        self.button_layout.addWidget(btn)
        return btn
    
    @staticmethod
    def information(parent, title, message):
        """信息提示框"""
        dialog = GMDialog(title, parent)
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #e0e0e0; font-size: 13px; background-color: transparent;")
        msg_label.setWordWrap(True)
        dialog.content_layout.addWidget(msg_label)
        dialog.add_button("确定", dialog.accept, "primary")
        return dialog.exec_()
    
    @staticmethod
    def warning(parent, title, message):
        """警告提示框"""
        dialog = GMDialog(title, parent)
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #ffcc00; font-size: 13px; background-color: transparent;")
        msg_label.setWordWrap(True)
        dialog.content_layout.addWidget(msg_label)
        dialog.add_button("确定", dialog.accept, "primary")
        return dialog.exec_()
    
    @staticmethod
    def question(parent, title, message, buttons=QMessageBox.Yes | QMessageBox.No):
        """确认对话框"""
        dialog = GMDialog(title, parent)
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #e0e0e0; font-size: 13px; background-color: transparent;")
        msg_label.setWordWrap(True)
        dialog.content_layout.addWidget(msg_label)
        
        result = QMessageBox.No
        
        def on_yes():
            nonlocal result
            result = QMessageBox.Yes
            dialog.accept()
        
        def on_no():
            nonlocal result
            result = QMessageBox.No
            dialog.reject()
        
        if buttons & QMessageBox.Yes:
            dialog.add_button("是", on_yes, "primary")
        if buttons & QMessageBox.No:
            dialog.add_button("否", on_no, "normal")
        if buttons & QMessageBox.Ok:
            dialog.add_button("确定", on_yes, "primary")
        if buttons & QMessageBox.Cancel:
            dialog.add_button("取消", on_no, "normal")
        
        dialog.exec_()
        return result

# ========== 路径设置页面 ==========
class PathSetupPage(QWidget):
    """路径设置页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # 输入框样式
        edit_style = """
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                min-height: 24px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """
        btn_browse_style = """
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """
        label_style = "color: #cccccc; font-size: 12px; font-weight: bold; background-color: transparent;"

        # ===== 服务端类型 =====
        type_group = QWidget()
        type_layout = QVBoxLayout(type_group)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(8)

        type_label = QLabel("服务端类型")
        type_label.setStyleSheet(label_style)
        type_layout.addWidget(type_label)

        self.server_type_combo = QComboBox()
        self.server_type_combo.addItem("第三方服务端（Go原版）", "go")
        self.server_type_combo.addItem("一体式服务端（Python）", "python")
        self.server_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                min-height: 24px;
            }
            QComboBox:hover { border-color: #4a90d9; }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
        """)
        current_type = self.config.get("server_type", "go")
        idx = self.server_type_combo.findData(current_type)
        if idx >= 0:
            self.server_type_combo.setCurrentIndex(idx)
        self.server_type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.server_type_combo)
        layout.addWidget(type_group)

        # ===== 第三方服务端路径 =====
        self.go_group = QWidget()
        go_layout = QVBoxLayout(self.go_group)
        go_layout.setContentsMargins(0, 0, 0, 0)
        go_layout.setSpacing(8)

        go_label = QLabel("第三方服务端路径")
        go_label.setStyleSheet(label_style)
        go_layout.addWidget(go_label)

        go_row = QWidget()
        go_row_layout = QHBoxLayout(go_row)
        go_row_layout.setContentsMargins(0, 0, 0, 0)
        go_row_layout.setSpacing(8)
        self.go_path_edit = QLineEdit()
        self.go_path_edit.setPlaceholderText("请选择第三方服务端目录")
        self.go_path_edit.setText(self.config.get("go_server_path", ""))
        self.go_path_edit.setStyleSheet(edit_style)
        go_row_layout.addWidget(self.go_path_edit)
        go_browse = QPushButton("浏览")
        go_browse.setCursor(Qt.PointingHandCursor)
        go_browse.setStyleSheet(btn_browse_style)
        go_browse.clicked.connect(self.browse_go_path)
        go_row_layout.addWidget(go_browse)
        go_layout.addWidget(go_row)
        layout.addWidget(self.go_group)

        # ===== 一体式服务端路径 =====
        self.python_group = QWidget()
        py_layout = QVBoxLayout(self.python_group)
        py_layout.setContentsMargins(0, 0, 0, 0)
        py_layout.setSpacing(8)

        py_label = QLabel("一体式服务端路径")
        py_label.setStyleSheet(label_style)
        py_layout.addWidget(py_label)

        py_row = QWidget()
        py_row_layout = QHBoxLayout(py_row)
        py_row_layout.setContentsMargins(0, 0, 0, 0)
        py_row_layout.setSpacing(8)
        self.python_path_edit = QLineEdit()
        self.python_path_edit.setPlaceholderText("请选择一体式服务端目录")
        self.python_path_edit.setText(self.config.get("python_server_path", ""))
        self.python_path_edit.setStyleSheet(edit_style)
        py_row_layout.addWidget(self.python_path_edit)
        py_browse = QPushButton("浏览")
        py_browse.setCursor(Qt.PointingHandCursor)
        py_browse.setStyleSheet(btn_browse_style)
        py_browse.clicked.connect(self.browse_python_path)
        py_row_layout.addWidget(py_browse)
        py_layout.addWidget(py_row)
        layout.addWidget(self.python_group)

        # ===== 客户端路径 =====
        client_group = QWidget()
        client_layout = QVBoxLayout(client_group)
        client_layout.setContentsMargins(0, 0, 0, 0)
        client_layout.setSpacing(8)

        client_label = QLabel("客户端路径")
        client_label.setStyleSheet(label_style)
        client_layout.addWidget(client_label)

        client_row = QWidget()
        client_row_layout = QHBoxLayout(client_row)
        client_row_layout.setContentsMargins(0, 0, 0, 0)
        client_row_layout.setSpacing(8)
        self.client_path_edit = QLineEdit()
        self.client_path_edit.setPlaceholderText("请选择DNF客户端目录（包含DNF.exe）")
        self.client_path_edit.setText(self.config.get("client_path", ""))
        self.client_path_edit.setStyleSheet(edit_style)
        client_row_layout.addWidget(self.client_path_edit)
        client_browse = QPushButton("浏览")
        client_browse.setCursor(Qt.PointingHandCursor)
        client_browse.setStyleSheet(btn_browse_style)
        client_browse.clicked.connect(self.browse_client_path)
        client_row_layout.addWidget(client_browse)
        client_layout.addWidget(client_row)
        layout.addWidget(client_group)

        layout.addStretch()

        # ===== 保存按钮 =====
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        self.confirm_btn = QPushButton("保存")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setMinimumHeight(36)
        self.confirm_btn.setMinimumWidth(120)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        self.confirm_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(self.confirm_btn)
        layout.addWidget(btn_widget)

        # 初始化显示状态
        self.on_type_changed()

    def on_type_changed(self):
        """切换服务端类型时显示/隐藏对应路径框"""
        server_type = self.server_type_combo.currentData()
        self.go_group.setVisible(server_type == "go")
        self.python_group.setVisible(server_type == "python")

    def browse_go_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择第三方服务端目录")
        if path:
            self.go_path_edit.setText(path.replace("/", os.sep))

    def browse_python_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择一体式服务端目录")
        if path:
            self.python_path_edit.setText(path.replace("/", os.sep))

    def browse_client_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择DNF客户端目录")
        if path:
            self.client_path_edit.setText(path.replace("/", os.sep))

    def on_confirm(self):
        """保存配置并进入首页"""
        server_type = self.server_type_combo.currentData()
        go_path = self.go_path_edit.text().strip()
        py_path = self.python_path_edit.text().strip()
        client_path = self.client_path_edit.text().strip()

        if server_type == "go" and not go_path:
            GMDialog.warning(self, "提示", "请选择第三方服务端目录")
            return
        if server_type == "python" and not py_path:
            GMDialog.warning(self, "提示", "请选择一体式服务端目录")
            return
        if not client_path:
            GMDialog.warning(self, "提示", "请选择客户端目录")
            return

        # 保存配置
        self.config.set("server_type", server_type)
        self.config.set("go_server_path", go_path)
        self.config.set("python_server_path", py_path)
        self.config.set("client_path", client_path)
        self.config.save_config()

        # 同步更新首页服务端类型标签
        if hasattr(self, "main_window") and hasattr(self.main_window, "main_page"):
            self.main_window.main_page.update_server_type_label()
            self.main_window.show_main_page()

class LogPage(QWidget):
    """操作日志页面 - 独立模块"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        # 清空日志按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                font-size: 13px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #4a4a4a; }
        """)
        clear_btn.clicked.connect(self.clear_log)
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        # 日志条数统计
        self.log_count_label = QLabel("共 0 条日志")
        self.log_count_label.setStyleSheet("color: #888888; font-size: 12px; background-color: transparent;")
        toolbar.addWidget(self.log_count_label)
        
        layout.addLayout(toolbar)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #b0b0b0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                font-size: 12px;
                font-family: Consolas, monospace;
            }
        """)
        layout.addWidget(self.log_text)
    
    def append_log(self, message):
        """追加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(log_line + "\n")
        self.log_text.setTextCursor(cursor)
        
        # 更新条数
        count = self.log_text.document().blockCount() - 1
        self.log_count_label.setText(f"共 {count} 条日志")
        
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_count_label.setText("共 0 条日志")

# ========== 存档管理页面 ==========
class ArchivePage(QWidget):
    """存档管理页面 - 独立模块"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        # 统一按钮样式
        archive_btn_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #4a4a4a; }
        """
        
        # 创建存档按钮
        create_btn = QPushButton("创建存档")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(archive_btn_style)
        create_btn.clicked.connect(self.create_archive)
        toolbar.addWidget(create_btn)
        
        # 恢复存档按钮
        restore_btn = QPushButton("恢复存档")
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.setStyleSheet(archive_btn_style)
        restore_btn.clicked.connect(self.restore_archive)
        toolbar.addWidget(restore_btn)
        
        # 删除存档按钮
        delete_btn = QPushButton("删除存档")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(archive_btn_style)
        delete_btn.clicked.connect(self.delete_archive)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        # 自动备份设置
        self.auto_backup_checkbox = QCheckBox("关闭服务端时自动备份")
        self.auto_backup_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 13px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
        """)
        self.auto_backup_checkbox.setChecked(self.config.get("auto_backup_on_stop", False))
        self.auto_backup_checkbox.stateChanged.connect(self.on_auto_backup_changed)
        toolbar.addWidget(self.auto_backup_checkbox)
        
        layout.addLayout(toolbar)
        
        # 存档列表
        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(4)
        self.archive_table.setHorizontalHeaderLabels(["存档名称", "创建时间", "大小", "备注"])
        self.archive_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                font-size: 12px;
                gridline-color: #2a2a2a;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #1a2a4a;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #cccccc;
                border: none;
                border-bottom: 1px solid #3a3a3a;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.archive_table.horizontalHeader().setStretchLastSection(True)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.archive_table)
        
        # 加载存档列表
        self.load_archives()
    
    def load_archives(self):
        """加载存档列表"""
        self.archive_table.setRowCount(0)
        
        # 获取存档目录
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
        else:
            server_path = self.config.get("python_server_path", "")
        
        if not server_path:
            return
        
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
        if not os.path.exists(backup_dir):
            return
        
        # 遍历存档文件
        archives = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.db') or filename.endswith('.sqlite') or filename.endswith('.bak'):
                filepath = os.path.join(backup_dir, filename)
                stat = os.stat(filepath)
                size_mb = stat.st_size / (1024 * 1024)
                create_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                archives.append({
                    'name': filename,
                    'time': create_time,
                    'size': f"{size_mb:.2f} MB",
                    'path': filepath
                })
        
        # 按创建时间倒序排列
        archives.sort(key=lambda x: x['time'], reverse=True)
        
        # 添加到表格
        for archive in archives:
            row = self.archive_table.rowCount()
            self.archive_table.insertRow(row)
            self.archive_table.setItem(row, 0, QTableWidgetItem(archive['name']))
            self.archive_table.setItem(row, 1, QTableWidgetItem(archive['time']))
            self.archive_table.setItem(row, 2, QTableWidgetItem(archive['size']))
            self.archive_table.setItem(row, 3, QTableWidgetItem(""))
    
    def create_archive(self):
        """创建存档"""
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
            self.main_window.main_page.log("开始创建存档...")
            # TODO: 实现存档创建逻辑
            GMDialog.information(self, "提示", "存档功能开发中...")
    
    def restore_archive(self):
        """恢复存档"""
        selected_rows = self.archive_table.selectedItems()
        if not selected_rows:
            GMDialog.warning(self, "提示", "请先选择要恢复的存档")
            return
        
        archive_name = selected_rows[0].text()
        reply = GMDialog.question(self, "确认恢复", 
                                       f"确定要恢复存档「{archive_name}」吗？\n此操作将覆盖当前数据！",
                                       QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"正在恢复存档: {archive_name}")
                # TODO: 实现存档恢复逻辑
                GMDialog.information(self, "提示", "存档恢复功能开发中...")
    
    def delete_archive(self):
        """删除存档"""
        selected_rows = self.archive_table.selectedItems()
        if not selected_rows:
            GMDialog.warning(self, "提示", "请先选择要删除的存档")
            return
        
        archive_name = selected_rows[0].text()
        reply = GMDialog.question(self, "确认删除", 
                                       f"确定要删除存档「{archive_name}」吗？\n此操作不可恢复！",
                                       QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # TODO: 实现存档删除逻辑
            self.load_archives()
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"已删除存档: {archive_name}")
    
    def on_auto_backup_changed(self, state):
        """自动备份设置改变"""
        self.config.set("auto_backup_on_stop", state == Qt.Checked)
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
            if state == Qt.Checked:
                self.main_window.main_page.log("已开启关闭服务端时自动备份")
            else:
                self.main_window.main_page.log("已关闭关闭服务端时自动备份")

# ========== 账号登录弹窗 ==========
class LoginDialog(QDialog):
    """账号登录弹窗 - 独立弹出窗口"""
    
    login_success = pyqtSignal(str, str)  # account, password
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.setWindowTitle("账号登录")
        self.setFixedSize(360, 280)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui()
    
    def init_ui(self):
        # 主容器
        main_container = QWidget()
        main_container.setStyleSheet("""
            background-color: #2a2a2a;
            border: 1px solid #444444;
            border-radius: 8px;
        """)
        
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet("""
            background-color: #202020;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            border-bottom: 1px solid #3a3a3a;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 8, 0)
        
        title_label = QLabel("账号登录")
        title_label.setStyleSheet("color: #cccccc; font-size: 14px; font-weight: bold; background-color: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888888; border: none; font-size: 12px; border-radius: 4px; }
                    """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(12)
        
        # 账号输入
        account_label = QLabel("账号")
        account_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent;")
        content_layout.addWidget(account_label)
        
        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("请输入账号")
        self.account_edit.setText(self.config.get("last_account", ""))
        self.account_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """)
        content_layout.addWidget(self.account_edit)
        
        # 密码输入
        password_label = QLabel("密码")
        password_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent;")
        content_layout.addWidget(password_label)
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(self.account_edit.styleSheet())
        content_layout.addWidget(self.password_edit)
        
        content_layout.addSpacing(8)

        # 登录按钮
        login_btn = QPushButton("登录")
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setFixedHeight(36)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        login_btn.clicked.connect(self.on_login)
        content_layout.addWidget(login_btn)

        self.setLayout(main_layout)

    def on_login(self):
        account = self.account_edit.text().strip()
        password = self.password_edit.text().strip()
        if not account:
            return
        self.config.set("last_account", account)
        self.login_success.emit(account, password)
        self.accept()

    def get_credentials(self):
        return self.account_edit.text().strip(), self.password_edit.text().strip()


# ========== 登录页面（旧版，弃用保留） ==========
class LoginPage(QWidget):
    """登录页面 - 旧版独立页面，当前由首页内嵌登录表单替代，保留兼容"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.main_window = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        layout.addStretch()

        title = QLabel("账号登录")
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; background-color: transparent;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        input_style = """
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 10px 14px;
                font-size: 14px;
                min-height: 28px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """

        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("请输入账号")
        self.account_edit.setText(self.config.get("last_account", ""))
        self.account_edit.setStyleSheet(input_style)
        layout.addWidget(self.account_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(input_style)
        layout.addWidget(self.password_edit)

        layout.addSpacing(10)

        self.login_btn = QPushButton("登录并启动游戏")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        self.login_btn.clicked.connect(self.on_login)
        layout.addWidget(self.login_btn)

        layout.addStretch()

    def on_login(self):
        account = self.account_edit.text().strip()
        password = self.password_edit.text().strip()
        if not account:
            GMDialog.warning(self, "提示", "请输入账号")
            return
        if not password:
            GMDialog.warning(self, "提示", "请输入密码")
            return
        self.config.set("last_account", account)
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
            self.main_window.main_page.do_login(account, password)


# ========== 服务端状态检测线程 ==========
class StatusCheckThread(QThread):
    """后台服务端状态检测线程"""
    status_updated = pyqtSignal(bool, bool, bool)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        while self._running:
            try:
                go_running = ServerStatusChecker.check_go_server()
                python_running = ServerStatusChecker.check_python_server()
                mysql_running = ServerStatusChecker.check_mysql()
                self.status_updated.emit(go_running, python_running, mysql_running)
            except Exception:
                pass
            self.msleep(3000)

    def stop(self):
        self._running = False
        self.wait(1000)


# ========== 启动游戏后台线程 ==========
class LaunchGameWorker(QThread):
    """启动游戏后台线程"""
    log_message = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, server_type, server_path, client_path, account, password):
        super().__init__()
        self.server_type = server_type
        self.server_path = server_path
        self.client_path = client_path
        self.account = account
        self.password = password

    def log(self, msg):
        self.log_message.emit(msg)

    def run(self):
        try:
            self.log("正在检查服务端状态...")
            server_running = ServerStatusChecker.check_go_server() or ServerStatusChecker.check_python_server()
            if not server_running:
                self.log("服务端未启动，正在启动服务端...")
                self._start_server()
                import time as _time
                for i in range(20):
                    _time.sleep(1.5)
                    if ServerStatusChecker.check_go_server() or ServerStatusChecker.check_python_server():
                        break
                else:
                    self.finished_signal.emit(False, "服务端启动失败，请检查服务端目录配置")
                    return
            self.log("服务端已就绪")

            self.log("正在启动客户端...")
            dnf_exe = os.path.join(self.client_path, "DNF.exe")
            if not os.path.exists(dnf_exe):
                self.finished_signal.emit(False, f"未找到DNF.exe: {dnf_exe}")
                return

            proc = subprocess.Popen(
                [dnf_exe, "-username", self.account, "-password-stdin", "-multi-instance"],
                cwd=self.client_path,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            try:
                proc.stdin.write((self.password + "\n").encode("utf-8"))
                proc.stdin.flush()
                proc.stdin.close()
            except Exception:
                pass

            self.log("游戏启动成功")
            self.finished_signal.emit(True, "游戏启动成功")
        except Exception as e:
            self.finished_signal.emit(False, f"启动游戏异常: {e}")

    def _start_server(self):
        try:
            if self.server_type == "python":
                exe_path = os.path.join(self.server_path, "game_server.exe")
                if os.path.exists(exe_path):
                    subprocess.Popen([exe_path], cwd=self.server_path,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                control_exe = os.path.join(self.server_path, "runtime", "bin", "DNF90Control.exe")
                if os.path.exists(control_exe):
                    subprocess.Popen([control_exe, "start"], cwd=self.server_path,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    control_bat = os.path.join(self.server_path, "deploy", "windows", "control.bat")
                    if os.path.exists(control_bat):
                        subprocess.Popen(["cmd", "/c", control_bat, "start"], cwd=self.server_path,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            self.log(f"启动服务端异常: {e}")


# ========== 主页面 ==========

class SettingsWindow(QWidget):
    """服务端设置独立窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(360, 480)
        self.init_ui()
        self._refresh_current_server_label()

    def init_ui(self):
        # 主容器（圆角背景）
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 360, 480)
        self.container.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(8)

        # 标题栏（一体式，与内容区同色无分割线）
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet("""
            background-color: #2a2a2a;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 8, 0)
        title_label = QLabel("服务端设置")
        title_label.setStyleSheet("color: #cccccc; font-size: 14px; font-weight: bold; background-color: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(28, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton#closeBtn { background-color: transparent; color: #999999; border: none; font-size: 14px; border-radius: 4px; }
            QPushButton#closeBtn:hover { background-color: #c42b1c; color: #ffffff; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        layout.addWidget(title_bar)

        small_label_style = "color: #888888; font-size: 11px; background-color: transparent;"
        path_label_style = "color: #b0b0b0; font-size: 12px; background-color: transparent;"
        path_edit_style = """
            QLineEdit {
                background-color: #1a1a1a; color: #ffffff; border: 1px solid #3a3a3a;
                border-radius: 4px; padding: 6px 10px; font-size: 12px; min-height: 20px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """
        browse_btn_style = """
            QPushButton {
                background-color: #333333; color: #e0e0e0; border: none;
                border-radius: 4px; padding: 6px 14px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #444444; }
        """

        # 当前服务端路径
        self.current_server_label = QLabel()
        self.current_server_label.setStyleSheet(small_label_style)
        self.current_server_label.setWordWrap(True)
        layout.addWidget(self.current_server_label)
        layout.addSpacing(4)

        # 客户端路径
        client_label = QLabel("客户端路径")
        client_label.setStyleSheet(path_label_style)
        layout.addWidget(client_label)
        client_row = QWidget()
        client_row_layout = QHBoxLayout(client_row)
        client_row_layout.setContentsMargins(0, 0, 0, 0)
        client_row_layout.setSpacing(6)
        self.client_path_edit = QLineEdit()
        self.client_path_edit.setPlaceholderText("请选择 dnf.exe 所在目录")
        self.client_path_edit.setText(self.config.get("client_path", ""))
        self.client_path_edit.setStyleSheet(path_edit_style)
        client_row_layout.addWidget(self.client_path_edit, 1)
        self.client_browse_btn = QPushButton("浏览")
        self.client_browse_btn.setCursor(Qt.PointingHandCursor)
        self.client_browse_btn.setStyleSheet(browse_btn_style)
        self.client_browse_btn.clicked.connect(self.on_client_browse)
        client_row_layout.addWidget(self.client_browse_btn)
        layout.addWidget(client_row)
        client_hint = QLabel("请选择 dnf.exe 所在目录")
        client_hint.setStyleSheet(small_label_style)
        layout.addWidget(client_hint)
        layout.addSpacing(4)

        # 服务端路径
        server_label = QLabel("服务端路径")
        server_label.setStyleSheet(path_label_style)
        layout.addWidget(server_label)
        server_row = QWidget()
        server_row_layout = QHBoxLayout(server_row)
        server_row_layout.setContentsMargins(0, 0, 0, 0)
        server_row_layout.setSpacing(6)
        self.server_path_edit = QLineEdit()
        self.server_path_edit.setPlaceholderText("请选择服务端根目录")
        server_type = self.config.get("server_type", "go")
        default_server = self.config.get("go_server_path" if server_type == "go" else "python_server_path", "")
        self.server_path_edit.setText(default_server)
        self.server_path_edit.setStyleSheet(path_edit_style)
        server_row_layout.addWidget(self.server_path_edit, 1)
        self.server_browse_btn = QPushButton("浏览")
        self.server_browse_btn.setCursor(Qt.PointingHandCursor)
        self.server_browse_btn.setStyleSheet(browse_btn_style)
        self.server_browse_btn.clicked.connect(self.on_server_browse)
        server_row_layout.addWidget(self.server_browse_btn)
        layout.addWidget(server_row)
        server_hint = QLabel("请选择服务端根目录（包含 runtime、deploy 等文件夹）")
        server_hint.setStyleSheet(small_label_style)
        layout.addWidget(server_hint)
        layout.addSpacing(6)

        # 确认按钮
        self.confirm_path_btn = QPushButton("确认")
        self.confirm_path_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_path_btn.setFixedHeight(32)
        self.confirm_path_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: #fff; border: none;
                border-radius: 4px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        self.confirm_path_btn.clicked.connect(self.on_confirm_path)

        # 安装客户端补丁按钮
        self.install_patch_left_btn = QPushButton("安装客户端补丁")
        self.install_patch_left_btn.setCursor(Qt.PointingHandCursor)
        self.install_patch_left_btn.setFixedHeight(32)
        self.install_patch_left_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #fff; border: none;
                border-radius: 4px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #444444; }
        """)
        self.install_patch_left_btn.clicked.connect(self.on_install_patch_clicked)

        # 确认和安装补丁并列
        left_btn_row = QHBoxLayout()
        left_btn_row.setContentsMargins(0, 0, 0, 0)
        left_btn_row.setSpacing(8)
        left_btn_row.addWidget(self.confirm_path_btn, 1)
        left_btn_row.addWidget(self.install_patch_left_btn, 1)
        layout.addLayout(left_btn_row)
        layout.addSpacing(4)

        # 底部弹簧
        layout.addStretch()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.container.setGeometry(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_pos'):
            del self._drag_pos

    def _refresh_current_server_label(self):
        server_type = self.config.get("server_type", "go")
        path = self.config.get("go_server_path" if server_type == "go" else "python_server_path", "")
        type_name = "第三方服务端" if server_type == "go" else "一体式服务端"
        self.current_server_label.setText(f"当前服务端: {path}" if path else f"当前服务端: 未设置（{type_name}）")

    def on_client_browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择DNF客户端目录")
        if path:
            self.client_path_edit.setText(path.replace("/", os.sep))

    def on_server_browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择服务端根目录")
        if path:
            self.server_path_edit.setText(path.replace("/", os.sep))

    def on_confirm_path(self):
        client_path = self.client_path_edit.text().strip()
        server_path = self.server_path_edit.text().strip()
        server_type = self.config.get("server_type", "go")
        if not client_path or not server_path:
            return
        self.config.set("client_path", client_path)
        if server_type == "go":
            self.config.set("go_server_path", server_path)
        else:
            self.config.set("python_server_path", server_path)
        self.config.save_config()
        self._refresh_current_server_label()

    def on_install_patch_clicked(self):
        self.left_log("安装客户端补丁功能开发中...")


class MainPage(QWidget):
    """主页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.launch_worker = None
        self.init_ui()
        self.start_status_timer()


    def _add_form_field(self, parent_layout, label_text, edit_name, placeholder, password=False):
        """添加表单项到布局"""
        label = QLabel(label_text)
        label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent;")
        parent_layout.addWidget(label)
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        if edit_name == "account":
            edit.setText(self.config.get("last_account", ""))
        if password:
            edit.setEchoMode(QLineEdit.Password)
        edit.setStyleSheet(STYLES["line_edit"])
        setattr(self, edit_name, edit)
        parent_layout.addWidget(edit)

    def _create_primary_button(self, text, on_click, min_width=0):
        """创建主按钮"""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(36)
        if min_width:
            btn.setMinimumWidth(min_width)
        btn.setStyleSheet(STYLES["primary"])
        btn.clicked.connect(on_click)
        return btn

    def _create_secondary_button(self, text, on_click):
        """创建次按钮"""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setStyleSheet(STYLES["dark"])
        btn.clicked.connect(on_click)
        return btn

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 顶部：服务端类型标签（右上角）
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch()

        self.server_type_label = QLabel()
        self.server_type_label.setStyleSheet("""
            color: #888888;
            font-size: 12px;
            background-color: transparent;
            border: none;
        """)
        self.server_type_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(self.server_type_label)

        # 设置按钮（抽屉开关）
        self.settings_toggle_btn = QPushButton("设置")
        self.settings_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.settings_toggle_btn.setFixedSize(60, 28)
        self.settings_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #444444; }
        """)
        self.settings_toggle_btn.clicked.connect(self.open_settings_window)
        top_layout.addWidget(self.settings_toggle_btn)
        top_layout.addSpacing(8)

        main_layout.addWidget(top_widget)

        # 隐藏的状态标签对象
        self.server_status_label = QLabel("服务端状态: 检测中...")
        self.server_status_label.setVisible(False)
        self.mysql_status_label = QLabel("MySQL状态: 检测中...")
        self.mysql_status_label.setVisible(False)

        # 主体：单栏布局，贴右
        body_widget = QWidget()
        body_outer = QHBoxLayout(body_widget)
        body_outer.setContentsMargins(0, 0, 0, 0)

        center_widget = QWidget()
        body_layout = QVBoxLayout(center_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        # 账号/密码输入框（使用辅助方法）
        self._add_form_field(body_layout, "账号", "account", "请输入账号")
        self._add_form_field(body_layout, "密码", "password", "请输入密码", password=True)

        body_layout.addSpacing(6)

        # 功能按钮（使用辅助方法创建）
        self.login_btn = self._create_primary_button("登录", self.on_login_clicked)
        self.register_btn = self._create_secondary_button("注册", self.on_register_clicked)
        self.install_patch_btn = self._create_secondary_button("打开GM工具", self.on_install_patch_clicked)
        self.start_server_btn = self._create_secondary_button("启动", self.start_server)
        self.stop_server_btn = self._create_secondary_button("停止", self.stop_server)
        self.stop_server_btn.setEnabled(False)

        # 功能按钮：两列网格分布
        func_grid = QGridLayout()
        func_grid.setContentsMargins(0, 0, 0, 0)
        func_grid.setHorizontalSpacing(10)
        func_grid.setVerticalSpacing(10)
        func_grid.setColumnStretch(0, 1)
        func_grid.setColumnStretch(1, 1)

        # 行0：注册 | 登录
        func_grid.addWidget(self.register_btn, 0, 0)
        func_grid.addWidget(self.login_btn, 0, 1)

        # 行1：启动 | 停止
        func_grid.addWidget(self.start_server_btn, 1, 0)
        func_grid.addWidget(self.stop_server_btn, 1, 1)

        # 行2：打开GM工具（跨两列）
        func_grid.addWidget(self.install_patch_btn, 2, 0, 1, 2)

        # 所有按钮等宽填充单元格（必须在按钮创建之后）
        for _btn in [self.register_btn, self.login_btn, self.start_server_btn, self.stop_server_btn, self.install_patch_btn]:
            _btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        body_layout.addLayout(func_grid)

        body_layout.addStretch()

        # 登录区居中
        body_outer.addStretch()
        body_outer.addWidget(center_widget)
        body_outer.addStretch()

        main_layout.addWidget(body_widget, 1)

        # 隐藏的日志对象（用于内部记录，不显示在首页）
        self.log_text = QTextEdit()
        self.log_text.setVisible(False)

        self.update_server_type_label()

    def open_settings_window(self):
        """打开服务端设置独立窗口"""
        if not hasattr(self, '_settings_window') or self._settings_window is None:
            self._settings_window = SettingsWindow(self)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def update_server_type_label(self):
        """更新服务端类型标签"""
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            self.server_type_label.setText("第三方服务端")
        else:
            self.server_type_label.setText("一体式服务端")

    def on_register_clicked(self):
        """注册按钮（占位）"""
        GMDialog.information(self, "提示", "注册功能开发中，敬请期待")

    def on_install_patch_clicked(self):
        """安装客户端补丁按钮（占位）"""
        GMDialog.information(self, "提示", "安装客户端补丁功能开发中，敬请期待")

    def on_login_clicked(self):
        """登录按钮点击 - 直接从右侧表单获取账号密码"""
        account = self.account_edit.text().strip()
        password = self.password_edit.text().strip()

        if not account:
            GMDialog.warning(self, "提示", "请输入账号")
            return
        if not password:
            GMDialog.warning(self, "提示", "请输入密码")
            return

        # 保存账号
        self.config.set("last_account", account)
        self.do_login(account, password)

    def do_login(self, account, password):
        """执行登录"""
        self.log(f"账号登录: {account}")

        # 获取服务端和客户端路径
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
        else:
            server_path = self.config.get("python_server_path", "")
        client_path = self.config.get("client_path", "")

        if not server_path:
            GMDialog.warning(self, "提示", "服务端路径未配置，请先设置路径")
            return
        if not client_path:
            GMDialog.warning(self, "提示", "客户端路径未配置，请先设置路径")
            return

        # 使用后台线程启动游戏
        self.launch_worker = LaunchGameWorker(server_type, server_path, client_path, account, password)
        self.launch_worker.log_message.connect(self.log)
        self.launch_worker.finished_signal.connect(self.on_launch_finished)
        self.launch_worker.start()

    def on_launch_finished(self, success, message):
        """启动完成回调"""
        if success:
            self.log(f"启动完成: {message}")
        else:
            self.log(f"启动失败: {message}")
            GMDialog.warning(self, "错误", f"启动游戏失败:\n{message}")

    def start_status_timer(self):
        """启动后台状态检测线程"""
        self.status_thread = StatusCheckThread()
        self.status_thread.status_updated.connect(self.on_status_updated)
        self.status_thread.start()
        QTimer.singleShot(100, self.check_status_once)

    def check_status_once(self):
        """立即检测一次状态"""
        try:
            server_running = ServerStatusChecker.check_go_server() or ServerStatusChecker.check_python_server()
            mysql_running = ServerStatusChecker.check_mysql()
            self.on_status_updated(server_running, server_running, mysql_running)
        except Exception:
            pass

    def on_status_updated(self, go_running, python_running, mysql_running):
        """状态更新回调"""
        server_running = go_running or python_running
        # 更新侧边栏状态
        if hasattr(self, 'main_window'):
            if hasattr(self.main_window, 'nav_server_status'):
                self.main_window.nav_server_status.setText(
                    "服务端: 运行中" if server_running else "服务端: 未启动")
            if hasattr(self.main_window, 'nav_mysql_status'):
                self.main_window.nav_mysql_status.setText(
                    "MySQL: 运行中" if mysql_running else "MySQL: 未启动")
        # 更新按钮状态
        self.stop_server_btn.setEnabled(server_running)
        self.start_server_btn.setEnabled(not server_running)

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(log_line + "\n")
        # 同时向独立日志页面发送日志
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'log_page'):
            self.main_window.log_page.append_log(message)

    def start_server(self):
        """启动服务端"""
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
            self.log(f"正在启动第三方服务端: {server_path}")
            control_exe = os.path.join(server_path, "runtime", "bin", "DNF90Control.exe")
            if os.path.exists(control_exe):
                try:
                    subprocess.Popen([control_exe, "start"], cwd=server_path,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log("服务端启动命令已发送")
                except Exception as e:
                    self.log(f"启动失败: {e}")
            else:
                self.log(f"未找到 DNF90Control.exe: {control_exe}")
        else:
            server_path = self.config.get("python_server_path", "")
            self.log(f"正在启动一体式服务端: {server_path}")
            exe_path = os.path.join(server_path, "game_server.exe")
            if os.path.exists(exe_path):
                try:
                    subprocess.Popen([exe_path], cwd=server_path,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                    self.log("一体式服务端启动命令已发送")
                except Exception as e:
                    self.log(f"启动失败: {e}")
            else:
                self.log(f"未找到 game_server.exe: {exe_path}")

    def stop_server(self):
        """停止服务端"""
        self.log("正在停止服务端...")
        for process_name in ["DNF90Server.exe", "game_server.exe", "mysqld.exe", "DNF90Control.exe"]:
            try:
                subprocess.run(["taskkill", "/F", "/IM", process_name], capture_output=True)
            except Exception:
                pass
        self.log("服务端停止命令已发送")

    def show_settings(self):
        """显示设置页面"""
        if hasattr(self, 'main_window'):
            self.main_window.show_path_setup_page()


# ========== 主窗口 ==========
class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.init_window()
        self.init_ui()
    
    def init_window(self):
        """初始化窗口 - 16:10比例"""
        self.setWindowTitle(APP_NAME)
        self.resize(960, 600)
        self.setMinimumSize(800, 500)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 窗口拖动
        self.dragging = False
        self.drag_position = QPoint()
    
    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        try:
            # 停止后台状态检测线程
            if hasattr(self, 'main_page') and hasattr(self.main_page, 'status_thread'):
                self.main_page.status_thread.stop()
            
            # 保存配置
            if hasattr(self, 'config'):
                self.config.save_config()
        except Exception as e:
            print(f"关闭时清理异常: {e}")
        
        event.accept()
    
    def init_ui(self):
        """初始化UI - GM工具风格，16:10比例"""
        # 主容器
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== 标题栏（无文字） ==========
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 8, 0)
        title_layout.setSpacing(8)
        
        # 返回按钮
        self.back_btn = QPushButton("←")
        self.back_btn.setObjectName("titleBtn")
        self.back_btn.setFixedSize(28, 24)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setToolTip("返回")
        self.back_btn.clicked.connect(self.go_back)
        title_layout.addWidget(self.back_btn)
        
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(28, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        # 双击标题栏最小化
        title_bar.mouseDoubleClickEvent = self.on_title_double_click
        
        main_layout.addWidget(title_bar)
        
        # ========== 内容区域（侧边栏 + 主内容） ==========
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 侧边栏
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(180)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)
        
        # 导航按钮（最后两个始终为操作日志和服务端设置）
        self.nav_buttons = []
        nav_items = [
            ("首页", "home"),
            ("存档管理", "archive"),
            ("操作日志", "log"),
            ("服务端设置", "settings"),
        ]
        
        for text, key in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("page_id", key)
            btn.clicked.connect(lambda checked, k=key: self.switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        sidebar_layout.addStretch()
        
        # 服务端状态
        self.nav_server_status = QLabel("服务端: 检测中...")
        self.nav_server_status.setObjectName("statusLabel")
        self.nav_server_status.setAlignment(Qt.AlignCenter)
        self.nav_server_status.setWordWrap(True)
        sidebar_layout.addWidget(self.nav_server_status)
        
        # MySQL状态
        self.nav_mysql_status = QLabel("MySQL: 检测中...")
        self.nav_mysql_status.setObjectName("statusLabel")
        self.nav_mysql_status.setAlignment(Qt.AlignCenter)
        self.nav_mysql_status.setWordWrap(True)
        sidebar_layout.addWidget(self.nav_mysql_status)
        
        sidebar_layout.addSpacing(8)
        
        # 重启服务端按钮（状态标签下方，居中显示，向右微调20px）
        restart_widget = QWidget()
        restart_widget.setStyleSheet("background-color: transparent;")
        restart_layout = QHBoxLayout(restart_widget)
        restart_layout.setContentsMargins(20, 0, 0, 0)  # 整体向右偏移20px
        restart_layout.addStretch()
        
        self.restart_server_btn = QPushButton("重启服务端")
        self.restart_server_btn.setObjectName("navBtn")
        self.restart_server_btn.setCursor(Qt.PointingHandCursor)
        self.restart_server_btn.setFixedWidth(120)
        self.restart_server_btn.clicked.connect(self.restart_server)
        restart_layout.addWidget(self.restart_server_btn)
        
        restart_layout.addStretch()
        sidebar_layout.addWidget(restart_widget)
        
        content_layout.addWidget(self.sidebar)
        
        # 主内容区域
        self.content_area = QWidget()
        self.content_area.setObjectName("contentArea")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # 内容区域标题栏
        self.content_title_bar = QWidget()
        self.content_title_bar.setFixedHeight(48)
        self.content_title_bar.setStyleSheet("background-color: #202020; border-bottom: 1px solid #3a3a3a;")
        title_layout2 = QHBoxLayout(self.content_title_bar)
        title_layout2.setContentsMargins(20, 0, 20, 0)
        
        self.content_title = QLabel("首页")
        self.content_title.setStyleSheet("color: #cccccc; font-size: 16px; font-weight: bold; background-color: transparent;")
        title_layout2.addWidget(self.content_title)
        title_layout2.addStretch()
        
        self.content_layout.addWidget(self.content_title_bar)
        
        # 堆叠页面
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent; border: none;")
        
        self.path_setup_page = PathSetupPage()
        self.path_setup_page.main_window = self
        self.stacked_widget.addWidget(self.path_setup_page)
        
        self.main_page = MainPage()
        self.main_page.main_window = self
        self.stacked_widget.addWidget(self.main_page)
        
        self.log_page = LogPage()
        self.log_page.main_window = self
        self.stacked_widget.addWidget(self.log_page)
        
        self.archive_page = ArchivePage()
        self.archive_page.main_window = self
        self.stacked_widget.addWidget(self.archive_page)
        
        self.login_page = LoginPage()
        self.login_page.main_window = self
        self.stacked_widget.addWidget(self.login_page)
        
        self.content_layout.addWidget(self.stacked_widget)
        content_layout.addWidget(self.content_area)
        
        main_layout.addWidget(content_widget)
        
        # ========== 底部状态栏 ==========
        status_bar = QWidget()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(30)
        
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)
        
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("statusLabel")
        status_layout.addWidget(self.datetime_label)
        
        main_layout.addWidget(status_bar)
        
        # 启动日期时间更新定时器
        self.datetime_timer = QTimer()
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)  # 每秒更新
        self.update_datetime()  # 立即更新一次
        
        # 设置中央widget
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(self.main_container)
        self.setCentralWidget(central_widget)
        
        # 窗口拖动（通过标题栏）
        self.dragging = False
        self.drag_position = QPoint()
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseReleaseEvent = self.title_bar_mouse_release
        
        # 检查是否已配置路径
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            has_path = bool(self.config.get("go_server_path", ""))
        else:
            has_path = bool(self.config.get("python_server_path", ""))
        
        if has_path and self.config.get("client_path", ""):
            self.show_main_page()
        else:
            self.show_path_setup_page()
    
    def on_title_double_click(self, event):
        """双击标题栏最小化"""
        self.showMinimized()
    
    def update_datetime(self):
        """更新底部状态栏的日期时间"""
        now = datetime.now()
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_label.setText(datetime_str)
    
    def title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def title_bar_mouse_move(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def title_bar_mouse_release(self, event):
        self.dragging = False
    
    def title_bar_double_click(self, event):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def switch_page(self, page_id):
        if page_id == "home": self.show_main_page()
        elif page_id == "log": self.show_log_page()
        elif page_id == "archive": self.show_archive_page()
        elif page_id == "settings": self.show_path_setup_page()
    
    def go_back(self):
        # 返回按钮总是回到首页
        self.show_main_page()
    
    def update_nav_active(self):
        current = self.stacked_widget.currentIndex()
        page_ids = ["settings", "home", "log", "archive"]
        if current < len(page_ids):
            current_id = page_ids[current]
            for btn in self.nav_buttons:
                is_active = btn.property("page_id") == current_id
                btn.setProperty("class", "active" if is_active else "")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            titles = {"home": "首页", "log": "操作日志", "archive": "存档管理", "settings": "服务端设置"}
            if current_id in titles:
                self.content_title.setText(titles[current_id])
            # 返回按钮：首页和路径设置页隐藏，其他页面显示
            if hasattr(self, "back_btn"):
                self.back_btn.setVisible(current_id not in ("home", "settings"))
    
    def show_path_setup_page(self):
        self.stacked_widget.setCurrentWidget(self.path_setup_page)
        self.update_nav_active()
    
    def show_main_page(self):
        self.stacked_widget.setCurrentWidget(self.main_page)
        self.update_nav_active()
        self.main_page.log("启动器已就绪")
    
    def show_log_page(self):
        self.stacked_widget.setCurrentWidget(self.log_page)
        self.update_nav_active()
    
    def show_archive_page(self):
        self.stacked_widget.setCurrentWidget(self.archive_page)
        self.update_nav_active()
        self.archive_page.load_archives()
    
    def show_login_page(self):
        self.stacked_widget.setCurrentWidget(self.login_page)
        self.update_nav_active()
    
    def restart_server(self):
        """重启服务端"""
        if hasattr(self, 'main_page'):
            self.main_page.log("正在重启服务端...")
            # 先停止服务端
            self.main_page.stop_server()
            # 延迟2秒后启动服务端
            QTimer.singleShot(2000, self.main_page.start_server)

# ========== 主函数 ==========
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # 设置全局字体 - Noto Sans SC
    font = QFont("Noto Sans SC", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    # 设置全局GM工具风格样式
    app.setStyleSheet("""
        QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: "Noto Sans SC", "Microsoft YaHei";
            font-size: 13px;
        }
        
        QLabel { background-color: transparent; }
        QCheckBox { background-color: transparent; }
        QMainWindow { background-color: transparent; }
        
        QToolTip {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #444444;
            padding: 4px 8px;
            border-radius: 4px;
        }
        
        QPushButton {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 13px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        QPushButton:pressed {
            background-color: #4a4a4a;
        }
        QPushButton:disabled {
            background-color: #1a1a1a;
            color: #555555;
            border-color: #2a2a2a;
        }
        
        QLineEdit {
            background-color: #1a1a1a;
            color: #ffffff;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: #2a5a9a;
        }
        QLineEdit:focus { border-color: #4a90d9; }
        QLineEdit:disabled {
            background-color: #151515;
            color: #555555;
        }
        
        QComboBox {
            background-color: #1a1a1a;
            color: #ffffff;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 13px;
        }
        QComboBox:hover { border-color: #4a90d9; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView {
            background-color: #1a1a1a;
            color: #ffffff;
            selection-background-color: #2a5a9a;
            border: 1px solid #3a3a3a;
            outline: none;
        }
        
        QGroupBox {
            background-color: transparent;
            color: #cccccc;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 16px;
            font-size: 12px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        
        QTextEdit {
            background-color: #151515;
            color: #b0b0b0;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 12px;
        }
        
        QProgressBar {
            background-color: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            text-align: center;
            color: #cccccc;
        }
        QProgressBar::chunk {
            background-color: #4a90d9;
            border-radius: 3px;
        }
        
        QScrollBar:vertical {
            background-color: transparent;
            width: 8px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background-color: #3a3a3a;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background-color: #4a4a4a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background-color: transparent;
            height: 8px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background-color: #3a3a3a;
            border-radius: 4px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover { background-color: #4a4a4a; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555555;
            border-radius: 3px;
            background-color: transparent;
        }
        QCheckBox::indicator:hover { border-color: #4a90d9; }
        QCheckBox::indicator:checked {
            background-color: #4a90d9;
            border-color: #4a90d9;
        }
        
        #mainContainer {
            background-color: #2a2a2a;
            border: 1px solid #444444;
            border-radius: 8px;
        }
        
        #titleBar {
            background-color: #202020;
            border-bottom: 1px solid #3a3a3a;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        
        #titleBtn {
            background-color: transparent;
            color: #888888;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 14px;
        }
        #titleBtn:hover {
            background-color: #3a3a3a;
            color: #ffffff;
        }
        
        #closeBtn {
            background-color: transparent;
            color: #888888;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 14px;
        }
        
        #sidebar {
            background-color: #202020;
            border-right: 1px solid #3a3a3a;
        }
        
        #navBtn {
            background-color: transparent;
            color: #cccccc;
            border: none;
            border-radius: 4px;
            padding: 10px 16px;
            text-align: left;
            font-size: 13px;
        }
        #navBtn:hover {
            background-color: #2a2a2a;
            color: #ffffff;
        }
        #navBtn.active {
            background-color: #1a2a4a;
            color: #ffffff;
            border: 1px solid #4a90d9;
        }
        
        #contentArea {
            background-color: #202020;
        }
        
        #statusBar {
            background-color: #252525;
            border-top: 1px solid #333333;
        }
        
        #statusLabel {
            color: #888888;
            font-size: 11px;
            background-color: transparent;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
