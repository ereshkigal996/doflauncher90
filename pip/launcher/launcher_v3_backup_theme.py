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
import base64
import hashlib
from datetime import datetime

from PyQt5.QtWidgets import (QGraphicsOpacityEffect, 
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox, QDialog, QFrame,
    QStackedWidget, QProgressBar, QComboBox, QTextEdit, QFileDialog,
    QSizePolicy, QGroupBox, QGridLayout, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QIcon, QFontDatabase

# 程序版本号
APP_VERSION = "3.0.0"
APP_NAME = "DNF轮回启动器"

# ========== 通用样式字典 ==========
STYLES = {
    "base_qpushbutton": """
        QPushButton {
            background-color: #2a2a2a; color: #ffffff; border: 1px solid #4a4a4a;
            border-radius: 4px; padding: 8px 12px; font-size: 14px; font-weight: bold;
        }
        QPushButton:hover { background-color: #3a3a3a; border-color: #5a5a5a; }
        QPushButton:pressed { background-color: #4a4a4a; }
        QPushButton:disabled { background-color: #1a1a1a; color: #555555; border-color: #2a2a2a; }
    """,
    "primary": """
        QPushButton {
            background-color: #0078d4; color: #ffffff; border: none;
            border-radius: 4px; font-size: 14px; padding: 6px 16px;
        }
        QPushButton:hover { background-color: #106ebe; }
        QPushButton:pressed { background-color: #005a9e; }
    """,
    "dark": """
        QPushButton {
            background-color: #333333; color: #ffffff; border: none;
            border-radius: 4px; font-size: 15px; font-weight: bold; padding: 8px 16px;
        }
        QPushButton:hover { background-color: #3d3d3d; }
        QPushButton:pressed { background-color: #444444; }
    """,
    "small_label": "color: #888888; font-size: 12px; background-color: transparent;",
    "path_label": "color: #b0b0b0; font-size: 13px; background-color: transparent;",
    "line_edit": """
        QLineEdit {
            background-color: #1a1a1a; color: #ffffff; border: 1px solid #3a3a3a;
            border-radius: 4px; padding: 8px 12px; font-size: 14px; min-height: 24px;
        }
        QLineEdit:focus { border-color: #4a90d9; }
    """,
    "close_btn": """
        QPushButton { background-color: transparent; color: #888888; border: 1px solid #444444;
            border-radius: 4px; font-size: 13px; padding: 4px 12px; }
        QPushButton:hover { background-color: #333333; border-color: #666666; color: #ffffff; }
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
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        # 配置文件放入config文件夹
        config_dir = os.path.join(base_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    def load_config(self):
        """加载配置文件"""
        config_dir = self.get_config_dir()
        self._config_path = os.path.join(config_dir, "config.lau")

        # 配置文件迁移：从旧的位置迁移到config文件夹
        old_locations = [
            os.path.join(os.path.dirname(config_dir), "config.lau"),
            os.path.join(os.path.dirname(config_dir), "launcher.lau"),
        ]
        for old_path in old_locations:
            if not os.path.exists(self._config_path) and os.path.exists(old_path):
                try:
                    shutil.copy2(old_path, self._config_path)
                    print(f"配置文件已迁移: {old_path} -> {self._config_path}")
                    break
                except Exception as e:
                    print(f"配置文件迁移失败: {e}")

        # 默认配置结构：登录器和gm工具使用独立字段
        default_config = {
            "launcher": {
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
            },
            "gmtool": {
                "server_path": "",
                "client_path": "",
                "pvf_path": "",
                "db_mode": "mysql",
                "settings": {}
            }
        }
        
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8-sig') as f:
                    loaded_config = json.load(f)
                
                # 向后兼容：如果旧配置文件顶层直接是登录器的配置，迁移到新结构
                if "launcher" not in loaded_config and "gmtool" not in loaded_config:
                    # 旧格式，迁移到launcher字段下
                    self._config = {
                        "launcher": loaded_config,
                        "gmtool": default_config["gmtool"]
                    }
                    self._dirty = True
                    self._schedule_save()
                    print("配置文件已迁移到新格式（launcher/gmtool独立字段）")
                else:
                    self._config = loaded_config
                
                # 合并默认配置（确保新字段存在）
                for key, value in default_config.items():
                    if key not in self._config:
                        self._config[key] = value
                    elif isinstance(value, dict) and isinstance(self._config[key], dict):
                        for sub_key, sub_value in value.items():
                            if sub_key not in self._config[key]:
                                self._config[key][sub_key] = sub_value
            except Exception as e:
                print(f"配置文件加载失败: {e}")
                self._config = default_config
        else:
            self._config = default_config
    
    def save_config(self):
        """立即保存配置文件"""
        if self._config_path and self._config and self._dirty:
            try:
                # 确保config文件夹存在
                config_dir = os.path.dirname(self._config_path)
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)
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
        """获取登录器配置项"""
        if self._config and "launcher" in self._config:
            return self._config["launcher"].get(key, default)
        return default
    
    def set(self, key, value):
        """设置登录器配置项（延迟保存）"""
        if self._config is not None:
            if "launcher" not in self._config:
                self._config["launcher"] = {}
            self._config["launcher"][key] = value
            self._dirty = True
            self._schedule_save()
    
    def get_gmtool(self, key, default=None):
        """获取GM工具配置项"""
        if self._config and "gmtool" in self._config:
            return self._config["gmtool"].get(key, default)
        return default
    
    def set_gmtool(self, key, value):
        """设置GM工具配置项（延迟保存）"""
        if self._config is not None:
            if "gmtool" not in self._config:
                self._config["gmtool"] = {}
            self._config["gmtool"][key] = value
            self._dirty = True
            self._schedule_save()

    # ========== 账号密码管理 ==========
    def _get_dat_path(self):
        """获取账号密码dat文件路径"""
        return os.path.join(self.get_config_dir(), "accounts.dat")

    def _encrypt_password(self, password):
        """简单加密密码（base64 + 异或）"""
        key = b"launcher_2024_secure_key"
        encrypted = bytearray()
        for i, byte in enumerate(password.encode('utf-8')):
            encrypted.append(byte ^ key[i % len(key)])
        return base64.b64encode(bytes(encrypted)).decode('utf-8')

    def _decrypt_password(self, encrypted):
        """解密密码"""
        try:
            key = b"launcher_2024_secure_key"
            decoded = base64.b64decode(encrypted.encode('utf-8'))
            decrypted = bytearray()
            for i, byte in enumerate(decoded):
                decrypted.append(byte ^ key[i % len(key)])
            return decrypted.decode('utf-8')
        except:
            return ""

    def save_account(self, username, password):
        """保存账号密码 - 只保存在dat文件中，不保存到lau文件"""
        # 密码和账号列表都存储在dat文件
        try:
            dat_path = self._get_dat_path()
            dat_data = {}
            if os.path.exists(dat_path):
                with open(dat_path, 'r', encoding='utf-8') as f:
                    dat_data = json.load(f)
            # 保存账号信息（用户名、创建时间、加密密码）
            if username not in dat_data:
                dat_data[username] = {
                    "password": self._encrypt_password(password),
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                dat_data[username]["password"] = self._encrypt_password(password)
            with open(dat_path, 'w', encoding='utf-8') as f:
                json.dump(dat_data, f, indent=4, ensure_ascii=False)
            # 只保存last_account到lau文件，不保存账号列表
            self.set("last_account", username)
        except Exception as e:
            print(f"账号密码保存失败: {e}")

    def get_accounts(self):
        """获取已保存的账号列表 - 从dat文件读取"""
        dat_path = self._get_dat_path()
        if not os.path.exists(dat_path):
            return []
        try:
            with open(dat_path, 'r', encoding='utf-8') as f:
                dat_data = json.load(f)
            accounts = []
            for username, info in dat_data.items():
                if isinstance(info, dict):
                    accounts.append({
                        "username": username,
                        "created": info.get("created", "")
                    })
                else:
                    # 兼容旧格式（直接保存加密密码字符串）
                    accounts.append({
                        "username": username,
                        "created": ""
                    })
            return accounts
        except Exception as e:
            print(f"账号列表读取失败: {e}")
            return []

    def get_password(self, username):
        """获取指定账号的密码（解密）- 从dat文件读取"""
        try:
            dat_path = self._get_dat_path()
            if os.path.exists(dat_path):
                with open(dat_path, 'r', encoding='utf-8') as f:
                    dat_data = json.load(f)
                if username in dat_data:
                    info = dat_data[username]
                    if isinstance(info, dict):
                        return self._decrypt_password(info.get("password", ""))
                    else:
                        # 兼容旧格式（直接保存加密密码字符串）
                        return self._decrypt_password(info)
        except Exception as e:
            print(f"密码读取失败: {e}")
        return ""

    def delete_account(self, username):
        """删除账号 - 从dat文件删除"""
        # 从dat文件删除账号
        try:
            dat_path = self._get_dat_path()
            if os.path.exists(dat_path):
                with open(dat_path, 'r', encoding='utf-8') as f:
                    dat_data = json.load(f)
                if username in dat_data:
                    del dat_data[username]
                with open(dat_path, 'w', encoding='utf-8') as f:
                    json.dump(dat_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"账号删除失败: {e}")
        
        # 更新last_account
        if self.get("last_account") == username:
            accounts = self.get_accounts()
            self.set("last_account", accounts[0]["username"] if accounts else "")

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
    
    def __init__(self, title="提示", parent=None, show_back=False, size=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if size:
            self.setFixedSize(size[0], size[1])
        else:
            self.setFixedSize(500, 300)
        self.dragging = False
        self.drag_position = QPoint()
        self.show_back = show_back
        self.init_ui(title)
    
    def init_ui(self, title):
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet("""
            QWidget#mainContainer {
                background-color: #1d1d1d;
                border-radius: 8px;
                border: 1px solid #333333;
            }
            QPushButton#titleBtn {
                background-color: transparent; color: #b0b0b0; border: none;
                font-size: 15px; border-radius: 4px;
            }
            QPushButton#titleBtn:hover {
                background-color: #2a2a2a; color: #ffffff;
            }
            QPushButton#closeBtn {
                background-color: transparent; color: #999999; border: none;
                font-size: 13px; font-weight: bold; border-radius: 4px;
            }
            QPushButton#closeBtn:hover {
                background-color: #c42b1c; color: #ffffff;
            }
            QPushButton#dangerBtn {
                background-color: #c42b1c; color: #ffffff; border: none;
                border-radius: 4px; font-size: 14px; padding: 6px 16px;
            }
            QPushButton#dangerBtn:hover { background-color: #a5281a; }
            QPushButton#successBtn {
                background-color: #0e6b0e; color: #ffffff; border: none;
                border-radius: 4px; font-size: 14px; padding: 6px 16px;
            }
            QPushButton#successBtn:hover { background-color: #0c5a0c; }
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
            font-size: 15px;
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
        self.content_widget.setStyleSheet("background-color: #1d1d1d; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        layout.addWidget(self.content_widget)
        
        # 按钮区域
        self.button_widget = QWidget()
        self.button_widget.setStyleSheet("background-color: #1d1d1d; border: none;")
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(10)
        self.button_layout.addStretch()
        layout.addWidget(self.button_widget)
        
        # 拖动支持
        self.main_container.mousePressEvent = self.mousePressEvent
        self.main_container.mouseMoveEvent = self.mouseMoveEvent
        self.main_container.mouseReleaseEvent = self.mouseReleaseEvent
        
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
                    border-radius: 4px; font-size: 14px; padding: 6px 16px; }
                QPushButton:hover { background-color: #106ebe; }
                QPushButton:pressed { background-color: #005a9e; }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton { background-color: #3a3a3a; color: #e0e0e0;
                    border: 1px solid #555555; border-radius: 4px; font-size: 14px; padding: 6px 16px; }
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
        msg_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        msg_label.setWordWrap(True)
        dialog.content_layout.addWidget(msg_label)
        dialog.add_button("确定", dialog.accept, "primary")
        return dialog.exec_()
    
    @staticmethod
    def warning(parent, title, message):
        """警告提示框"""
        dialog = GMDialog(title, parent)
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        msg_label.setWordWrap(True)
        dialog.content_layout.addWidget(msg_label)
        dialog.add_button("确定", dialog.accept, "primary")
        return dialog.exec_()
    
    @staticmethod
    def question(parent, title, message, buttons=QMessageBox.Yes | QMessageBox.No, size=None):
        """确认对话框"""
        dialog = GMDialog(title, parent, size=size)
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
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

# ========== 工具中心页面 ==========
class ToolsPage(QWidget):
    """工具中心页面 - 整合所有工具入口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # 页面标题
        title = QLabel("工具中心")
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold; background-color: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("常用工具快捷入口")
        subtitle.setStyleSheet("color: #777777; font-size: 13px; background-color: transparent;")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        # 工具卡片网格
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(16)

        # 工具列表（去掉图标）
        tools = [
            ("GM工具", "物品发放、角色管理、装备管理", self.open_gm_tool),
            ("账号管理", "账号列表、注册、修改密码", self.open_account_manager),
            ("PVF校验", "服务端与客户端PVF版本比对", self.open_pvf_check),
            ("数据备份", "数据库备份与恢复", self.open_backup),
            ("客户端补丁", "安装或重新安装客户端补丁", self.open_patch_install),
            ("服务端管理", "启动、停止、重启服务端", self.open_server_manager),
        ]

        for i, (name, desc, callback) in enumerate(tools):
            row = i // 3
            col = i % 3
            card = self._create_tool_card(name, desc, callback, i)
            grid_layout.addWidget(card, row, col)

        layout.addWidget(grid_widget)
        layout.addStretch()

    def _create_tool_card(self, name, desc, callback, index=0):
        """创建工具卡片（按照设定：ID选择器+子QLabel无边框+卡片描边）"""
        card = QFrame()
        card.setObjectName(f"toolCard_{index}")
        card.setStyleSheet(f"""
            #toolCard_{index} {{
                background-color: #252525;
                border-radius: 10px;
                border: 1px solid #333333;
            }}
            #toolCard_{index}:hover {{
                background-color: #2a2a2a;
                border: 1px solid #444444;
            }}
            #toolCard_{index} QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumHeight(100)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        # 名称
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; background-color: transparent;")
        card_layout.addWidget(name_label)

        # 描述
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #888888; font-size: 12px; background-color: transparent;")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)

        # 点击事件
        card.mousePressEvent = lambda event: callback()

        return card

    def open_gm_tool(self):
        """打开GM工具"""
        gm_path = os.path.join(os.path.dirname(sys.executable), "module", "gmtool.exe")
        if os.path.exists(gm_path):
            subprocess.Popen([gm_path], cwd=os.path.dirname(gm_path))
        else:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"GM工具未找到：{gm_path}", color="#ff6b6b")

    def open_account_manager(self):
        """打开账号管理"""
        acc_path = os.path.join(os.path.dirname(sys.executable), "module", "accmg.exe")
        if os.path.exists(acc_path):
            subprocess.Popen([acc_path], cwd=os.path.dirname(acc_path))
        else:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"账号管理工具未找到：{acc_path}", color="#ff6b6b")

    def open_pvf_check(self):
        """打开PVF校验"""
        server_path = self.config.get("go_server_path", "") or self.config.get("python_server_path", "")
        client_path = self.config.get("client_path", "")
        if not server_path or not client_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先在首页设置服务端和客户端路径", color="#ffcc00")
            return
        
        # 先比较文件是否一致
        server_pvf = os.path.join(server_path, "runtime", "data", "dnf", "Script.pvf")
        client_pvf = os.path.join(client_path, "Script.pvf")
        
        try:
            stat1 = os.stat(server_pvf)
            stat2 = os.stat(client_pvf)
            is_same = stat1.st_size == stat2.st_size and int(stat1.st_mtime) == int(stat2.st_mtime)
        except:
            is_same = False
        
        if is_same:
            # 文件一致，直接状态栏静默通知，不弹窗
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("当前服务端与客户端pvf一致，无需替换", color="#4caf50", duration=4000)
            return
        
        # 文件不一致，打开弹窗
        pvf_window = PvfCheckWindow(server_path, client_path, self)
        pvf_window.exec_()

    def open_backup(self):
        """打开数据备份"""
        # 切换到存档管理页面
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "show_archive_page"):
                parent.show_archive_page()
                break
            parent = parent.parent()

    def open_patch_install(self):
        """打开客户端补丁安装"""
        server_path = self.config.get("go_server_path", "") or self.config.get("python_server_path", "")
        client_path = self.config.get("client_path", "")
        if not server_path or not client_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先在首页设置服务端和客户端路径", color="#ffcc00")
            return
        install_window = InstallPatchWindow(server_path, client_path, self)
        install_window.exec_()

    def open_server_manager(self):
        """打开服务端管理"""
        # 切换到首页
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "show_main_page"):
                parent.show_main_page()
                break
            parent = parent.parent()


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
                font-size: 14px;
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
                font-size: 14px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """
        label_style = "color: #cccccc; font-size: 13px; font-weight: bold; background-color: transparent;"

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
                font-size: 14px;
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

        # ===== 按钮区域 =====
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        # 安装客户端补丁按钮
        self.install_patch_btn = QPushButton("安装客户端补丁")
        self.install_patch_btn.setCursor(Qt.PointingHandCursor)
        self.install_patch_btn.setMinimumHeight(36)
        self.install_patch_btn.setMinimumWidth(140)
        self.install_patch_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #4a4a4a; border-color: #666666; }
            QPushButton:pressed { background-color: #555555; }
        """)
        self.install_patch_btn.clicked.connect(self.on_install_patch)
        btn_layout.addWidget(self.install_patch_btn)

        # 保存按钮
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
                font-size: 15px;
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
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请选择第三方服务端目录", color="#ffcc00")
            return
        if server_type == "python" and not py_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请选择一体式服务端目录", color="#ffcc00")
            return
        if not client_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请选择客户端目录", color="#ffcc00")
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

    def on_install_patch(self):
        """安装客户端补丁"""
        server_type = self.server_type_combo.currentData()
        server_path = self.go_path_edit.text().strip() if server_type == "go" else self.python_path_edit.text().strip()
        client_path = self.client_path_edit.text().strip()

        if not server_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先选择服务端目录", color="#ffcc00")
            return
        if not client_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先选择客户端目录", color="#ffcc00")
            return

        # 验证客户端目录
        if not os.path.exists(os.path.join(client_path, "DNF.exe")) and not os.path.exists(os.path.join(client_path, "NoPack.exe")):
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("客户端目录中没有找到 DNF.exe 或 NoPack.exe", color="#ff6b6b")
            return

        # 检查游戏进程
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in ['DNF.exe', 'NoPack.exe']:
                        if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                            self.main_window.show_notify("请先退出游戏后再安装补丁", color="#ff6b6b")
                        return
                except:
                    pass
        except ImportError:
            pass

        # 先保存配置
        self.config.set("server_type", server_type)
        self.config.set("go_server_path", self.go_path_edit.text().strip())
        self.config.set("python_server_path", self.python_path_edit.text().strip())
        self.config.set("client_path", client_path)
        self.config.save_config()

        # 打开安装窗口
        install_window = InstallPatchWindow(server_path, client_path, self)
        result = install_window.exec_()
        if result == QDialog.Accepted:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("客户端补丁安装完成", color="#4caf50")
        else:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("客户端补丁安装已取消", color="#ffcc00")

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
                font-size: 14px;
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
        self.log_count_label.setStyleSheet("color: #888888; font-size: 13px; background-color: transparent;")
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
                font-size: 13px;
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
        self.scheduled_backup_timer = None
        self.init_ui()
        self.init_scheduled_backup()
    
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
                font-size: 14px;
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
        
        # 定时备份设置
        self.scheduled_backup_checkbox = QCheckBox("定时备份")
        self.scheduled_backup_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 14px;
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
        self.scheduled_backup_checkbox.setChecked(self.config.get("scheduled_backup_enabled", False))
        self.scheduled_backup_checkbox.stateChanged.connect(self.on_scheduled_backup_changed)
        toolbar.addWidget(self.scheduled_backup_checkbox)
        
        # 备份间隔输入框
        self.backup_interval_edit = QLineEdit()
        self.backup_interval_edit.setPlaceholderText("间隔(分钟)")
        self.backup_interval_edit.setFixedWidth(100)
        self.backup_interval_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """)
        self.backup_interval_edit.setText(str(self.config.get("scheduled_backup_interval", 30)))
        self.backup_interval_edit.editingFinished.connect(self.on_backup_interval_changed)
        toolbar.addWidget(self.backup_interval_edit)
        
        # 自动备份设置
        self.auto_backup_checkbox = QCheckBox("关闭服务端时自动备份")
        self.auto_backup_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 14px;
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
                font-size: 13px;
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
                font-size: 13px;
                font-weight: bold;
            }
            QTableCornerButton::section {
                background-color: #252525;
                border: none;
                border-bottom: 1px solid #3a3a3a;
                border-right: 1px solid #3a3a3a;
            }
        """)
        self.archive_table.horizontalHeader().setStretchLastSection(True)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.archive_table.cellDoubleClicked.connect(self.on_archive_cell_double_clicked)
        layout.addWidget(self.archive_table)
        
        # 加载存档列表
        self.load_archives()
    
    def get_server_path(self):
        """获取服务端路径"""
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            return self.config.get("go_server_path", "")
        else:
            return self.config.get("python_server_path", "")
    
    def get_db_path(self):
        """获取数据库文件路径"""
        server_path = self.get_server_path()
        if not server_path:
            return ""
        
        # 默认MySQL数据目录
        mysql_data = os.path.join(server_path, "runtime", "mysql", "data")
        if os.path.exists(mysql_data):
            return mysql_data
        
        # SQLite数据库文件
        sqlite_db = os.path.join(server_path, "runtime", "data", "dnf_local.db")
        if os.path.exists(sqlite_db):
            return sqlite_db
        
        return mysql_data  # 默认返回MySQL路径
    
    def get_backup_dir(self):
        """获取备份目录 - 存储在程序根目录的backup文件夹下"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(base_dir, "backup")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        return backup_dir
    
    def get_dir_size(self, path):
        """计算目录大小"""
        total_size = 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except:
                    pass
        return total_size
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def load_archives(self):
        """加载存档列表"""
        self.archive_table.setRowCount(0)
        
        backup_dir = self.get_backup_dir()
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
            return
        
        # 读取备份元数据
        meta_file = os.path.join(backup_dir, "backups.json")
        archives = []
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    archives = json.load(f)
            except:
                archives = []
        
        # 按时间倒序
        archives.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 添加到表格
        for archive in archives:
            row = self.archive_table.rowCount()
            self.archive_table.insertRow(row)
            self.archive_table.setItem(row, 0, QTableWidgetItem(archive.get("name", "")))
            self.archive_table.setItem(row, 1, QTableWidgetItem(archive.get("timestamp", "")))
            self.archive_table.setItem(row, 2, QTableWidgetItem(archive.get("size", "")))
            self.archive_table.setItem(row, 3, QTableWidgetItem(archive.get("note", "")))
    
    def on_archive_cell_double_clicked(self, row, column):
        """双击存档表格单元格 - 备注列可编辑"""
        if column != 3:  # 只允许编辑备注列（第4列，索引为3）
            return
        
        # 获取当前存档名称
        archive_name_item = self.archive_table.item(row, 0)
        if not archive_name_item:
            return
        archive_name = archive_name_item.text()
        
        # 获取当前备注
        current_note = ""
        note_item = self.archive_table.item(row, 3)
        if note_item:
            current_note = note_item.text()
        
        # 使用输入对话框编辑备注
        from PyQt5.QtWidgets import QInputDialog
        new_note, ok = QInputDialog.getText(self, "编辑备注", f"存档：{archive_name}\n请输入备注：", text=current_note)
        
        if ok and new_note is not None:
            # 保存到backups.json
            backup_dir = self.get_backup_dir()
            meta_file = os.path.join(backup_dir, "backups.json")
            archives = []
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        archives = json.load(f)
                except:
                    archives = []
            
            # 更新备注
            for archive in archives:
                if archive.get("name", "") == archive_name:
                    archive["note"] = new_note
                    break
            
            # 保存元数据
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(archives, f, ensure_ascii=False, indent=4)
            
            # 刷新列表
            self.load_archives()
            
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("备注已更新", color="#4caf50")
    
    def create_archive(self):
        """创建存档"""
        try:
            db_path = self.get_db_path()
            if not db_path or not os.path.exists(db_path):
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify("数据库路径不存在，请先配置服务端", color="#ff4444")
                return
            
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log("开始创建存档...")
            
            # 生成备份目录名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.get_backup_dir(), backup_name)
            
            # 复制数据库文件
            import shutil
            if os.path.isdir(db_path):
                shutil.copytree(db_path, backup_path)
            else:
                shutil.copy2(db_path, backup_path)
            
            # 计算大小
            size = self.get_dir_size(backup_path)
            size_str = self.format_size(size)
            
            # 读取现有备份元数据
            meta_file = os.path.join(self.get_backup_dir(), "backups.json")
            archives = []
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        archives = json.load(f)
                except:
                    archives = []
            
            # 添加备份记录
            backup_info = {
                "name": backup_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "",
                "size": size_str,
                "path": backup_path
            }
            archives.insert(0, backup_info)
            
            # 保存元数据
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(archives, f, ensure_ascii=False, indent=4)
            
            # 刷新列表
            self.load_archives()
            
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"存档创建成功: {backup_name} ({size_str})")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("存档创建成功", color="#44ff44")
                
        except Exception as e:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"存档创建失败: {str(e)}")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"存档创建失败: {str(e)}", color="#ff4444")
    
    def restore_archive(self):
        """恢复存档"""
        selected_rows = self.archive_table.selectedItems()
        if not selected_rows:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先选择要恢复的存档", color="#ffcc00")
            return
        
        archive_name = selected_rows[0].text()
        
        # 读取备份元数据
        meta_file = os.path.join(self.get_backup_dir(), "backups.json")
        archives = []
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    archives = json.load(f)
            except:
                archives = []
        
        # 找到对应的备份
        backup_info = None
        for archive in archives:
            if archive.get("name") == archive_name:
                backup_info = archive
                break
        
        if not backup_info:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("未找到对应的存档文件", color="#ff4444")
            return
        
        # 确认对话框
        reply = GMDialog.question(self, "确认恢复", 
                                       f"确定要恢复存档「{archive_name}」吗？\n此操作将覆盖当前数据，不可恢复！",
                                       QMessageBox.Yes | QMessageBox.No,
                                       size=(350, 210))
        if reply != QMessageBox.Yes:
            return
        
        try:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"正在恢复存档: {archive_name}")
            
            db_path = self.get_db_path()
            backup_path = backup_info.get("path", "")
            
            if not os.path.exists(backup_path):
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify("备份文件不存在", color="#ff4444")
                return
            
            import shutil
            # 删除当前数据库
            if os.path.exists(db_path):
                if os.path.isdir(db_path):
                    shutil.rmtree(db_path)
                else:
                    os.remove(db_path)
            
            # 恢复备份
            if os.path.isdir(backup_path):
                shutil.copytree(backup_path, db_path)
            else:
                shutil.copy2(backup_path, db_path)
            
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"存档恢复成功: {archive_name}")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("存档恢复成功", color="#44ff44")
                
        except Exception as e:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"存档恢复失败: {str(e)}")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"存档恢复失败: {str(e)}", color="#ff4444")
    
    def delete_archive(self):
        """删除存档"""
        selected_rows = self.archive_table.selectedItems()
        if not selected_rows:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先选择要删除的存档", color="#ffcc00")
            return
        
        archive_name = selected_rows[0].text()
        
        # 读取备份元数据
        meta_file = os.path.join(self.get_backup_dir(), "backups.json")
        archives = []
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    archives = json.load(f)
            except:
                archives = []
        
        # 找到对应的备份
        backup_info = None
        for archive in archives:
            if archive.get("name") == archive_name:
                backup_info = archive
                break
        
        # 确认对话框
        reply = GMDialog.question(self, "确认删除", 
                                       f"确定要删除存档「{archive_name}」吗？\n此操作不可恢复！",
                                       QMessageBox.Yes | QMessageBox.No,
                                       size=(350, 210))
        if reply != QMessageBox.Yes:
            return
        
        try:
            import shutil
            if backup_info:
                backup_path = backup_info.get("path", "")
                if os.path.exists(backup_path):
                    if os.path.isdir(backup_path):
                        shutil.rmtree(backup_path)
                    else:
                        os.remove(backup_path)
            
            # 从元数据中移除
            archives = [a for a in archives if a.get("name") != archive_name]
            
            # 保存元数据
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(archives, f, ensure_ascii=False, indent=4)
            
            # 刷新列表
            self.load_archives()
            
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"已删除存档: {archive_name}")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("存档删除成功", color="#44ff44")
                
        except Exception as e:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log(f"存档删除失败: {str(e)}")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"存档删除失败: {str(e)}", color="#ff4444")
    
    def on_auto_backup_changed(self, state):
        """自动备份设置改变"""
        self.config.set("auto_backup_on_stop", state == Qt.Checked)
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
            if state == Qt.Checked:
                self.main_window.main_page.log("已开启关闭服务端时自动备份")
            else:
                self.main_window.main_page.log("已关闭关闭服务端时自动备份")
    
    def init_scheduled_backup(self):
        """初始化定时备份"""
        if self.config.get("scheduled_backup_enabled", False):
            self.start_scheduled_backup()
    
    def start_scheduled_backup(self):
        """启动定时备份"""
        if self.scheduled_backup_timer is None:
            self.scheduled_backup_timer = QTimer()
            self.scheduled_backup_timer.timeout.connect(self.do_scheduled_backup)
        interval = self.config.get("scheduled_backup_interval", 30) * 60 * 1000  # 转换为毫秒
        self.scheduled_backup_timer.start(interval)
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
            self.main_window.main_page.log(f"定时备份已启动，间隔{self.config.get('scheduled_backup_interval', 30)}分钟")
    
    def stop_scheduled_backup(self):
        """停止定时备份"""
        if self.scheduled_backup_timer and self.scheduled_backup_timer.isActive():
            self.scheduled_backup_timer.stop()
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
                self.main_window.main_page.log("定时备份已停止")
    
    def on_scheduled_backup_changed(self, state):
        """定时备份设置改变"""
        self.config.set("scheduled_backup_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            self.start_scheduled_backup()
        else:
            self.stop_scheduled_backup()
    
    def on_backup_interval_changed(self):
        """备份间隔改变"""
        try:
            interval = int(self.backup_interval_edit.text())
            if interval < 1:
                interval = 1
            self.config.set("scheduled_backup_interval", interval)
            if self.config.get("scheduled_backup_enabled", False):
                self.stop_scheduled_backup()
                self.start_scheduled_backup()
        except ValueError:
            self.backup_interval_edit.setText(str(self.config.get("scheduled_backup_interval", 30)))
    
    def do_scheduled_backup(self):
        """执行定时备份"""
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'main_page'):
            self.main_window.main_page.log("执行定时备份...")
        self.create_archive()

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
        title_label.setStyleSheet("color: #cccccc; font-size: 15px; font-weight: bold; background-color: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888888; border: 1px solid #444444;
                border-radius: 4px; font-size: 13px; }
            QPushButton:hover { background-color: #333333; border-color: #666666; color: #ffffff; }
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
        account_label.setStyleSheet("color: #b0b0b0; font-size: 14px; background-color: transparent;")
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
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """)
        content_layout.addWidget(self.account_edit)
        
        # 密码输入
        password_label = QLabel("密码")
        password_label.setStyleSheet("color: #b0b0b0; font-size: 14px; background-color: transparent;")
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
                font-size: 14px;
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
        title.setStyleSheet("color: #ffffff; font-size: 21px; font-weight: bold; background-color: transparent;")
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
                font-size: 15px;
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
                font-size: 15px;
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
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请输入账号", color="#ffcc00")
            return
        if not password:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请输入密码", color="#ffcc00")
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


# ========== 数据库管理器 ==========
class DatabaseManager:
    """数据库管理器 - 支持MySQL和SQLite"""

    def __init__(self, server_path):
        self.server_path = server_path
        self.db_config = self._load_db_config()
        self.connection = None

    def _load_db_config(self):
        """从instance.json加载数据库配置"""
        try:
            config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("database", {})
        except Exception as e:
            print(f"加载数据库配置失败: {e}")
            return {}

    def is_sqlite(self):
        """判断是否为SQLite模式"""
        return self.db_config.get("mode", "portable") == "sqlite"

    def get_mysql_config(self):
        """获取MySQL配置"""
        return {
            "host": self.db_config.get("host", "127.0.0.1"),
            "port": self.db_config.get("port", 13306),
            "user": self.db_config.get("user", "root"),
            "password": self.db_config.get("password", ""),
            "database": self.db_config.get("name", "dnf_local")
        }

    def get_sqlite_path(self):
        """获取SQLite数据库路径"""
        return os.path.join(self.server_path, "runtime", "data", "dnf", "dnf_local.db")

    def connect(self):
        """连接数据库"""
        try:
            if self.is_sqlite():
                import sqlite3
                db_path = self.get_sqlite_path()
                if not os.path.exists(db_path):
                    return False, f"SQLite数据库文件不存在: {db_path}"
                self.connection = sqlite3.connect(db_path)
                return True, "SQLite连接成功"
            else:
                try:
                    import pymysql
                    config = self.get_mysql_config()
                    self.connection = pymysql.connect(
                        host=config["host"],
                        port=config["port"],
                        user=config["user"],
                        password=config["password"],
                        database=config["database"],
                        charset='utf8mb4',
                        connect_timeout=5
                    )
                    return True, "MySQL连接成功"
                except ImportError:
                    return False, "pymysql模块未安装"
        except Exception as e:
            return False, f"数据库连接失败: {e}"

    def verify_account(self, username, password):
        """验证账号密码 - 使用dnf_login_accounts表"""
        try:
            success, msg = self.connect()
            if not success:
                return False, msg

            cursor = self.connection.cursor()

            if self.is_sqlite():
                # SQLite模式
                query = "SELECT password_hash FROM dnf_login_accounts WHERE username = ?"
                cursor.execute(query, (username,))
            else:
                # MySQL模式
                query = "SELECT password_hash FROM dnf_login_accounts WHERE username = %s"
                cursor.execute(query, (username,))

            result = cursor.fetchone()
            cursor.close()

            if result is None:
                return False, "账号不存在"

            db_password_hash = result[0]

            # varbinary类型需要转换为字符串
            if isinstance(db_password_hash, bytes):
                db_password_hash = db_password_hash.decode('utf-8', errors='ignore')

            # 空密码直接通过
            if not db_password_hash or db_password_hash == "":
                return True, "登录成功"

            # 明文匹配
            if db_password_hash == password:
                return True, "登录成功"

            # bcrypt匹配（密码以$2开头）
            if db_password_hash.startswith('$2'):
                try:
                    import bcrypt
                    if bcrypt.checkpw(password.encode('utf-8'), db_password_hash.encode('utf-8')):
                        return True, "登录成功"
                except ImportError:
                    return False, "bcrypt模块未安装，无法验证密码"
                except Exception as e:
                    return False, f"密码验证失败: {e}"

            # MD5匹配
            import hashlib
            md5_password = hashlib.md5(password.encode('utf-8')).hexdigest()
            if db_password_hash == md5_password:
                return True, "登录成功"

            # SHA256匹配
            sha256_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if db_password_hash == sha256_password:
                return True, "登录成功"

            return False, "密码错误"

        except Exception as e:
            return False, f"验证失败: {e}"
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def register_account(self, username, password):
        """注册账号 - 使用dnf_login_accounts表"""
        try:
            success, msg = self.connect()
            if not success:
                return False, msg

            cursor = self.connection.cursor()

            # 检查账号是否已存在
            if self.is_sqlite():
                cursor.execute("SELECT account_id FROM dnf_login_accounts WHERE username = ?", (username,))
            else:
                cursor.execute("SELECT account_id FROM dnf_login_accounts WHERE username = %s", (username,))

            if cursor.fetchone() is not None:
                cursor.close()
                return False, "账号已存在"

            # 密码使用bcrypt加密
            import bcrypt
            import uuid
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # 生成account_id
            account_id = f"dnf:{uuid.uuid4().hex}"

            # 插入新账号
            current_time = datetime.now()
            if self.is_sqlite():
                cursor.execute(
                    "INSERT INTO dnf_login_accounts (account_id, username, password_hash, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (account_id, username, password_hash, 'active', current_time, current_time)
                )
            else:
                cursor.execute(
                    "INSERT INTO dnf_login_accounts (account_id, username, password_hash, state, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (account_id, username, password_hash, 'active', current_time, current_time)
                )

            self.connection.commit()
            cursor.close()
            return True, "注册成功"

        except ImportError:
            return False, "bcrypt模块未安装，无法注册账号"
        except Exception as e:
            return False, f"注册失败: {e}"
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None


# ========== 启动游戏后台线程 ==========
class LaunchGameWorker(QThread):
    """启动游戏后台线程（完整流程版）"""
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

    def _check_port_open(self, host, port, timeout=2):
        """检查端口是否开放"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
                return result == 0
        except:
            return False

    def _get_mysql_config(self):
        """从instance.json获取MySQL配置"""
        try:
            config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            db_config = config.get("database", {})
            return db_config.get("host", "127.0.0.1"), db_config.get("port", 13306)
        except:
            return "127.0.0.1", 13306

    def _get_db_mode(self):
        """从instance.json获取数据库模式"""
        try:
            config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            db_config = config.get("database", {})
            return db_config.get("mode", "portable")
        except:
            return "portable"

    def _is_sqlite_mode(self):
        """判断是否为SQLite模式"""
        # 1. 优先从启动器配置文件读取
        try:
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
        # 2. 从instance.json读取
        return self._get_db_mode() == "sqlite"

    def _is_admin(self):
        """检查是否以管理员身份运行"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

    def _start_server_and_wait(self, timeout=60):
        """启动服务端并等待就绪（完整流程）"""
        try:
            control_exe = os.path.join(self.server_path, "runtime", "bin", "DNF90Control.exe")

            # 1. 验证控制文件存在
            if not os.path.exists(control_exe):
                self.log(f"错误: 未找到 DNF90Control.exe")
                self.log(f"  路径: {control_exe}")
                return False

            # 2. 验证instance.json存在并读取端口配置
            config_file = os.path.join(self.server_path, "runtime", "config", "instance.json")
            if not os.path.exists(config_file):
                self.log("错误: 未找到 instance.json 配置文件")
                return False

            mysql_host, mysql_port = self._get_mysql_config()
            is_sqlite = self._is_sqlite_mode()

            if is_sqlite:
                check_host = "127.0.0.1"
                check_port = 7001
                db_type = "SQLite"
            else:
                check_host = mysql_host
                check_port = mysql_port
                db_type = "MySQL"

            self.log(f"数据库模式: {db_type} (检查端口: {check_port})")

            # 3. 检查管理员权限
            if not self._is_admin():
                self.log("警告: 未以管理员身份运行，可能导致启动失败")

            # 4. 检查端口是否已被占用
            if self._check_port_open(check_host, check_port, timeout=1):
                self.log(f"提示: 端口{check_port}已被占用，可能{db_type}已在运行")

            # 5. 自动同步客户端路径到服务端配置
            if self.client_path and os.path.exists(self.client_path):
                try:
                    self.log("正在同步客户端路径...")
                    env = os.environ.copy()
                    env["DNF90_PROJECT_ROOT"] = self.server_path
                    sync_proc = subprocess.Popen(
                        [control_exe, "configure-client", "--directory", self.client_path],
                        cwd=self.server_path,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    sync_proc.wait(timeout=10)
                    if sync_proc.returncode == 0:
                        self.log("客户端路径同步成功")
                    else:
                        self.log(f"客户端路径同步失败（返回码: {sync_proc.returncode}），继续启动服务端...")
                except Exception as e:
                    self.log(f"客户端路径同步异常: {e}，继续启动服务端...")
            else:
                self.log("警告: 客户端路径未配置或不存在，服务端可能使用旧配置")

            # 6. 设置环境变量并启动服务端
            env = os.environ.copy()
            env["DNF90_PROJECT_ROOT"] = self.server_path
            env["DNF_RESIDENT_CHANNEL_ID"] = "19"

            self.log("正在启动服务端...")
            self.log(f"  工作目录: {self.server_path}")
            self.log(f"  控制程序: {control_exe}")

            try:
                proc = subprocess.Popen(
                    [control_exe, "start"],
                    cwd=self.server_path,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.log(f"  进程ID: {proc.pid}")
            except Exception as e:
                self.log(f"错误: 启动进程失败 - {e}")
                return False

            # 7. 收集输出的线程
            output_lines = []
            MAX_OUTPUT_LINES = 500
            def read_output():
                try:
                    for line in iter(proc.stdout.readline, b''):
                        try:
                            decoded = line.decode('gbk', errors='ignore').strip()
                        except:
                            decoded = line.decode('utf-8', errors='ignore').strip()
                        if decoded:
                            output_lines.append(decoded)
                            if len(output_lines) > MAX_OUTPUT_LINES:
                                output_lines.pop(0)
                except:
                    pass

            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()

            # 8. 等待服务端就绪
            start_time = time.time()
            last_log = 0
            last_checked_count = 0
            server_ready = False
            control_exited = False
            ready_keywords = ["dnf90 is ready", "server is ready", "ready."]

            while time.time() - start_time < timeout:
                # 检查控制进程是否退出
                if proc.poll() is not None and not control_exited:
                    control_exited = True
                    exit_code = proc.returncode
                    self.log(f"DNF90Control进程已退出（退出码: {exit_code}），继续检测服务端状态...")

                # 检查输出中的就绪信号
                if len(output_lines) > last_checked_count:
                    new_lines = output_lines[last_checked_count:]
                    for line in new_lines:
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ready_keywords):
                            self.log(f"检测到服务端就绪信号: {line}")
                            server_ready = True
                            break
                    last_checked_count = len(output_lines)
                    if server_ready:
                        break

                # 检查服务端端口7001
                if self._check_port_open("127.0.0.1", 7001, timeout=1):
                    self.log("服务端端口7001已开放")
                    server_ready = True
                    break

                # MySQL模式下检查MySQL端口
                if not is_sqlite:
                    if self._check_port_open(mysql_host, mysql_port, timeout=1):
                        self.log("MySQL端口已开放")
                        server_ready = True
                        break

                # 每10秒输出等待信息
                elapsed = int(time.time() - start_time)
                if elapsed - last_log >= 10:
                    self.log(f"等待服务端启动... ({elapsed}/{timeout}秒)")
                    last_log = elapsed

                time.sleep(1)

            if server_ready:
                self.log("服务端启动成功")
                return True
            else:
                self.log(f"错误: 服务端启动超时（{timeout}秒）")
                if output_lines:
                    self.log("=== 服务端输出（最后10行）===")
                    for line in output_lines[-10:]:
                        self.log(f"  {line}")
                return False

        except Exception as e:
            self.log(f"错误: 启动服务端异常 - {e}")
            return False

    def run(self):
        try:
            # Go服务端使用完整流程，Python服务端使用简化流程
            if self.server_type == "python":
                self._run_python_server()
            else:
                self._run_go_server()
        except Exception as e:
            self.finished_signal.emit(False, f"启动游戏异常: {e}")

    def _run_python_server(self):
        """Python一体式服务端启动流程（简化版）"""
        self.log("正在检查服务端状态...")
        server_running = ServerStatusChecker.check_python_server()
        if not server_running:
            self.log("服务端未启动，正在启动一体式服务端...")
            exe_path = os.path.join(self.server_path, "game_server.exe")
            if not os.path.exists(exe_path):
                self.finished_signal.emit(False, f"未找到game_server.exe: {exe_path}")
                return
            subprocess.Popen([exe_path], cwd=self.server_path,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            # 等待服务端就绪
            for i in range(30):
                time.sleep(1)
                if ServerStatusChecker.check_python_server():
                    break
            else:
                self.finished_signal.emit(False, "服务端启动失败，请检查服务端目录配置")
                return
        self.log("服务端已就绪")
        self._launch_client_direct()

    def _run_go_server(self):
        """Go第三方服务端启动流程（完整版）"""
        self.log("正在检查服务端状态...")

        # 获取数据库配置
        mysql_host, mysql_port = self._get_mysql_config()
        is_sqlite = self._is_sqlite_mode()
        if is_sqlite:
            check_port = 7001
            db_type = "SQLite"
        else:
            check_port = mysql_port
            db_type = "MySQL"

        # 检查服务端是否已启动
        server_running = self._check_port_open("127.0.0.1", 7001, timeout=2)
        if not server_running and not is_sqlite:
            server_running = self._check_port_open(mysql_host, mysql_port, timeout=2)

        if not server_running:
            self.log("服务端未启动，正在启动服务端...")
            if not self._start_server_and_wait(timeout=60):
                self.finished_signal.emit(False, "服务启动失败，请检查服务端目录配置")
                return
        else:
            self.log("服务端已在运行")

        self.log("服务端已就绪")
        self._launch_client_via_control()

    def _launch_client_direct(self):
        """直接启动DNF.exe（Python服务端用）"""
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

    def _launch_client_via_control(self):
        """通过DNF90Control.exe启动客户端（Go服务端用，完整版）"""
        self.log("正在启动客户端...")

        control_exe = os.path.join(self.server_path, "runtime", "bin", "DNF90Control.exe")
        if not os.path.exists(control_exe):
            self.log(f"错误: 未找到 DNF90Control.exe: {control_exe}")
            self.finished_signal.emit(False, "未找到DNF90Control.exe")
            return

        # 设置环境变量
        env = os.environ.copy()
        env["DNF90_PROJECT_ROOT"] = self.server_path
        env["DNF_RESIDENT_CHANNEL_ID"] = "19"

        # 构建启动参数
        launch_args = [control_exe, "launch-client", "--multi-instance"]
        if self.client_path and os.path.exists(self.client_path):
            launch_args.extend(["--client-directory", self.client_path])
        launch_args.extend(["--username", self.account, "--password-stdin"])

        self.log(f"启动参数: {' '.join(launch_args[1:])}")

        try:
            proc = subprocess.Popen(
                launch_args,
                cwd=self.server_path,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 通过标准输入传递密码
            try:
                proc.stdin.write((self.password + "\n").encode('utf-8'))
                proc.stdin.flush()
                proc.stdin.close()
            except Exception as e:
                self.log(f"密码传递提示: {e}")

            # 等待启动结果（最多15秒）
            try:
                stdout, stderr = proc.communicate(timeout=15)
                if proc.returncode == 0:
                    self.log("游戏启动成功！")

                    # 尝试绑定客户端账号
                    self._bind_client_account(proc.pid, env)

                    self.finished_signal.emit(True, "游戏启动成功")
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore').strip() if stderr else "未知错误"
                    self.log(f"启动返回码: {proc.returncode}")
                    if error_msg:
                        self.log(f"错误: {error_msg}")
                    self.finished_signal.emit(False, f"启动失败: {error_msg}")
            except subprocess.TimeoutExpired:
                # 超时但进程还在运行，认为启动成功
                self.log("客户端启动中（超时，认为启动成功）")
                self.finished_signal.emit(True, "游戏启动成功")
        except Exception as e:
            self.log(f"启动客户端异常: {e}")
            self.finished_signal.emit(False, f"启动客户端异常: {e}")

    def _bind_client_account(self, client_pid, env):
        """绑定客户端账号（可选）"""
        try:
            control_exe = os.path.join(self.server_path, "runtime", "bin", "DNF90Control.exe")
            self.log("正在绑定客户端账号...")

            bind_args = [
                control_exe, "account", "bind-client",
                "--username", self.account,
                "--pid", str(client_pid),
                "--password-stdin"
            ]

            bind_proc = subprocess.Popen(
                bind_args,
                cwd=self.server_path,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 传递密码
            try:
                bind_proc.stdin.write((self.password + "\n").encode('utf-8'))
                bind_proc.stdin.flush()
                bind_proc.stdin.close()
            except:
                pass

            # 等待绑定结果（最多5秒）
            try:
                bind_proc.communicate(timeout=5)
                if bind_proc.returncode == 0:
                    self.log("客户端账号绑定成功")
                else:
                    self.log("客户端账号绑定失败（不影响游戏）")
            except subprocess.TimeoutExpired:
                self.log("客户端账号绑定超时（不影响游戏）")
        except Exception as e:
            self.log(f"客户端账号绑定异常（不影响游戏）: {e}")


# ========== PVF校验窗口 ==========
class PvfCheckWindow(QDialog):
    """PVF文件校验窗口"""
    def __init__(self, server_path, client_path, parent=None):
        super().__init__(parent)
        self.server_path = server_path
        self.client_path = client_path
        self.selected_version = None  # "server" or "client"
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 480)
        self.init_ui()

    def init_ui(self):
        # 主容器
        self.container = QWidget(self)
        self.container.setObjectName("pvfContainer")
        self.container.setGeometry(0, 0, 520, 480)
        self.container.setStyleSheet("""
            #pvfContainer { background-color: #1e1e1e; border-radius: 8px; border: 1px solid #333333; }
            #pvfContainer QLabel { background-color: transparent; border: none; }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)

        # 标题
        title = QLabel("PVF 文件校验")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; background-color: transparent;")
        layout.addWidget(title)
        layout.addSpacing(12)

        # 获取PVF文件信息
        server_pvf = os.path.join(self.server_path, "runtime", "data", "dnf", "Script.pvf")
        client_pvf = os.path.join(self.client_path, "Script.pvf")

        server_info = self._get_file_info(server_pvf)
        client_info = self._get_file_info(client_pvf)

        # 比较文件是否一致
        is_same = self._compare_files(server_pvf, client_pvf)

        if is_same:
            # 文件一致，显示提示
            layout.addSpacing(40)
            hint = QLabel("✅ 当前服务端与客户端pvf一致，无需替换")
            hint.setStyleSheet("color: #4caf50; font-size: 15px; font-weight: 600; background-color: transparent;")
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignCenter)
            layout.addWidget(hint)
            layout.addSpacing(20)

            # 显示文件信息
            info_label = QLabel(f"服务端: {server_info['size']} | {server_info['time']}\n客户端: {client_info['size']} | {client_info['time']}")
            info_label.setStyleSheet("color: #888888; font-size: 12px; background-color: transparent;")
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)
            layout.addStretch()

            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.setFixedHeight(38)
            close_btn.setCursor(Qt.PointingHandCursor)
            close_btn.setStyleSheet("""
                QPushButton { background-color: transparent; color: #888888; border: 1px solid #444444;
                    border-radius: 4px; font-size: 14px; padding: 4px 20px; }
                QPushButton:hover { background-color: #333333; border-color: #666666; color: #ffffff; }
            """)
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn)
        else:
            # 文件不一致，显示选择版本界面
            hint = QLabel("检测到服务端与客户端的 Script.pvf 文件不一致，请选择要使用的版本：")
            hint.setStyleSheet("color: #cccccc; font-size: 13px; background-color: transparent;")
            hint.setWordWrap(True)
            layout.addWidget(hint)
            layout.addSpacing(12)

            # 服务端版本卡片（2.x样式：蓝色边框）
            server_card = QFrame()
            server_card.setObjectName("serverCard")
            server_card.setStyleSheet("""
                #serverCard { background-color: #1a1a2e; border-radius: 6px; border: 1px solid #0078d4; }
                #serverCard QLabel { background-color: transparent; border: none; }
            """)
            server_layout = QVBoxLayout(server_card)
            server_layout.setContentsMargins(14, 10, 14, 10)
            server_layout.setSpacing(4)

            server_title = QLabel("服务端版本")
            server_title.setStyleSheet("color: #4da6ff; font-size: 14px; font-weight: bold; background-color: transparent;")
            server_layout.addWidget(server_title)

            server_path_label = QLabel(f"路径: {server_pvf}")
            server_path_label.setStyleSheet("color: #aaaaaa; font-size: 11px; background-color: transparent;")
            server_path_label.setWordWrap(True)
            server_layout.addWidget(server_path_label)

            server_size = QLabel(f"文件大小: {server_info['size']}")
            server_size.setStyleSheet("color: #aaaaaa; font-size: 12px; background-color: transparent;")
            server_layout.addWidget(server_size)

            server_time = QLabel(f"修改时间: {server_info['time']}")
            server_time.setStyleSheet("color: #aaaaaa; font-size: 12px; background-color: transparent;")
            server_layout.addWidget(server_time)

            layout.addWidget(server_card)
            layout.addSpacing(10)

            # 客户端版本卡片（2.x样式：红色边框）
            client_card = QFrame()
            client_card.setObjectName("clientCard")
            client_card.setStyleSheet("""
                #clientCard { background-color: #2e1a1a; border-radius: 6px; border: 1px solid #e74c3c; }
                #clientCard QLabel { background-color: transparent; border: none; }
            """)
            client_layout = QVBoxLayout(client_card)
            client_layout.setContentsMargins(14, 10, 14, 10)
            client_layout.setSpacing(4)

            client_title = QLabel("客户端版本")
            client_title.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold; background-color: transparent;")
            client_layout.addWidget(client_title)

            client_path_label = QLabel(f"路径: {client_pvf}")
            client_path_label.setStyleSheet("color: #aaaaaa; font-size: 11px; background-color: transparent;")
            client_path_label.setWordWrap(True)
            client_layout.addWidget(client_path_label)

            client_size = QLabel(f"文件大小: {client_info['size']}")
            client_size.setStyleSheet("color: #aaaaaa; font-size: 12px; background-color: transparent;")
            client_layout.addWidget(client_size)

            client_time = QLabel(f"修改时间: {client_info['time']}")
            client_time.setStyleSheet("color: #aaaaaa; font-size: 12px; background-color: transparent;")
            client_layout.addWidget(client_time)

            layout.addWidget(client_card)
            layout.addSpacing(10)

            # 不一致原因提示
            diff_hint = QLabel("⚠ 文件大小或修改时间不一致")
            diff_hint.setStyleSheet("color: #ffcc00; font-size: 12px; background-color: transparent;")
            diff_hint.setAlignment(Qt.AlignCenter)
            layout.addWidget(diff_hint)
            layout.addStretch()

            # 底部按钮区域
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(10)

            # 使用服务端版本按钮（蓝色）
            use_server_btn = QPushButton("使用服务端版本")
            use_server_btn.setFixedHeight(38)
            use_server_btn.setCursor(Qt.PointingHandCursor)
            use_server_btn.setStyleSheet("""
                QPushButton { background-color: #0078d4; color: #ffffff; border: none; border-radius: 4px; font-size: 13px; font-weight: 500; }
                QPushButton:hover { background-color: #106ebe; }
                QPushButton:pressed { background-color: #005a9e; }
            """)
            use_server_btn.clicked.connect(lambda: self._select_version("server"))
            btn_layout.addWidget(use_server_btn)

            # 使用客户端版本按钮（红色）
            use_client_btn = QPushButton("使用客户端版本")
            use_client_btn.setFixedHeight(38)
            use_client_btn.setCursor(Qt.PointingHandCursor)
            use_client_btn.setStyleSheet("""
                QPushButton { background-color: #e74c3c; color: #ffffff; border: none; border-radius: 4px; font-size: 13px; font-weight: 500; }
                QPushButton:hover { background-color: #c0392b; }
                QPushButton:pressed { background-color: #a93226; }
            """)
            use_client_btn.clicked.connect(lambda: self._select_version("client"))
            btn_layout.addWidget(use_client_btn)

            # 取消按钮（灰色）
            cancel_btn = QPushButton("取消")
            cancel_btn.setFixedHeight(38)
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.setStyleSheet("""
                QPushButton { background-color: #3a3a3a; color: #ffffff; border: none; border-radius: 4px; font-size: 13px; }
                QPushButton:hover { background-color: #4a4a4a; }
            """)
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

            layout.addLayout(btn_layout)

    def _compare_files(self, file1, file2):
        """比较两个文件是否一致（大小和修改时间）"""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            # 比较大小和修改时间（精确到秒）
            return stat1.st_size == stat2.st_size and int(stat1.st_mtime) == int(stat2.st_mtime)
        except:
            return False

    def _get_file_info(self, file_path):
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            size_mb = stat.st_size / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB"
            time_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            return {"size": size_str, "time": time_str}
        except:
            return {"size": "未知", "time": "未知"}

    def _select_version(self, version):
        """选择版本并执行替换"""
        self.selected_version = version
        server_pvf = os.path.join(self.server_path, "runtime", "data", "dnf", "Script.pvf")
        client_pvf = os.path.join(self.client_path, "Script.pvf")

        try:
            if version == "server":
                # 使用服务端版本，替换客户端
                shutil.copy2(server_pvf, client_pvf)
            else:
                # 使用客户端版本，替换服务端
                shutil.copy2(client_pvf, server_pvf)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"PVF文件替换失败:\n{e}")

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


# ========== 安装客户端补丁Worker ==========
class InstallPatchWorker(QThread):
    """安装客户端补丁后台Worker"""
    progress = pyqtSignal(int, str)  # 进度百分比, 状态文字
    finished = pyqtSignal(bool, str)  # 是否成功, 消息
    db_mode_selected = pyqtSignal(str)  # 选择的数据库模式

    def __init__(self, server_path, client_path, db_mode="mysql"):
        super().__init__()
        self.server_path = server_path
        self.client_path = client_path
        self.db_mode = db_mode

    def run(self):
        try:
            self.progress.emit(5, "正在验证文件...")

            # 验证服务端文件
            required_files = [
                ("client-patch\\bin\\DNF.exe", "客户端EXE"),
                ("client-patch\\bin\\ijl15.dll", "ijl15.dll"),
                ("client-patch\\bin\\ijl15_real.dll", "ijl15_real.dll"),
                ("client-patch\\bin\\90CN.dll", "90CN.dll"),
                ("client-lua\\bin\\90CNLua.dll", "90CNLua.dll"),
                ("client-lua\\bin\\lua\\init.lua", "lua\\init.lua"),
                ("client-lua\\bin\\lua\\ai\\init.lua", "lua\\ai\\init.lua"),
                ("runtime\\data\\dnf\\Script.pvf", "Script.pvf"),
            ]

            for rel_path, desc in required_files:
                full_path = os.path.join(self.server_path, rel_path)
                if not os.path.exists(full_path):
                    self.finished.emit(False, f"缺少文件: {desc} ({rel_path})")
                    return

            # 验证ImagePacks2目录
            image_packs_src = os.path.join(self.server_path, "ImagePacks2")
            if not os.path.exists(image_packs_src):
                self.finished.emit(False, "缺少 ImagePacks2 目录")
                return

            self.progress.emit(10, "正在复制客户端EXE...")
            shutil.copy2(
                os.path.join(self.server_path, "client-patch", "bin", "DNF.exe"),
                os.path.join(self.client_path, "DNF.exe")
            )

            self.progress.emit(20, "正在复制补丁DLL...")
            dll_files = ["ijl15.dll", "ijl15_real.dll", "90CN.dll"]
            for dll in dll_files:
                shutil.copy2(
                    os.path.join(self.server_path, "client-patch", "bin", dll),
                    os.path.join(self.client_path, dll)
                )

            self.progress.emit(30, "正在复制Lua补丁...")
            shutil.copy2(
                os.path.join(self.server_path, "client-lua", "bin", "90CNLua.dll"),
                os.path.join(self.client_path, "90CNLua.dll")
            )

            # 创建lua目录
            lua_dir = os.path.join(self.client_path, "lua")
            os.makedirs(lua_dir, exist_ok=True)
            lua_ai_dir = os.path.join(lua_dir, "ai")
            os.makedirs(lua_ai_dir, exist_ok=True)

            shutil.copy2(
                os.path.join(self.server_path, "client-lua", "bin", "lua", "init.lua"),
                os.path.join(lua_dir, "init.lua")
            )
            shutil.copy2(
                os.path.join(self.server_path, "client-lua", "bin", "lua", "ai", "init.lua"),
                os.path.join(lua_ai_dir, "init.lua")
            )

            self.progress.emit(40, "正在复制Script.pvf...")
            shutil.copy2(
                os.path.join(self.server_path, "runtime", "data", "dnf", "Script.pvf"),
                os.path.join(self.client_path, "Script.pvf")
            )

            self.progress.emit(60, "正在复制ImagePacks2资源...")
            image_packs_dst = os.path.join(self.client_path, "ImagePacks2")
            os.makedirs(image_packs_dst, exist_ok=True)

            npk_files = [f for f in os.listdir(image_packs_src) if f.lower().endswith('.npk')]
            total = len(npk_files)
            for i, npk in enumerate(npk_files):
                shutil.copy2(
                    os.path.join(image_packs_src, npk),
                    os.path.join(image_packs_dst, npk)
                )
                progress_val = 60 + int((i + 1) / total * 25)
                self.progress.emit(progress_val, f"正在复制ImagePacks2资源... ({i+1}/{total})")

            self.progress.emit(90, "正在保存客户端配置...")
            # 调用DNF90Control.exe configure-client
            control_exe = os.path.join(self.server_path, "runtime", "bin", "DNF90Control.exe")
            if os.path.exists(control_exe):
                env = os.environ.copy()
                env["DNF90_PROJECT_ROOT"] = self.server_path
                env["DNF_RESIDENT_CHANNEL_ID"] = "19"
                try:
                    result = subprocess.run(
                        [control_exe, "configure-client", "--directory", self.client_path],
                        capture_output=True, text=True, timeout=30,
                        env=env, cwd=self.server_path,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode != 0:
                        self.progress.emit(92, f"警告: 客户端配置保存失败（不影响补丁安装）")
                except Exception as e:
                    self.progress.emit(92, f"警告: 客户端配置保存异常（不影响补丁安装）: {e}")

            self.progress.emit(95, "正在选择数据库模式...")
            # 调用DNF90Control.exe database select
            if os.path.exists(control_exe):
                env = os.environ.copy()
                env["DNF90_PROJECT_ROOT"] = self.server_path
                env["DNF_RESIDENT_CHANNEL_ID"] = "19"
                try:
                    if self.db_mode == "mysql":
                        result = subprocess.run(
                            [control_exe, "database", "select", "--mode", "mysql", "--prepare"],
                            capture_output=True, text=True, timeout=120,
                            env=env, cwd=self.server_path,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        result = subprocess.run(
                            [control_exe, "database", "select", "--mode", "sqlite"],
                            capture_output=True, text=True, timeout=30,
                            env=env, cwd=self.server_path,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    if result.returncode != 0:
                        self.progress.emit(97, f"警告: 数据库模式设置失败")
                except Exception as e:
                    self.progress.emit(97, f"警告: 数据库模式设置异常: {e}")

            self.progress.emit(100, "安装完成！")
            self.finished.emit(True, "客户端补丁安装完成")

        except Exception as e:
            self.finished.emit(False, f"安装失败: {e}")


# ========== 安装客户端补丁窗口 ==========
class InstallPatchWindow(QDialog):
    """安装客户端补丁窗口"""
    def __init__(self, server_path, client_path, parent=None):
        super().__init__(parent)
        self.server_path = server_path
        self.client_path = client_path
        self.worker = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(420, 252)
        self.init_ui()

    def init_ui(self):
        # 主容器
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 420, 252)
        self.container.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 8px;
            border: 1px solid #333333;
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # 标题
        title = QLabel("安装客户端补丁")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; background-color: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 客户端路径显示
        path_label = QLabel(f"客户端目录: {self.client_path}")
        path_label.setStyleSheet("color: #b0b0b0; font-size: 12px; background-color: transparent; border: none;")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        # 数据库模式选择
        db_frame = QFrame()
        db_frame.setStyleSheet("background-color: transparent; border: none;")
        db_layout = QHBoxLayout(db_frame)
        db_layout.setContentsMargins(0, 0, 0, 0)
        db_layout.setSpacing(8)

        db_label = QLabel("数据库模式:")
        db_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent; border: none;")
        db_layout.addWidget(db_label)

        self.db_combo = QComboBox()
        self.db_combo.addItems(["MySQL（推荐）", "SQLite（便携）"])
        self.db_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a; color: #ffffff; border: 1px solid #3a3a3a;
                border-radius: 4px; padding: 4px 8px; font-size: 13px;
            }
            QComboBox:hover { border-color: #0078d4; }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a; color: #ffffff; selection-background-color: #0078d4;
                border: 1px solid #3a3a3a;
            }
        """)
        db_layout.addWidget(self.db_combo)
        db_layout.addStretch()
        layout.addWidget(db_frame)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a1a1a; border: 1px solid #3a3a3a;
                border-radius: 4px; text-align: center; color: #ffffff;
                height: 24px; font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #0078d4; border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 状态文字
        self.status_label = QLabel("准备安装...")
        self.status_label.setStyleSheet("color: #b0b0b0; font-size: 12px; background-color: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setFixedHeight(32)
        self.cancel_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #fff; border: none;
                border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #444444; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.install_btn = QPushButton("开始安装")
        self.install_btn.setCursor(Qt.PointingHandCursor)
        self.install_btn.setFixedHeight(32)
        self.install_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: #fff; border: none;
                border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555; }
        """)
        self.install_btn.clicked.connect(self.start_install)
        btn_layout.addWidget(self.install_btn)

        layout.addLayout(btn_layout)

    def start_install(self):
        """开始安装"""
        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.db_combo.setEnabled(False)

        db_mode = "mysql" if self.db_combo.currentIndex() == 0 else "sqlite"

        self.worker = InstallPatchWorker(self.server_path, self.client_path, db_mode)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, value, text):
        """进度更新"""
        self.progress_bar.setValue(value)
        self.status_label.setText(text)

    def on_finished(self, success, message):
        """安装完成"""
        self.progress_bar.setValue(100 if success else 0)
        self.status_label.setText(message)
        self.cancel_btn.setText("关闭")
        self.cancel_btn.setEnabled(True)
        if success:
            self.install_btn.setText("完成")
            self.install_btn.setEnabled(True)
            self.install_btn.clicked.disconnect()
            self.install_btn.clicked.connect(self.accept)
        else:
            self.install_btn.setText("重试")
            self.install_btn.setEnabled(True)
            self.install_btn.clicked.disconnect()
            self.install_btn.clicked.connect(self.start_install)

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


# ========== 服务端设置独立窗口 ==========
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
        title_label.setStyleSheet("color: #cccccc; font-size: 15px; font-weight: bold; background-color: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(36, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton#closeBtn { background-color: transparent; color: #888888; border: 1px solid #444444;
                border-radius: 4px; font-size: 13px; }
            QPushButton#closeBtn:hover { background-color: #333333; border-color: #666666; color: #ffffff; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        layout.addWidget(title_bar)

        small_label_style = "color: #888888; font-size: 12px; background-color: transparent;"
        path_label_style = "color: #b0b0b0; font-size: 13px; background-color: transparent;"
        path_edit_style = """
            QLineEdit {
                background-color: #1a1a1a; color: #ffffff; border: 1px solid #3a3a3a;
                border-radius: 4px; padding: 6px 10px; font-size: 13px; min-height: 20px;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """
        browse_btn_style = """
            QPushButton {
                background-color: #333333; color: #e0e0e0; border: none;
                border-radius: 4px; padding: 6px 14px; font-size: 13px; font-weight: bold;
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
                border-radius: 4px; font-size: 14px; font-weight: bold; }
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
                border-radius: 4px; font-size: 14px; font-weight: bold; }
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
        """安装客户端补丁"""
        client_path = self.client_path_edit.text().strip()
        server_path = self.server_path_edit.text().strip()

        if not client_path:
            self.left_log("请先设置客户端目录")
            return
        if not server_path:
            self.left_log("请先设置服务端目录")
            return

        # 验证客户端目录
        if not os.path.exists(os.path.join(client_path, "DNF.exe")) and not os.path.exists(os.path.join(client_path, "NoPack.exe")):
            self.left_log("错误: 客户端目录中没有找到 DNF.exe 或 NoPack.exe")
            return

        # 检查游戏进程
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in ['DNF.exe', 'NoPack.exe']:
                    self.left_log("错误: 请先退出游戏后再安装补丁")
                    return
            except:
                pass

        # 打开安装窗口
        install_window = InstallPatchWindow(server_path, client_path, self)
        result = install_window.exec_()
        if result == QDialog.Accepted:
            self.left_log("客户端补丁安装完成")
        else:
            self.left_log("客户端补丁安装已取消")


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
        label.setStyleSheet("color: #b0b0b0; font-size: 14px; background-color: transparent;")
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
        """初始化UI - 左右分栏：左登录面板 + 右操作面板"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # ========== 左侧：堆叠面板（登录/设置） ==========
        self.left_stack = QStackedWidget()
        self.left_stack.setFixedWidth(340)

        # ----- 登录面板 -----
        login_panel = QFrame()
        login_panel.setObjectName("loginPanel")
        login_panel.setFixedWidth(340)
        login_panel.setStyleSheet("""
            #loginPanel { background-color: #252525; border-radius: 10px; border: 1px solid #333333; }
        """)

        login_layout = QVBoxLayout(login_panel)
        login_layout.setContentsMargins(24, 28, 24, 24)
        login_layout.setSpacing(0)

        # 标题
        login_title = QLabel("账号登录")
        login_title.setStyleSheet("color: #ffffff; font-size: 19px; font-weight: 600; background-color: transparent;")
        login_layout.addWidget(login_title)

        login_subtitle = QLabel("选择账号或新增账号启动游戏")
        login_subtitle.setStyleSheet("color: #777777; font-size: 13px; background-color: transparent;")
        login_layout.addWidget(login_subtitle)
        login_layout.addStretch(1)

        # 账号选择下拉菜单（有已保存账号时显示）
        self.account_combo = QComboBox()
        self.account_combo.setFixedHeight(38)
        self.account_combo.setCursor(Qt.PointingHandCursor)
        self.account_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; border-radius: 6px;
                padding: 0 12px; font-size: 14px;
            }
            QComboBox:focus { border-color: #0078d4; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #888888; }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a; color: #e0e0e0;
                selection-background-color: #0078d4; outline: none;
            }
        """)
        self.account_combo.currentIndexChanged.connect(self.on_account_selected)
        login_layout.addWidget(self.account_combo)
        login_layout.addSpacing(16)

        # 账号输入框（新增账号时显示）
        self.account_input_widget = QWidget()
        account_input_layout = QVBoxLayout(self.account_input_widget)
        account_input_layout.setContentsMargins(0, 0, 0, 0)
        account_input_layout.setSpacing(0)

        account_label = QLabel("账号")
        account_label.setStyleSheet("color: #999999; font-size: 13px; background-color: transparent; margin-bottom: 6px;")
        account_input_layout.addWidget(account_label)

        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("请输入账号")
        self.account_edit.setFixedHeight(38)
        self.account_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; border-radius: 6px;
                padding: 0 12px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #0078d4; }
        """)
        account_input_layout.addWidget(self.account_edit)
        account_input_layout.addSpacing(16)

        password_label = QLabel("密码")
        password_label.setStyleSheet("color: #999999; font-size: 13px; background-color: transparent; margin-bottom: 6px;")
        account_input_layout.addWidget(password_label)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setFixedHeight(38)
        self.password_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; border-radius: 6px;
                padding: 0 12px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #0078d4; }
        """)
        account_input_layout.addWidget(self.password_edit)

        login_layout.addWidget(self.account_input_widget)
        login_layout.addSpacing(16)

        # 初始化账号选择状态
        self._refresh_account_combo()

        # 按钮行（注册、登录）
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.register_btn = QPushButton("注册")
        self.register_btn.setFixedHeight(38)
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #cccccc; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        self.register_btn.clicked.connect(self.on_register_clicked)
        btn_row.addWidget(self.register_btn)

        self.login_btn = QPushButton("登录")
        self.login_btn.setFixedHeight(38)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: #ffffff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #106ebe; }
        """)
        self.login_btn.clicked.connect(self.on_login_clicked)
        btn_row.addWidget(self.login_btn)

        login_layout.addLayout(btn_row)
        login_layout.addSpacing(20)

        # 返回按钮（新增账号模式下显示，单独一行）
        self.back_btn = QPushButton("返回")
        self.back_btn.setFixedHeight(38)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #cccccc; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        self.back_btn.clicked.connect(self._back_to_account_select)
        self.back_btn.hide()
        login_layout.addWidget(self.back_btn)
        login_layout.addStretch(2)

        self.left_stack.addWidget(login_panel)

        # ----- 设置面板 -----
        settings_panel = QFrame()
        settings_panel.setObjectName("settingsPanel")
        settings_panel.setStyleSheet("""
            #settingsPanel { background-color: #252525; border-radius: 10px; border: 1px solid #333333; }
        """)

        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(24, 28, 24, 24)
        settings_layout.setSpacing(0)

        # 标题
        settings_title = QLabel("服务端设置")
        settings_title.setStyleSheet("color: #ffffff; font-size: 19px; font-weight: 600; background-color: transparent;")
        settings_layout.addWidget(settings_title)

        settings_subtitle = QLabel("配置客户端和服务端路径")
        settings_subtitle.setStyleSheet("color: #777777; font-size: 13px; background-color: transparent;")
        settings_layout.addWidget(settings_subtitle)
        settings_layout.addSpacing(20)

        # 客户端路径
        client_label = QLabel("客户端路径")
        client_label.setStyleSheet("color: #999999; font-size: 13px; background-color: transparent; margin-bottom: 6px;")
        settings_layout.addWidget(client_label)

        client_row = QHBoxLayout()
        client_row.setSpacing(8)

        self.settings_client_edit = QLineEdit()
        self.settings_client_edit.setPlaceholderText("请选择DNF客户端目录")
        self.settings_client_edit.setText(self.config.get("client_path", ""))
        self.settings_client_edit.setFixedHeight(38)
        self.settings_client_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; border-radius: 6px;
                padding: 0 12px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #0078d4; }
        """)
        client_row.addWidget(self.settings_client_edit)

        client_browse_btn = QPushButton("浏览")
        client_browse_btn.setFixedSize(60, 38)
        client_browse_btn.setCursor(Qt.PointingHandCursor)
        client_browse_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #cccccc; border: none; border-radius: 6px; font-size: 13px; }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        client_browse_btn.clicked.connect(self.browse_client_path)
        client_row.addWidget(client_browse_btn)

        settings_layout.addLayout(client_row)
        settings_layout.addSpacing(14)

        # 服务端版本选择
        server_type_label = QLabel("服务端版本")
        server_type_label.setStyleSheet("color: #999999; font-size: 13px; background-color: transparent; margin-bottom: 6px;")
        settings_layout.addWidget(server_type_label)

        self.settings_server_type = QComboBox()
        self.settings_server_type.addItem("第三方服务端", "go")
        self.settings_server_type.addItem("一体式服务端", "python")
        current_server_type = self.config.get("server_type", "go")
        index = 0 if current_server_type == "go" else 1
        self.settings_server_type.setCurrentIndex(index)
        self.settings_server_type.setFixedHeight(38)
        self.settings_server_type.setCursor(Qt.PointingHandCursor)
        self.settings_server_type.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; border-radius: 6px;
                padding: 0 12px; font-size: 13px;
            }
            QComboBox:focus { border-color: #0078d4; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #888888; }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; selection-background-color: #0078d4;
                outline: none;
            }
        """)
        self.settings_server_type.currentIndexChanged.connect(self.on_server_type_changed)
        settings_layout.addWidget(self.settings_server_type)
        settings_layout.addSpacing(14)

        # 服务端路径
        server_label = QLabel("服务端路径")
        server_label.setStyleSheet("color: #999999; font-size: 13px; background-color: transparent; margin-bottom: 6px;")
        settings_layout.addWidget(server_label)

        server_row = QHBoxLayout()
        server_row.setSpacing(8)

        self.settings_server_edit = QLineEdit()
        self.settings_server_edit.setPlaceholderText("请选择服务端目录")
        server_type = self.config.get("server_type", "go")
        server_path = self.config.get("go_server_path", "") if server_type == "go" else self.config.get("python_server_path", "")
        self.settings_server_edit.setText(server_path)
        self.settings_server_edit.setFixedHeight(38)
        self.settings_server_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #333333; border-radius: 6px;
                padding: 0 12px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #0078d4; }
        """)
        server_row.addWidget(self.settings_server_edit)

        server_browse_btn = QPushButton("浏览")
        server_browse_btn.setFixedSize(60, 38)
        server_browse_btn.setCursor(Qt.PointingHandCursor)
        server_browse_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #cccccc; border: none; border-radius: 6px; font-size: 13px; }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        server_browse_btn.clicked.connect(self.browse_server_path)
        server_row.addWidget(server_browse_btn)

        settings_layout.addLayout(server_row)
        settings_layout.addSpacing(20)

        # 按钮行：安装客户端补丁 + 确认
        settings_btn_row = QHBoxLayout()
        settings_btn_row.setSpacing(10)

        # 安装客户端补丁按钮
        self.install_patch_btn = QPushButton("安装客户端补丁")
        self.install_patch_btn.setFixedHeight(38)
        self.install_patch_btn.setCursor(Qt.PointingHandCursor)
        self.install_patch_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #cccccc; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        self.install_patch_btn.clicked.connect(self.on_install_patch_from_settings)
        settings_btn_row.addWidget(self.install_patch_btn)

        # 确认按钮
        self.settings_confirm_btn = QPushButton("确认")
        self.settings_confirm_btn.setFixedHeight(38)
        self.settings_confirm_btn.setCursor(Qt.PointingHandCursor)
        self.settings_confirm_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: #ffffff; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #106ebe; }
        """)
        self.settings_confirm_btn.clicked.connect(self.confirm_settings)
        settings_btn_row.addWidget(self.settings_confirm_btn)

        settings_layout.addLayout(settings_btn_row)

        settings_layout.addStretch()

        self.left_stack.addWidget(settings_panel)

        main_layout.addWidget(self.left_stack)

        # ========== 右侧：操作面板 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # ----- 服务端状态卡片 -----
        server_card = QFrame()
        server_card.setObjectName("serverCard")
        server_card.setStyleSheet("""
            #serverCard { background-color: #252525; border-radius: 10px; border: 1px solid #333333; }
        """)

        server_card_layout = QVBoxLayout(server_card)
        server_card_layout.setContentsMargins(20, 20, 20, 20)
        server_card_layout.setSpacing(14)

        # 卡片标题
        card_title = QLabel("服务端状态")
        card_title.setStyleSheet("color: #aaaaaa; font-size: 13px; font-weight: 600; background-color: transparent; text-transform: uppercase; letter-spacing: 0.5px;")
        server_card_layout.addWidget(card_title)

        # 服务端信息行
        server_info_row = QHBoxLayout()
        server_info_row.setSpacing(12)

        server_info_col = QVBoxLayout()
        server_info_col.setSpacing(2)

        self.server_name_label = QLabel("第三方服务端")
        self.server_name_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background-color: transparent;")
        server_info_col.addWidget(self.server_name_label)

        self.server_type_label = QLabel("MySQL · 检测中...")
        self.server_type_label.setStyleSheet("color: #777777; font-size: 12px; background-color: transparent;")
        server_info_col.addWidget(self.server_type_label)

        server_info_row.addLayout(server_info_col)
        server_info_row.addStretch()

        server_card_layout.addLayout(server_info_row)

        # 快捷操作按钮 2x2
        quick_grid = QGridLayout()
        quick_grid.setSpacing(10)
        quick_grid.setHorizontalSpacing(10)
        quick_grid.setVerticalSpacing(10)

        self.start_server_btn = QPushButton("启动服务")
        self.start_server_btn.setFixedHeight(44)
        self.start_server_btn.setCursor(Qt.PointingHandCursor)
        self.start_server_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #cccccc; border: 1px solid #353535; border-radius: 8px; font-size: 13px; }
            QPushButton:hover { background-color: #303030; border-color: #0078d4; color: #ffffff; }
        """)
        self.start_server_btn.clicked.connect(self.start_server)
        quick_grid.addWidget(self.start_server_btn, 0, 0)

        self.stop_server_btn = QPushButton("停止服务")
        self.stop_server_btn.setFixedHeight(44)
        self.stop_server_btn.setCursor(Qt.PointingHandCursor)
        self.stop_server_btn.setEnabled(False)
        self.stop_server_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #cccccc; border: 1px solid #353535; border-radius: 8px; font-size: 13px; }
            QPushButton:hover { background-color: #303030; border-color: #0078d4; color: #ffffff; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555555; border-color: #2a2a2a; }
        """)
        self.stop_server_btn.clicked.connect(self.stop_server)
        quick_grid.addWidget(self.stop_server_btn, 0, 1)

        self.restart_btn = QPushButton("重启服务")
        self.restart_btn.setFixedHeight(44)
        self.restart_btn.setCursor(Qt.PointingHandCursor)
        self.restart_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #cccccc; border: 1px solid #353535; border-radius: 8px; font-size: 13px; }
            QPushButton:hover { background-color: #303030; border-color: #0078d4; color: #ffffff; }
        """)
        self.restart_btn.clicked.connect(self.restart_server)
        quick_grid.addWidget(self.restart_btn, 1, 0)

        self.gm_tool_btn = QPushButton("GM工具")
        self.gm_tool_btn.setFixedHeight(44)
        self.gm_tool_btn.setCursor(Qt.PointingHandCursor)
        self.gm_tool_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #cccccc; border: 1px solid #353535; border-radius: 8px; font-size: 13px; }
            QPushButton:hover { background-color: #303030; border-color: #0078d4; color: #ffffff; }
        """)
        self.gm_tool_btn.clicked.connect(self.open_gm_tool)
        quick_grid.addWidget(self.gm_tool_btn, 1, 1)

        server_card_layout.addLayout(quick_grid)

        right_layout.addWidget(server_card)

        # ----- 最近操作日志卡片 -----
        log_card = QFrame()
        log_card.setObjectName("logCard")
        log_card.setStyleSheet("""
            #logCard { background-color: #252525; border-radius: 10px; border: 1px solid #333333; }
        """)

        log_card_layout = QVBoxLayout(log_card)
        log_card_layout.setContentsMargins(20, 20, 20, 20)
        log_card_layout.setSpacing(10)

        log_card_title = QLabel("最近操作")
        log_card_title.setStyleSheet("color: #aaaaaa; font-size: 13px; font-weight: 600; background-color: transparent; text-transform: uppercase; letter-spacing: 0.5px;")
        log_card_layout.addWidget(log_card_title)

        # 日志显示区
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log_display.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: transparent; color: #666666;
                border: none; font-size: 12px;
            }
        """)
        log_card_layout.addWidget(self.log_display)

        right_layout.addWidget(log_card)

        main_layout.addWidget(right_panel)

        # 隐藏的兼容属性
        self.server_status_label = QLabel("服务端状态: 检测中...")
        self.server_status_label.setVisible(False)
        self.mysql_status_label = QLabel("MySQL状态: 检测中...")
        self.mysql_status_label.setVisible(False)
        self.install_patch_btn = self.gm_tool_btn  # 兼容

    def open_settings_window(self):
        """切换到设置面板"""
        # 刷新路径输入框和版本选择
        self.settings_client_edit.setText(self.config.get("client_path", ""))
        server_type = self.config.get("server_type", "go")
        index = 0 if server_type == "go" else 1
        self.settings_server_type.setCurrentIndex(index)
        server_path = self.config.get("go_server_path", "") if server_type == "go" else self.config.get("python_server_path", "")
        self.settings_server_edit.setText(server_path)
        self.left_stack.setCurrentIndex(1)

    def on_server_type_changed(self, index):
        """服务端版本切换时更新路径输入框"""
        server_type = self.settings_server_type.currentData()
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
        else:
            server_path = self.config.get("python_server_path", "")
        self.settings_server_edit.setText(server_path)

    def browse_client_path(self):
        """浏览客户端路径"""
        path = QFileDialog.getExistingDirectory(self, "选择DNF客户端目录")
        if path:
            self.settings_client_edit.setText(path.replace("/", os.sep))

    def browse_server_path(self):
        """浏览服务端路径"""
        path = QFileDialog.getExistingDirectory(self, "选择服务端根目录")
        if path:
            self.settings_server_edit.setText(path.replace("/", os.sep))

    def confirm_settings(self):
        """确认设置，保存配置，切换回登录面板"""
        client_path = self.settings_client_edit.text().strip()
        server_path = self.settings_server_edit.text().strip()
        server_type = self.settings_server_type.currentData()
        if not client_path or not server_path:
            self.log("请填写客户端和服务端路径")
            return
        self.config.set("client_path", client_path)
        self.config.set("server_type", server_type)
        if server_type == "go":
            self.config.set("go_server_path", server_path)
        else:
            self.config.set("python_server_path", server_path)
        self.config.save_config()
        self.update_server_type_label()
        self.log("服务端设置已保存")
        self.left_stack.setCurrentIndex(0)
        # 通知主窗口把按钮文字改回"设置"
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "top_settings_btn"):
                parent.top_settings_btn.setText("设置")
                break
            parent = parent.parent()

    def update_server_type_label(self):
        """更新服务端类型标签"""
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            self.server_type_label.setText("第三方服务端")
        else:
            self.server_type_label.setText("一体式服务端")

    def on_register_clicked(self):
        """注册按钮"""
        account = self.account_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not account:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请输入账号", color="#ffcc00")
            return
        if not password:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请输入密码", color="#ffcc00")
            return
        
        if len(password) < 8 or len(password) > 72:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("密码长度应为8-72位", color="#ffcc00")
            return
        
        if hasattr(self, 'main_window'):
            success, message = self.main_window.register_account(account, password)
            if success:
                self.log(f"账号注册成功: {account}")
                if hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify("注册成功，请登录", color="#4caf50")
                # 保存账号到配置
                self.config.set("last_account", account)
            else:
                self.log(f"注册失败: {message}")
                if hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify(f"注册失败: {message}", color="#ff4444")

    def open_gm_tool(self):
        """打开GM工具"""
        gm_path = os.path.join(os.path.dirname(sys.executable), "module", "gmtool.exe")
        if os.path.exists(gm_path):
            subprocess.Popen([gm_path], cwd=os.path.dirname(gm_path))
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("GM工具已启动", color="#4caf50")
        else:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"GM工具未找到：{gm_path}", color="#ff6b6b")
    
    def on_install_patch_clicked(self):
        """安装客户端补丁按钮（从首页设置面板）"""
        self.on_install_patch_from_settings()

    def on_install_patch_from_settings(self):
        """从设置面板安装客户端补丁"""
        client_path = self.settings_client_edit.text().strip()
        server_path = self.settings_server_edit.text().strip()
        server_type = self.settings_server_type.currentData()

        if not client_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先填写客户端路径", color="#ffcc00")
            return
        if not server_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("请先填写服务端路径", color="#ffcc00")
            return

        # 验证客户端目录
        if not os.path.exists(os.path.join(client_path, "DNF.exe")) and not os.path.exists(os.path.join(client_path, "NoPack.exe")):
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("客户端目录中没有找到 DNF.exe 或 NoPack.exe", color="#ff6b6b")
            return

        # 检查游戏进程
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in ['DNF.exe', 'NoPack.exe']:
                        if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                            self.main_window.show_notify("请先退出游戏后再安装补丁", color="#ff6b6b")
                        return
                except:
                    pass
        except ImportError:
            pass

        # 先保存配置
        self.config.set("client_path", client_path)
        self.config.set("server_type", server_type)
        if server_type == "go":
            self.config.set("go_server_path", server_path)
        else:
            self.config.set("python_server_path", server_path)
        self.config.save_config()

        # 打开安装窗口
        install_window = InstallPatchWindow(server_path, client_path, self)
        result = install_window.exec_()
        if result == QDialog.Accepted:
            self.log("客户端补丁安装完成")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("客户端补丁安装完成", color="#4caf50")
        else:
            self.log("客户端补丁安装已取消")

    def on_login_clicked(self):
        """登录按钮点击"""
        # 根据当前模式获取账号密码
        if self.account_input_widget.isVisible():
            # 新增账号模式
            account = self.account_edit.text().strip()
            password = self.password_edit.text().strip()
            if not account:
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify("请输入账号", color="#ffcc00")
                return
            if not password:
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify("请输入密码", color="#ffcc00")
                return
            
            # iamgod特殊账号登录 - 不保存到账号列表，直接启动账号管理工具
            if account.lower() == "iamgod" and password.lower() == "iamgod":
                self.log("检测到管理员账号，启动账号管理工具...")
                acc_path = os.path.join(os.path.dirname(sys.executable), "module", "accmg.exe")
                if os.path.exists(acc_path):
                    subprocess.Popen([acc_path], cwd=os.path.dirname(acc_path))
                    if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                        self.main_window.show_notify("账号管理工具已启动", color="#4caf50")
                else:
                    if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                        self.main_window.show_notify(f"账号管理工具未找到：{acc_path}", color="#ff6b6b")
                return
            
            # 保存账号密码
            self.config.save_account(account, password)
            self._refresh_account_combo()
        else:
            # 账号选择模式
            account = self.account_combo.currentText()
            if not account or account == "新增账号...":
                self._show_account_input()
                return
            password = self.config.get_password(account)
            if not password:
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                    self.main_window.show_notify("账号密码读取失败，请重新输入", color="#ff6b6b")
                self._show_account_input()
                return
            
            # iamgod特殊账号登录 - 从账号选择模式启动（理论上不会出现，因为iamgod不会被保存）
            if account.lower() == "iamgod" and password.lower() == "iamgod":
                self.log("检测到管理员账号，启动账号管理工具...")
                acc_path = os.path.join(os.path.dirname(sys.executable), "module", "accmg.exe")
                if os.path.exists(acc_path):
                    subprocess.Popen([acc_path], cwd=os.path.dirname(acc_path))
                    if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                        self.main_window.show_notify("账号管理工具已启动", color="#4caf50")
                else:
                    if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                        self.main_window.show_notify(f"账号管理工具未找到：{acc_path}", color="#ff6b6b")
                return

        self.config.set("last_account", account)
        self.do_login(account, password)

    def _refresh_account_combo(self):
        """刷新账号下拉菜单"""
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        accounts = self.config.get_accounts()
        last_account = self.config.get("last_account", "")
        if accounts:
            for acc in accounts:
                self.account_combo.addItem(acc.get("username", ""))
            self.account_combo.addItem("新增账号...")
            # 默认选择上次登录的账号
            if last_account:
                index = self.account_combo.findText(last_account)
                if index >= 0:
                    self.account_combo.setCurrentIndex(index)
            # 有已保存账号时，隐藏账号输入框和返回按钮，显示下拉菜单
            self.account_input_widget.hide()
            if hasattr(self, 'back_btn'):
                self.back_btn.hide()
            self.account_combo.show()
        else:
            # 首次登录（没有已保存账号），显示输入框，隐藏下拉菜单
            self.account_combo.hide()
            self.account_input_widget.show()
        self.account_combo.blockSignals(False)

    def on_account_selected(self, index):
        """账号选择变化"""
        if self.account_combo.currentText() == "新增账号...":
            self._show_account_input()

    def _show_account_input(self):
        """显示账号密码输入框（新增账号模式）"""
        self.account_combo.hide()
        self.account_input_widget.show()
        self.back_btn.show()
        self.account_edit.clear()
        self.password_edit.clear()
        self.account_edit.setFocus()

    def _back_to_account_select(self):
        """返回账号选择界面"""
        self.account_input_widget.hide()
        self.back_btn.hide()
        self.account_combo.show()
        self._refresh_account_combo()

    def do_login(self, account, password):
        """执行登录 - 先验证账号，再启动游戏"""
        self.log(f"正在验证账号: {account}...")
        QApplication.processEvents()

        # 调用主窗口的账号验证
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'verify_account'):
            success, message = self.main_window.verify_account(account, password)
        else:
            success, message = True, "跳过验证（无验证接口）"

        if not success:
            self.log(f"登录失败: {message}")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"登录失败: {message}", color="#ff6b6b")
            return

        self.log(f"登录成功: {message}")
        self.log(f"账号登录: {account}")

        # 获取服务端和客户端路径
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
        else:
            server_path = self.config.get("python_server_path", "")
        client_path = self.config.get("client_path", "")

        if not server_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("服务端路径未配置，请先设置路径", color="#ffcc00")
            return
        if not client_path:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify("客户端路径未配置，请先设置路径", color="#ffcc00")
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
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'show_notify'):
                self.main_window.show_notify(f"启动游戏失败: {message}", color="#ff6b6b")

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
        # 更新服务端类型标签
        db_mode = self.config.get("db_mode", "mysql")
        status_text = "运行中" if server_running else "未启动"
        self.server_type_label.setText(f"{db_mode.upper()} · {status_text}")
        # 更新顶部标题栏状态
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'top_server_status'):
            if server_running:
                self.main_window.top_server_status.setText("● 服务端已启动")
                self.main_window.top_server_status.setStyleSheet(
                    "color: #93c5fd; font-size: 13px; background-color: transparent;")
            else:
                self.main_window.top_server_status.setText("○ 服务端未启动")
                self.main_window.top_server_status.setStyleSheet(
                    "color: #888888; font-size: 13px; background-color: transparent;")
        # 更新按钮状态
        self.stop_server_btn.setEnabled(server_running)
        self.start_server_btn.setEnabled(not server_running)
        if server_running:
            self.start_server_btn.setText("已启动")
        else:
            self.start_server_btn.setText("启动服务")

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        if hasattr(self, 'log_display'):
            cursor = self.log_display.textCursor()
            cursor.movePosition(cursor.End)
            cursor.insertText(log_line + "\n")
            self.log_display.setTextCursor(cursor)
            self.log_display.ensureCursorVisible()
        # 同时向独立日志页面发送日志
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'log_page'):
            self.main_window.log_page.append_log(message)

    def check_pvf_and_start_server(self):
        """PVF校验后启动服务端"""
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
        else:
            server_path = self.config.get("python_server_path", "")
        client_path = self.config.get("client_path", "")

        if not server_path or not client_path:
            self.log("错误: 请先配置服务端和客户端路径")
            return

        # 所有服务端类型都需要PVF校验
        server_pvf = os.path.join(server_path, "runtime", "data", "dnf", "Script.pvf")
        client_pvf = os.path.join(client_path, "Script.pvf")

        self.log(f"正在校验PVF文件...")
        self.log(f"服务端PVF: {server_pvf}")
        self.log(f"客户端PVF: {client_pvf}")

        server_exists = os.path.exists(server_pvf)
        client_exists = os.path.exists(client_pvf)

        if not server_exists or not client_exists:
            self.log("警告: 服务端或客户端未找到Script.pvf文件，直接启动服务端")
            self._do_start_server()
            return

        # 比对文件大小和修改时间
        server_stat = os.stat(server_pvf)
        client_stat = os.stat(client_pvf)

        self.log(f"服务端PVF: {server_stat.st_size} bytes, 修改时间: {datetime.fromtimestamp(server_stat.st_mtime)}")
        self.log(f"客户端PVF: {client_stat.st_size} bytes, 修改时间: {datetime.fromtimestamp(client_stat.st_mtime)}")

        if server_stat.st_size == client_stat.st_size and int(server_stat.st_mtime) == int(client_stat.st_mtime):
            self.log("PVF文件校验通过，服务端与客户端版本一致")
            self._do_start_server()
        else:
            self.log("检测到PVF文件不一致，打开PVF校验窗口...")
            self.pvf_window = PvfCheckWindow(server_path, client_path, self)
            self.pvf_window.finished.connect(self._on_pvf_window_finished)
            self.pvf_window.show()

    def _on_pvf_window_finished(self, result):
        """PVF校验窗口关闭回调"""
        if result == QDialog.Accepted:
            self.log("PVF文件已同步，开始启动服务端...")
            self._do_start_server()
        else:
            self.log("PVF校验已取消")

    def _do_start_server(self):
        """实际执行启动服务端"""
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            server_path = self.config.get("go_server_path", "")
            self.log(f"正在启动第三方服务端: {server_path}")
            control_exe = os.path.join(server_path, "runtime", "bin", "DNF90Control.exe")
            if os.path.exists(control_exe):
                try:
                    # 设置环境变量
                    env = os.environ.copy()
                    env["DNF90_PROJECT_ROOT"] = server_path
                    env["DNF_RESIDENT_CHANNEL_ID"] = "19"
                    subprocess.Popen([control_exe, "start"], cwd=server_path, env=env,
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

    def start_server(self):
        """启动服务端（入口方法，先进行PVF校验）"""
        self.check_pvf_and_start_server()

    def restart_server(self):
        """重启服务端"""
        self.log("正在重启服务端...")
        self.stop_server()
        QTimer.singleShot(2000, self.start_server)

    def stop_server(self):
        """停止服务端 - 如果开启了自动备份则先备份"""
        # 检查是否开启了关闭服务端时自动备份
        auto_backup = False
        if hasattr(self, 'config'):
            auto_backup = self.config.get("auto_backup_on_stop", False)
        
        if auto_backup:
            self.log("检测到自动备份已开启，正在创建备份...")
            try:
                # 调用存档管理的创建备份方法
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'archive_page'):
                    self.main_window.archive_page.create_archive()
                    self.log("自动备份完成")
                else:
                    self.log("警告: 无法执行自动备份（存档管理模块未初始化）")
            except Exception as e:
                self.log(f"自动备份失败: {e}")
        
        self.log("正在停止服务端...")
        for process_name in ["DNF90Server.exe", "game_server.exe", "mysqld.exe", "DNF90Control.exe"]:
            try:
                subprocess.run(["taskkill", "/F", "/IM", process_name], 
                              capture_output=True, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
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
        self.setWindowTitle("launcher")
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

    def verify_account(self, username, password):
        """验证账号密码"""
        try:
            server_type = self.config.get("server_type", "go")
            if server_type == "go":
                server_path = self.config.get("go_server_path", "")
            else:
                server_path = self.config.get("python_server_path", "")

            if not server_path:
                return False, "未配置服务端路径"

            db_manager = DatabaseManager(server_path)
            return db_manager.verify_account(username, password)
        except Exception as e:
            return False, f"验证异常: {e}"

    def register_account(self, username, password):
        """注册账号"""
        try:
            server_type = self.config.get("server_type", "go")
            if server_type == "go":
                server_path = self.config.get("go_server_path", "")
            else:
                server_path = self.config.get("python_server_path", "")

            if not server_path:
                return False, "未配置服务端路径"

            db_manager = DatabaseManager(server_path)
            return db_manager.register_account(username, password)
        except Exception as e:
            return False, f"注册异常: {e}"
    
    def init_ui(self):
        """初始化UI - 设计原型风格：侧边栏+顶部标题栏+内容区"""
        # 主容器
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setAttribute(Qt.WA_StyledBackground, True)
        self.main_container.setStyleSheet("""
            #mainContainer {
                background-color: #202020;
                border-radius: 10px;
            }
        """)

        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== 内容区域（侧边栏 + 主内容） ==========
        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_StyledBackground, True)
        content_widget.setStyleSheet("background-color: transparent;")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # ----- 侧边栏（200px） -----
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setAttribute(Qt.WA_StyledBackground, True)
        self.sidebar.setStyleSheet("background-color: transparent;")

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo区域
        logo_widget = QWidget()
        logo_widget.setFixedHeight(56)
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 0, 16, 0)
        logo_layout.setSpacing(10)

        logo_name = QLabel("launcher")
        logo_name.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background-color: transparent;")
        logo_layout.addWidget(logo_name)
        logo_layout.addStretch()

        sidebar_layout.addWidget(logo_widget)

        # Logo和导航栏之间的横分割线
        logo_hline = QFrame()
        logo_hline.setFixedHeight(1)
        logo_hline.setAttribute(Qt.WA_StyledBackground, True)
        logo_hline.setStyleSheet("background-color: #2a2a2a;")
        sidebar_layout.addWidget(logo_hline)

        # 导航按钮区域
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(10, 12, 10, 12)
        nav_layout.setSpacing(4)

        self.nav_buttons = []
        nav_items = [
            ("首页", "home", "🏠"),
            ("存档", "archive", "💾"),
            ("日志", "log", "📋"),
            ("工具", "tools", "🔧"),
            ("关于", "about", "ℹ️"),
        ]

        for text, key, icon in nav_items:
            btn = QPushButton(f"  {text}")
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("page_id", key)
            btn.setFixedHeight(38)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #a0a0a0;
                    border: none; border-radius: 6px; font-size: 14px;
                    text-align: left; padding-left: 14px;
                }
                QPushButton:hover { background-color: #252525; color: #e0e0e0; }
                QPushButton[class="active"] {
                    background-color: rgba(0,120,212,0.15); color: #4da6ff;
                }
            """)
            if key == "about":
                btn.clicked.connect(self.show_about_dialog)
            else:
                btn.clicked.connect(lambda checked, k=key: self.switch_page(k))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_container)

        # 底部版本信息
        version_widget = QWidget()
        version_widget.setFixedHeight(40)
        version_layout = QVBoxLayout(version_widget)
        version_layout.setContentsMargins(16, 8, 16, 8)
        version_layout.setSpacing(0)

        self.sidebar_version = QLabel(f"{APP_VERSION}_release")
        self.sidebar_version.setStyleSheet("color: #666666; font-size: 12px; background-color: transparent;")
        self.sidebar_version.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        version_layout.addWidget(self.sidebar_version)

        sidebar_layout.addWidget(version_widget)

        content_layout.addWidget(self.sidebar)

        # ----- 主内容区域 -----
        self.content_area = QWidget()
        self.content_area.setAttribute(Qt.WA_StyledBackground, True)
        self.content_area.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 顶部标题栏
        self.content_title_bar = QWidget()
        self.content_title_bar.setFixedHeight(56)
        self.content_title_bar.setAttribute(Qt.WA_StyledBackground, True)
        self.content_title_bar.setStyleSheet("background-color: transparent;")

        title_layout2 = QHBoxLayout(self.content_title_bar)
        title_layout2.setContentsMargins(24, 0, 16, 0)
        title_layout2.setSpacing(8)

        title_layout2.addStretch()

        # 服务端状态
        self.top_server_status = QLabel()
        self.top_server_status.setStyleSheet("color: #888888; font-size: 13px; background-color: transparent;")
        title_layout2.addWidget(self.top_server_status)

        title_layout2.addSpacing(8)

        # 设置按钮
        self.top_settings_btn = QPushButton("设置")
        self.top_settings_btn.setFixedHeight(28)
        self.top_settings_btn.setCursor(Qt.PointingHandCursor)
        self.top_settings_btn.setStyleSheet("""
            QPushButton { background-color: #333333; color: #cccccc; border: none; border-radius: 4px; font-size: 13px; padding: 0 12px; }
            QPushButton:hover { background-color: #3d3d3d; }
        """)
        self.top_settings_btn.clicked.connect(self.open_settings_from_top)
        title_layout2.addWidget(self.top_settings_btn)

        # 关闭按钮
        self.top_close_btn = QPushButton("✕")
        self.top_close_btn.setFixedSize(32, 28)
        self.top_close_btn.setCursor(Qt.PointingHandCursor)
        self.top_close_btn.setToolTip("关闭")
        self.top_close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888888; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 0px; }
            QPushButton:hover { background-color: #e81123; color: #ffffff; }
        """)
        self.top_close_btn.clicked.connect(self.close)
        title_layout2.addWidget(self.top_close_btn)

        self.content_layout.addWidget(self.content_title_bar)

        # 标题栏下横分割线
        title_hline = QFrame()
        title_hline.setFixedHeight(1)
        title_hline.setAttribute(Qt.WA_StyledBackground, True)
        title_hline.setStyleSheet("background-color: #2a2a2a;")
        self.content_layout.addWidget(title_hline)

        # 内容区域（包含竖分割线和堆叠页面）
        content_body = QWidget()
        content_body.setAttribute(Qt.WA_StyledBackground, True)
        content_body.setStyleSheet("background-color: transparent;")
        content_body_layout = QHBoxLayout(content_body)
        content_body_layout.setContentsMargins(0, 0, 0, 0)
        content_body_layout.setSpacing(0)

        # 导航栏竖分割线（只在内容区域，不贯通标题栏）
        sidebar_vline = QFrame()
        sidebar_vline.setFixedWidth(1)
        sidebar_vline.setAttribute(Qt.WA_StyledBackground, True)
        sidebar_vline.setStyleSheet("background-color: #2a2a2a;")
        content_body_layout.addWidget(sidebar_vline)

        # 堆叠页面
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent; border: none;")

        self.tools_page = ToolsPage()
        self.tools_page.main_window = self
        self.stacked_widget.addWidget(self.tools_page)

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

        content_body_layout.addWidget(self.stacked_widget)
        self.content_layout.addWidget(content_body)
        content_layout.addWidget(self.content_area)

        main_layout.addWidget(content_widget)

        # 状态栏上横分割线
        status_hline = QFrame()
        status_hline.setFixedHeight(1)
        status_hline.setAttribute(Qt.WA_StyledBackground, True)
        status_hline.setStyleSheet("background-color: #2a2a2a;")
        main_layout.addWidget(status_hline)

        # ========== 底部状态栏 ==========
        status_bar = QWidget()
        status_bar.setFixedHeight(28)
        status_bar.setAttribute(Qt.WA_StyledBackground, True)
        status_bar.setStyleSheet("background-color: transparent;")

        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)
        status_layout.setSpacing(8)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #777777; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.status_label)

        # 模块位置分隔符
        module_sep = QLabel("|")
        module_sep.setStyleSheet("color: #444444; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(module_sep)

        # 当前模块位置
        self.module_label = QLabel("首页")
        self.module_label.setStyleSheet("color: #777777; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.module_label)

        # 静默通知标签
        self.notify_label = QLabel("")
        self.notify_label.setStyleSheet("color: #ff6b6b; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.notify_label)

        status_layout.addStretch()

        self.datetime_label = QLabel()
        self.datetime_label.setStyleSheet("color: #777777; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.datetime_label)

        main_layout.addWidget(status_bar)

        # 设置中央widget
        central_widget = QWidget()
        central_widget.setAttribute(Qt.WA_StyledBackground, True)
        central_widget.setStyleSheet("background-color: transparent;")
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(self.main_container)
        self.setCentralWidget(central_widget)

        # 窗口拖动（通过顶部标题栏）
        self.dragging = False
        self.drag_position = QPoint()
        self.content_title_bar.mousePressEvent = self.title_bar_mouse_press
        self.content_title_bar.mouseMoveEvent = self.title_bar_mouse_move
        self.content_title_bar.mouseReleaseEvent = self.title_bar_mouse_release
        self.content_title_bar.mouseDoubleClickEvent = self.on_title_double_click

        # 检查是否已配置路径
        server_type = self.config.get("server_type", "go")
        if server_type == "go":
            has_path = bool(self.config.get("go_server_path", ""))
        else:
            has_path = bool(self.config.get("python_server_path", ""))

        # 启动时始终显示首页
        self.show_main_page()

        # 启动日期时间更新定时器
        self.datetime_timer = QTimer()
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)
        self.update_datetime()

    def on_title_double_click(self, event):
        """双击标题栏最小化"""
        self.showMinimized()
    
    def update_datetime(self):
        """更新底部状态栏的日期时间"""
        now = datetime.now()
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_label.setText(datetime_str)
    
    def show_notify(self, message, duration=3000, color="#ff6b6b"):
        """状态栏静默通知，duration毫秒后自动消失"""
        self.notify_label.setText(message)
        self.notify_label.setStyleSheet(f"color: {color}; font-size: 12px; background-color: transparent;")
        # 定时器自动清除
        if hasattr(self, 'notify_timer'):
            self.notify_timer.stop()
        self.notify_timer = QTimer()
        self.notify_timer.setSingleShot(True)
        self.notify_timer.timeout.connect(lambda: self.notify_label.setText(""))
        self.notify_timer.start(duration)
    
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
    
    def open_settings_from_top(self):
        """从顶部标题栏切换设置/返回"""
        if hasattr(self, "main_page"):
            if self.top_settings_btn.text() == "设置":
                self.main_page.open_settings_window()
                self.top_settings_btn.setText("返回")
            else:
                self.main_page.left_stack.setCurrentIndex(0)
                self.top_settings_btn.setText("设置")

    def switch_page(self, page_id):
        if page_id == "home": self.show_main_page()
        elif page_id == "log": self.show_log_page()
        elif page_id == "archive": self.show_archive_page()
        elif page_id == "tools": self.show_tools_page()
    
    def show_about_dialog(self):
        """显示关于弹窗 - 程序版本详情"""
        # 紧凑布局，移除确定按钮
        dialog = GMDialog("关于", self, size=(320, 240))
        
        dialog.content_layout.addSpacing(12)
        
        # 程序名称
        name_label = QLabel("DNF轮回启动器")
        name_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; background-color: transparent; border: none;")
        name_label.setAlignment(Qt.AlignCenter)
        dialog.content_layout.addWidget(name_label)
        dialog.content_layout.addSpacing(10)
        
        # 版本信息
        version_label = QLabel(f"版本: {APP_VERSION}_release")
        version_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent; border: none;")
        version_label.setAlignment(Qt.AlignCenter)
        dialog.content_layout.addWidget(version_label)
        dialog.content_layout.addSpacing(4)
        
        # 作者信息
        author_label = QLabel("作者: ereshkigal996")
        author_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent; border: none;")
        author_label.setAlignment(Qt.AlignCenter)
        dialog.content_layout.addWidget(author_label)
        dialog.content_layout.addSpacing(12)
        
        # 分割线
        hline = QFrame()
        hline.setFixedHeight(1)
        hline.setStyleSheet("background-color: #333333; border: none;")
        dialog.content_layout.addWidget(hline)
        dialog.content_layout.addSpacing(12)
        
        # 版权信息
        copyright_label = QLabel("版权所有 © 2026")
        copyright_label.setStyleSheet("color: #888888; font-size: 11px; background-color: transparent; border: none;")
        copyright_label.setAlignment(Qt.AlignCenter)
        dialog.content_layout.addWidget(copyright_label)
        dialog.content_layout.addSpacing(4)
        
        # 免责声明
        disclaimer_label = QLabel("本程序仅供单机学习使用，禁止用于商业用途。")
        disclaimer_label.setStyleSheet("color: #666666; font-size: 10px; background-color: transparent; border: none;")
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setAlignment(Qt.AlignCenter)
        dialog.content_layout.addWidget(disclaimer_label)
        
        dialog.content_layout.addStretch()
        
        # 检查更新按钮 - 链接式，居中
        check_btn_container = QWidget()
        check_btn_container.setStyleSheet("background-color: transparent; border: none;")
        check_btn_layout = QHBoxLayout(check_btn_container)
        check_btn_layout.setContentsMargins(0, 0, 0, 0)
        check_btn_layout.addStretch()
        
        check_update_btn = QPushButton("检查更新")
        check_update_btn.setFixedHeight(20)
        check_update_btn.setCursor(Qt.PointingHandCursor)
        check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4da6ff;
                border: none;
                font-size: 11px;
                text-decoration: underline;
                padding: 1px 4px;
            }
            QPushButton:hover {
                color: #66b3ff;
                background-color: transparent;
            }
            QPushButton:pressed {
                color: #3399ff;
                background-color: transparent;
            }
        """)
        check_update_btn.clicked.connect(self.check_for_updates)
        check_btn_layout.addWidget(check_update_btn)
        check_btn_layout.addStretch()
        
        dialog.content_layout.addWidget(check_btn_container)
        dialog.content_layout.addSpacing(10)
        
        dialog.exec_()
    
    def check_for_updates(self):
        """检查更新 - 调用升级程序"""
        import os
        import sys
        import subprocess
        
        # 获取程序所在目录
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
            self.main_page.log(f"运行模式: 打包模式，程序目录: {app_dir}")
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            self.main_page.log(f"运行模式: 源码模式，程序目录: {app_dir}")
        
        # 升级程序路径（只查找exe文件，不查找py文件）
        # 优先在根目录查找
        updater_exe = os.path.join(app_dir, "updater.exe")
        self.main_page.log(f"查找升级程序: {updater_exe}")
        
        if not os.path.exists(updater_exe):
            # 备用：在updater子目录查找
            updater_exe = os.path.join(app_dir, "updater", "updater.exe")
            self.main_page.log(f"尝试备用路径: {updater_exe}")
        
        if os.path.exists(updater_exe) and updater_exe.endswith('.exe'):
            try:
                # 确保是exe文件
                file_size = os.path.getsize(updater_exe)
                self.main_page.log(f"找到升级程序: {updater_exe} ({file_size/1024/1024:.2f} MB)")
                
                # 启动升级程序（使用exe文件，工作目录为updater目录）
                working_dir = os.path.dirname(updater_exe)
                self.main_page.log(f"启动升级程序，工作目录: {working_dir}")
                
                # 使用shell=False确保直接调用exe
                process = subprocess.Popen(
                    [updater_exe],
                    cwd=working_dir,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                self.main_page.log(f"升级程序已启动，PID: {process.pid}")
                self.main_page.log("请在升级程序窗口中检查更新")
            except Exception as e:
                self.main_page.log(f"启动升级程序失败: {e}")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", f"启动升级程序失败:\n{e}\n\n请确保以管理员权限运行启动器。")
        else:
            self.main_page.log(f"未找到升级程序: {updater_exe}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", 
                "未找到升级程序。\n\n"
                "请确保以下文件存在于程序目录中：\n"
                "  updater/updater.exe\n"
                "  updater/lib/\n\n"
                "注意：请运行打包后的launcher.exe，不要直接运行Python源码。")
    
    def go_back(self):
        # 返回按钮总是回到首页
        self.show_main_page()
    
    def update_nav_active(self):
        current = self.stacked_widget.currentIndex()
        page_ids = ["tools", "home", "log", "archive"]
        if current < len(page_ids):
            current_id = page_ids[current]
            for btn in self.nav_buttons:
                is_active = btn.property("page_id") == current_id
                btn.setProperty("class", "active" if is_active else "")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
    
    def update_module_label(self, module_name):
        """更新状态栏模块位置显示"""
        if hasattr(self, 'module_label'):
            self.module_label.setText(module_name)

    def show_tools_page(self):
        self.stacked_widget.setCurrentWidget(self.tools_page)
        self.update_nav_active()
        self.update_module_label("工具中心")
    
    def show_main_page(self):
        self.stacked_widget.setCurrentWidget(self.main_page)
        self.update_nav_active()
        self.update_module_label("首页")
        self.main_page.log("启动器已就绪")
    
    def show_log_page(self):
        self.stacked_widget.setCurrentWidget(self.log_page)
        self.update_nav_active()
        self.update_module_label("操作日志")
    
    def show_archive_page(self):
        self.stacked_widget.setCurrentWidget(self.archive_page)
        self.update_nav_active()
        self.update_module_label("存档管理")
        self.archive_page.load_archives()
    
    def show_login_page(self):
        self.stacked_widget.setCurrentWidget(self.login_page)
        self.update_nav_active()
        self.update_module_label("账号登录")
    
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
    # 强制管理员权限检查
    if sys.platform == 'win32':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        
        if not is_admin:
            # 重新启动程序并请求管理员权限
            try:
                params = ' '.join([f'"{arg}"' for arg in sys.argv])
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, params, None, 1
                )
                sys.exit(0)
            except Exception as e:
                print(f"请求管理员权限失败: {e}")
                # 继续运行，不强制退出
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # 加载阿里巴巴普惠体字体
    font_family = "Microsoft YaHei"  # 默认回退字体
    font_paths = [
        os.path.join(os.path.dirname(sys.executable), "fonts", "NotoSansSC-Bold.ttf"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansSC-Bold.ttf"),
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    font_family = families[0]
                    print(f"字体加载成功: {font_family}")
            break

    # 设置全局字体 - 思源黑体原生粗体
    font = QFont(font_family, 10)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    app.setFont(font)
    
    # 设置全局GM工具风格样式
    global_stylesheet = """
        QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: "FONT_FAMILY_PLACEHOLDER";
            font-size: 14px;
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
            font-size: 14px;
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
            font-size: 14px;
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
            font-size: 14px;
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
            font-size: 13px;
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
            font-size: 13px;
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
            font-size: 15px;
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
            font-size: 15px;
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
            font-size: 14px;
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
            font-size: 12px;
            background-color: transparent;
        }
    """
    global_stylesheet = global_stylesheet.replace("FONT_FAMILY_PLACEHOLDER", font_family)
    app.setStyleSheet(global_stylesheet)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
