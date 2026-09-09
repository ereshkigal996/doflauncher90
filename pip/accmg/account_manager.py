#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轮回登录器 - 账号管理工具 (accmg)
无边框窗口，读取launcher配置，支持MySQL/SQLite双数据库模式
风格与主程序一致（蓝色主题）
适用范围：单机版
"""

import sys
import os
import json
import sqlite3
import bcrypt
from datetime import datetime

# ============== 运行库路径设置（支持调用根目录lib） ==============
def setup_lib_path():
    """设置运行库路径，支持调用根目录的lib文件夹"""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 如果当前目录是module目录，检测父目录是否有lib
    if os.path.basename(exe_dir) == "module":
        root_lib = os.path.join(os.path.dirname(exe_dir), "lib")
        if os.path.exists(root_lib):
            # 添加到系统PATH环境变量（用于dll查找）
            os.environ["PATH"] = root_lib + os.pathsep + os.environ.get("PATH", "")
            # 添加到Python sys.path（用于pyd模块查找）
            if root_lib not in sys.path:
                sys.path.insert(0, root_lib)
            return True
    return False

setup_lib_path()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QMessageBox, QDialog, QFormLayout, QHeaderView, QFrame,
    QCheckBox, QMenu, QInputDialog, QListWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEventLoop, QTimer
from PyQt5.QtGui import QFont, QColor, QCursor, QPainter, QPen, QFontDatabase

# ============== 全局配置 ==============
APP_NAME = "账号管理"
APP_VERSION = "3.2.0"
TEST_MODE = False
LAUNCHER_NAME = "launcher.exe"

# ============== 样式定义（与主程序一致 - 蓝色主题） ==============
GLOBAL_QSS = """
QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
    font-family: "Noto Sans SC", "Microsoft YaHei";
    font-size: 13px;
}

QMainWindow {
    background-color: transparent;
}

/* 标题栏（不透明背景，圆角由central容器提供） */
#titleBar {
    background-color: #1a1a1a;
    border-bottom: 1px solid #444444;
}

#titleLabel {
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
}

#dbModeLabel {
    color: #aaaaaa;
    font-size: 14px;
    font-weight: bold;
    background-color: transparent;
}

/* 标题栏按钮 */
QPushButton#titleBtn {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
    min-width: 36px;
    min-height: 28px;
    max-width: 36px;
    max-height: 28px;
}

QPushButton#titleBtn:hover {
    background-color: #3a3a3a;
}

QPushButton#titleBtnClose:hover {
    background-color: #e81123;
}

/* 普通按钮 */
QPushButton {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 5px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
    font-family: "Noto Sans SC", "Microsoft YaHei";
    min-height: 20px;
}

QPushButton:hover {
    background-color: #3a3a3a;
    border-color: #4a90d9;
    color: #4a90d9;
}

QPushButton:pressed {
    background-color: #1a1a1a;
    border-color: #4a90d9;
    color: #4a90d9;
}

/* 输入框样式 - 蓝色聚焦边框 */
QLineEdit {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 13px;
    font-family: "Noto Sans SC", "Microsoft YaHei";
    min-height: 20px;
}

QLineEdit:focus {
    border: 2px solid #4a90d9;
    background-color: #1a1a1a;
}

QLineEdit:disabled {
    background-color: #1a1a1a;
    color: #666666;
    border-color: #333333;
}

/* 表单标签样式 */
QLabel {
    color: #ffffff;
    font-size: 13px;
    font-family: "Noto Sans SC", "Microsoft YaHei";
}

QPushButton:disabled {
    background-color: #1a1a1a;
    border-color: #2a2a2a;
    color: #555555;
}

/* 主按钮（蓝色主题） */
QPushButton#primaryButton {
    background-color: #1a1a2e;
    border-color: #4a90d9;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #0a1a3a;
    border-color: #6ab0ff;
    color: #6ab0ff;
}

QPushButton#primaryButton:pressed {
    background-color: #0a0a1e;
    border-color: #6ab0ff;
    color: #6ab0ff;
}

/* 危险按钮 */
QPushButton#dangerButton {
    background-color: #2a2a2a;
    color: #ff6b6b;
    border: 1px solid #ff6b6b;
}

QPushButton#dangerButton:hover {
    background-color: #3a1a1a;
    background-color: #ff6b6b;
    color: #ffffff;
}

/* 输入框 */
QLineEdit, QComboBox {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: "Noto Sans SC", "Microsoft YaHei";
    selection-background-color: #4a90d9;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #4a90d9;
}

QLineEdit:disabled, QComboBox:disabled {
    background-color: #1a1a1a;
    color: #555555;
}

/* 表格 */
QTableWidget {
    background-color: #000000;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    gridline-color: #2a2a2a;
    selection-background-color: #1a3a5a;
    selection-color: #ffffff;
    outline: none;
    alternate-background-color: #0a0a0a;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #222222;
    background-color: #000000;
}

QTableWidget::item:alternate {
    background-color: #0a0a0a;
}

QTableWidget::item:selected {
    background-color: #1a3a5a;
    color: #ffffff;
}

QTableWidget::item:alternate:selected {
    background-color: #1a3a5a;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #1a2a3a;
}

QTableWidget::item:alternate:hover {
    background-color: #1a2a3a;
}

QHeaderView::section {
    background-color: #222222;
    color: #4a90d9;
    padding: 12px 10px;
    border: none;
    border-right: 1px solid #2a2a2a;
    border-bottom: 2px solid #4a90d9;
    font-weight: bold;
    font-size: 14px;
    font-family: "Noto Sans SC", "Microsoft YaHei";
}

QTableWidget QTableCornerButton::section {
    background-color: #222222;
    border: none;
}

/* 表格中的文字链接 */
QLabel#linkLabel {
    color: #6ab0ff;
    font-size: 13px;
    font-weight: bold;
    text-decoration: underline;
    cursor: pointer;
    padding: 4px 6px;
}

QLabel#linkLabel:hover {
    color: #88ccff;
    background-color: #1a2a4a;
    border-radius: 5px;
}

QLabel#linkLabelDanger {
    color: #ff8888;
    font-size: 13px;
    font-weight: bold;
    text-decoration: underline;
    cursor: pointer;
    padding: 4px 6px;
}

QLabel#linkLabelDanger:hover {
    color: #ffaaaa;
    background-color: #3a1a1a;
    border-radius: 5px;
}

QLabel#linkLabelWarn {
    color: #ffcc44;
    font-size: 13px;
    font-weight: bold;
    text-decoration: underline;
    cursor: pointer;
    padding: 4px 6px;
}

QLabel#linkLabelWarn:hover {
    color: #ffdd66;
    background-color: #3a3a1a;
    border-radius: 5px;
}

QLabel#linkLabelSuccess {
    color: #88ff88;
    font-size: 13px;
    font-weight: bold;
    text-decoration: underline;
    cursor: pointer;
    padding: 4px 6px;
}

QLabel#linkLabelSuccess:hover {
    color: #aaffaa;
    background-color: #1a3a1a;
    border-radius: 5px;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3a3a3a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4a90d9;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1a1a1a;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #3a3a3a;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4a90d9;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* 标签 */
QLabel {
    color: #ffffff;
    font-family: "Noto Sans SC", "Microsoft YaHei";
}

QLabel#infoLabel {
    color: #888888;
    font-size: 12px;
}

QLabel#statusLabel {
    color: #88ff88;
    font-size: 12px;
}

QLabel#statusLabelError {
    color: #ff6b6b;
    font-size: 12px;
}

QLabel#statusLabelWarn {
    color: #ffaa00;
    font-size: 12px;
}

/* 下拉框 */
QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #4a90d9;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    selection-background-color: #1a2a4a;
    selection-color: #ffffff;
}

/* 分隔线 */
QFrame[frameShape="4"] {
    color: #3a3a3a;
}

/* 底部光效栏（圆角由central容器提供） */
#glowBar {
    background-color: #111111;
}

/* 消息框 */
QMessageBox {
    background-color: #1a1a1a;
}

QMessageBox QLabel {
    color: #ffffff;
    font-size: 13px;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""


# ============== 可点击标签（文字链接） ==============
class ClickableLabel(QLabel):
    """可点击的标签，用于表格中的文字链接"""
    clicked = pyqtSignal()
    
    def __init__(self, text, link_type="normal", parent=None):
        super().__init__(text, parent)
        self.link_type = link_type
        self.setObjectName(f"linkLabel{link_type.capitalize() if link_type != 'normal' else ''}")
        self.setCursor(Qt.PointingHandCursor)
        self._data = None
    
    def set_data(self, data):
        """设置关联数据"""
        self._data = data
    
    def get_data(self):
        """获取关联数据"""
        return self._data
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ============== 通用独立窗口基类（圆角紧凑样式） ==============
class FramelessWindow(QDialog):
    """通用无边框独立窗口基类 - 圆角窗口，紧凑布局，确认在右"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.dragging = False
        self.drag_position = QPoint()
        self.init_window()
    
    def init_window(self):
        """初始化窗口 - 圆角紧凑样式"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(320)
        
        # 主容器 - 圆角背景
        main_container = QWidget(self)
        main_container.setObjectName("roundContainer")
        main_container.setStyleSheet("""
            #roundContainer {
                background-color: #1a1a1a;
                border: none;
                border-radius: 8px;
            }
        """)
        
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)
        
        # 内容区域
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)
        main_layout.addWidget(self.content_widget, 1)
        
        # 设置主容器为布局 - 边距2px给边框留出空间
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(2, 2, 2, 2)
        outer_layout.addWidget(main_container)
    
    def add_content(self, widget):
        """添加内容到内容区域"""
        self.content_layout.addWidget(widget)
    
    def add_button_layout(self, ok_btn, cancel_btn=None):
        """添加按钮布局 - 确认在右，取消在左，各占一半宽度"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        if cancel_btn:
            cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            cancel_btn.setMinimumHeight(34)
            btn_layout.addWidget(cancel_btn)
        
        ok_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ok_btn.setMinimumHeight(34)
        btn_layout.addWidget(ok_btn)
        
        self.content_layout.addLayout(btn_layout)
    
    def on_ok(self):
        """确认按钮点击"""
        self.accept()
    
    def on_cancel(self):
        """取消按钮点击"""
        self.reject()
    
    def paintEvent(self, event):
        """绘制圆角背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1a1a1a"))
        painter.setPen(QPen(QColor("#3a3a3a"), 2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
    
    # 窗口拖动（点击非控件区域拖动）
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child and (child.inherits("QLineEdit") or child.inherits("QPushButton") or 
                         child.inherits("QComboBox") or child.inherits("QTextEdit")):
                super().mousePressEvent(event)
                return
            
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False

# ============== 配置管理 ==============
class LauncherConfig:
    """启动器配置管理 - 支持launcher新配置结构（config/config.lau，launcher/gmtool独立字段）"""
    
    def __init__(self):
        self.launcher_dir = self._find_launcher_dir()
        self.config_file = self._find_config_file()
        self.config = self._load_config()
    
    def _find_launcher_dir(self):
        """查找启动器目录"""
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 检查当前目录是否有config文件夹或config.lau
        if os.path.exists(os.path.join(exe_dir, "config", "config.lau")):
            return exe_dir
        if os.path.exists(os.path.join(exe_dir, "config.lau")):
            return exe_dir
        
        # 向上查找3级目录
        parent = os.path.dirname(exe_dir)
        for _ in range(3):
            if os.path.exists(os.path.join(parent, "config", "config.lau")):
                return parent
            if os.path.exists(os.path.join(parent, "config.lau")):
                return parent
            parent = os.path.dirname(parent)
        
        return exe_dir
    
    def _find_config_file(self):
        """查找配置文件 - 优先使用config文件夹下的config.lau"""
        # 优先使用config文件夹下的config.lau
        config_in_folder = os.path.join(self.launcher_dir, "config", "config.lau")
        if os.path.exists(config_in_folder):
            return config_in_folder
        
        # 兼容旧格式：启动器目录下的config.lau
        config_in_root = os.path.join(self.launcher_dir, "config.lau")
        if os.path.exists(config_in_root):
            return config_in_root
        
        # 兼容旧格式：launcher.lau
        old_config = os.path.join(self.launcher_dir, "launcher.lau")
        if os.path.exists(old_config):
            return old_config
        
        # 默认返回config文件夹下的config.lau（即使不存在，保存时会创建）
        return config_in_folder
    
    def _load_config(self):
        """加载配置 - 支持新格式（launcher/gmtool独立字段）和旧格式"""
        default_config = {
            "server_path": "",
            "client_path": "",
            "db_mode": "mysql"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 检查是否是新格式（包含launcher或gmtool字段）
                if "launcher" in config or "gmtool" in config:
                    # 新格式：从launcher字段中读取配置
                    launcher_config = config.get("launcher", {})
                    
                    # 映射字段：launcher字段中的go_server_path/python_server_path映射到server_path
                    server_type = launcher_config.get("server_type", "go")
                    if server_type == "go":
                        default_config["server_path"] = launcher_config.get("go_server_path", "")
                    else:
                        default_config["server_path"] = launcher_config.get("python_server_path", "")
                    
                    default_config["client_path"] = launcher_config.get("client_path", "")
                    
                    # 从gmtool字段读取db_mode，如果没有则从launcher字段读取
                    gmtool_config = config.get("gmtool", {})
                    default_config["db_mode"] = gmtool_config.get("db_mode", launcher_config.get("db_mode", "mysql"))
                else:
                    # 旧格式：直接用配置文件的内容更新默认配置
                    default_config.update(config)
            except Exception as e:
                print(f"加载配置失败: {e}")
        
        return default_config
    
    def get_server_path(self):
        return self.config.get("server_path", "")
    
    def get_client_path(self):
        return self.config.get("client_path", "")
    
    def get_db_mode(self):
        return self.config.get("db_mode", "mysql")
    
    def get_instance_config(self):
        server_path = self.get_server_path()
        if not server_path:
            return {}
        
        instance_file = os.path.join(server_path, "runtime", "config", "instance.json")
        if os.path.exists(instance_file):
            try:
                with open(instance_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载instance.json失败: {e}")
        
        return {}


# ============== accmg增强配置管理（分组和备注） ==============
class AccmgConfig:
    """accmg增强配置管理 - 分组和备注（独立配置文件，不修改原数据库）"""
    
    def __init__(self, launcher_dir):
        self.launcher_dir = launcher_dir
        self.config_file = os.path.join(launcher_dir, "accmg_enhanced.json")
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置"""
        default_config = {
            "groups": ["默认分组"],
            "account_group": {},  # account_id -> group_name
            "account_remark": {}  # account_id -> remark_text
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                    return config
            except Exception as e:
                print(f"加载accmg增强配置失败: {e}")
        
        return default_config
    
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存accmg增强配置失败: {e}")
            return False
    
    # 分组管理
    def get_groups(self):
        """获取所有分组"""
        return self.config.get("groups", ["默认分组"])
    
    def add_group(self, group_name):
        """添加分组"""
        if group_name not in self.config["groups"]:
            self.config["groups"].append(group_name)
            self.save_config()
            return True
        return False
    
    def delete_group(self, group_name):
        """删除分组（该分组下的账号移到默认分组）"""
        if group_name == "默认分组":
            return False  # 不允许删除默认分组
        if group_name in self.config["groups"]:
            self.config["groups"].remove(group_name)
            # 将该分组下的账号移到默认分组
            for account_id, g in self.config["account_group"].items():
                if g == group_name:
                    self.config["account_group"][account_id] = "默认分组"
            self.save_config()
            return True
        return False
    
    def rename_group(self, old_name, new_name):
        """重命名分组"""
        if old_name == "默认分组":
            return False
        if old_name in self.config["groups"] and new_name not in self.config["groups"]:
            idx = self.config["groups"].index(old_name)
            self.config["groups"][idx] = new_name
            # 更新账号的分组
            for account_id, g in self.config["account_group"].items():
                if g == old_name:
                    self.config["account_group"][account_id] = new_name
            self.save_config()
            return True
        return False
    
    def get_account_group(self, account_id):
        """获取账号的分组"""
        return self.config["account_group"].get(account_id, "默认分组")
    
    def set_account_group(self, account_id, group_name):
        """设置账号的分组"""
        self.config["account_group"][account_id] = group_name
        self.save_config()
    
    # 备注管理
    def get_account_remark(self, account_id):
        """获取账号的备注"""
        return self.config["account_remark"].get(account_id, "")
    
    def set_account_remark(self, account_id, remark):
        """设置账号的备注"""
        if remark:
            self.config["account_remark"][account_id] = remark
        else:
            # 空备注则删除
            if account_id in self.config["account_remark"]:
                del self.config["account_remark"][account_id]
        self.save_config()


# ============== 数据库管理类 ==============
class AccountDB:
    """账号数据库管理（支持MySQL和SQLite）"""
    
    def __init__(self, config):
        self.config = config
        self.db_mode = config.get_db_mode()
        self.conn = None
        self.mysql_conn = None
    
    def connect(self):
        if self.db_mode == "mysql":
            return self._connect_mysql()
        else:
            return self._connect_sqlite()
    
    def _connect_sqlite(self):
        server_path = self.config.get_server_path()
        if not server_path:
            raise FileNotFoundError("未配置服务端路径")
        
        db_path = os.path.join(server_path, "runtime", "data", "dnf90.db")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        return True
    
    def _connect_mysql(self):
        import pymysql
        
        # 默认数据库密码（通用密码）
        DEFAULT_DB_PASSWORD = "db_ed372bfa36051308258d2a75f431e91b"
        
        instance_config = self.config.get_instance_config()
        db_config = instance_config.get("database", {})
        
        host = db_config.get("host", "127.0.0.1")
        port = int(db_config.get("port", 13306))
        user = db_config.get("user", "root")
        password = db_config.get("password", "")
        database = db_config.get("name", "dnf_local")
        
        # 如果密码为空，先用默认密码尝试
        if not password:
            password = DEFAULT_DB_PASSWORD
        
        try:
            self.mysql_conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except pymysql.err.OperationalError as e:
            error_msg = str(e)
            # 如果是密码错误且用的是默认密码，抛出特定异常让上层弹框
            if "Access denied" in error_msg and password == DEFAULT_DB_PASSWORD:
                raise ValueError("DEFAULT_PASSWORD_FAILED")
            raise
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        if self.mysql_conn:
            self.mysql_conn.close()
            self.mysql_conn = None
    
    def get_all_accounts(self):
        if self.db_mode == "mysql":
            return self._mysql_get_all()
        else:
            return self._sqlite_get_all()
    
    def _sqlite_get_all(self):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM dnf_login_accounts ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def _mysql_get_all(self):
        if not self.mysql_conn:
            return []
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM dnf_login_accounts ORDER BY created_at DESC")
            return cursor.fetchall()
    
    def search_accounts(self, keyword):
        if self.db_mode == "mysql":
            return self._mysql_search(keyword)
        else:
            return self._sqlite_search(keyword)
    
    def _sqlite_search(self, keyword):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM dnf_login_accounts WHERE username LIKE ? OR account_id LIKE ? ORDER BY created_at DESC",
            (f"%{keyword}%", f"%{keyword}%")
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def _mysql_search(self, keyword):
        if not self.mysql_conn:
            return []
        with self.mysql_conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM dnf_login_accounts WHERE username LIKE %s OR account_id LIKE %s ORDER BY created_at DESC",
                (f"%{keyword}%", f"%{keyword}%")
            )
            return cursor.fetchall()
    
    def add_account(self, username, password):
        if self.db_mode == "mysql":
            return self._mysql_add(username, password)
        else:
            return self._sqlite_add(username, password)
    
    def _sqlite_add(self, username, password):
        if not self.conn:
            return False, "数据库未连接"
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM dnf_login_accounts WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "用户名已存在"
        
        cursor.execute("SELECT COUNT(*) as cnt FROM dnf_login_accounts")
        count = cursor.fetchone()['cnt']
        account_id = f"dnf:{count + 1}"
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC")
        
        cursor.execute(
            """INSERT INTO dnf_login_accounts 
               (account_id, username, password_hash, state, created_at, updated_at, last_login_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, username, password_hash, 'active', now, now, now)
        )
        self.conn.commit()
        return True, f"账号添加成功，账号ID: {account_id}"
    
    def _mysql_add(self, username, password):
        if not self.mysql_conn:
            return False, "数据库未连接"
        
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM dnf_login_accounts WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "用户名已存在"
            
            cursor.execute("SELECT COUNT(*) as cnt FROM dnf_login_accounts")
            count = cursor.fetchone()['cnt']
            account_id = f"dnf:{count + 1}"
            
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            cursor.execute(
                """INSERT INTO dnf_login_accounts 
                   (account_id, username, password_hash, state, created_at, updated_at, last_login_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (account_id, username, password_hash, 'active', now, now, now)
            )
            self.mysql_conn.commit()
            return True, f"账号添加成功，账号ID: {account_id}"
    
    def update_password(self, account_id, new_password):
        if self.db_mode == "mysql":
            return self._mysql_update_password(account_id, new_password)
        else:
            return self._sqlite_update_password(account_id, new_password)
    
    def _sqlite_update_password(self, account_id, new_password):
        if not self.conn:
            return False, "数据库未连接"
        
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC")
        
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE dnf_login_accounts SET password_hash = ?, updated_at = ? WHERE account_id = ?",
            (password_hash, now, account_id)
        )
        self.conn.commit()
        return True, "密码修改成功"
    
    def _mysql_update_password(self, account_id, new_password):
        if not self.mysql_conn:
            return False, "数据库未连接"
        
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        with self.mysql_conn.cursor() as cursor:
            cursor.execute(
                "UPDATE dnf_login_accounts SET password_hash = %s, updated_at = %s WHERE account_id = %s",
                (password_hash, now, account_id)
            )
            self.mysql_conn.commit()
            return True, "密码修改成功"
    
    def update_state(self, account_id, state):
        if self.db_mode == "mysql":
            return self._mysql_update_state(account_id, state)
        else:
            return self._sqlite_update_state(account_id, state)
    
    def _sqlite_update_state(self, account_id, state):
        if not self.conn:
            return False, "数据库未连接"
        
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC")
        
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE dnf_login_accounts SET state = ?, updated_at = ? WHERE account_id = ?",
            (state, now, account_id)
        )
        self.conn.commit()
        return True, f"账号状态已修改为: {state}"
    
    def _mysql_update_state(self, account_id, state):
        if not self.mysql_conn:
            return False, "数据库未连接"
        
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        with self.mysql_conn.cursor() as cursor:
            cursor.execute(
                "UPDATE dnf_login_accounts SET state = %s, updated_at = %s WHERE account_id = %s",
                (state, now, account_id)
            )
            self.mysql_conn.commit()
            return True, f"账号状态已修改为: {state}"
    
    def delete_account(self, account_id):
        if self.db_mode == "mysql":
            return self._mysql_delete(account_id)
        else:
            return self._sqlite_delete(account_id)
    
    def _sqlite_delete(self, account_id):
        if not self.conn:
            return False, "数据库未连接"
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM dnf_login_accounts WHERE account_id = ?", (account_id,))
        self.conn.commit()
        return True, "账号已删除"
    
    def _mysql_delete(self, account_id):
        if not self.mysql_conn:
            return False, "数据库未连接"
        
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("DELETE FROM dnf_login_accounts WHERE account_id = %s", (account_id,))
            self.mysql_conn.commit()
            return True, "账号已删除"
    
    # 批量操作
    def batch_delete(self, account_ids):
        """批量删除账号"""
        if self.db_mode == "mysql":
            return self._mysql_batch_delete(account_ids)
        else:
            return self._sqlite_batch_delete(account_ids)
    
    def _sqlite_batch_delete(self, account_ids):
        if not self.conn:
            return False, "数据库未连接"
        
        cursor = self.conn.cursor()
        placeholders = ','.join(['?' for _ in account_ids])
        cursor.execute(f"DELETE FROM dnf_login_accounts WHERE account_id IN ({placeholders})", account_ids)
        self.conn.commit()
        return True, f"已删除 {len(account_ids)} 个账号"
    
    def _mysql_batch_delete(self, account_ids):
        if not self.mysql_conn:
            return False, "数据库未连接"
        
        with self.mysql_conn.cursor() as cursor:
            placeholders = ','.join(['%s' for _ in account_ids])
            cursor.execute(f"DELETE FROM dnf_login_accounts WHERE account_id IN ({placeholders})", account_ids)
            self.mysql_conn.commit()
            return True, f"已删除 {len(account_ids)} 个账号"
    
    def batch_update_state(self, account_ids, state):
        """批量修改账号状态"""
        if self.db_mode == "mysql":
            return self._mysql_batch_update_state(account_ids, state)
        else:
            return self._sqlite_batch_update_state(account_ids, state)
    
    def _sqlite_batch_update_state(self, account_ids, state):
        if not self.conn:
            return False, "数据库未连接"
        
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC")
        cursor = self.conn.cursor()
        placeholders = ','.join(['?' for _ in account_ids])
        cursor.execute(
            f"UPDATE dnf_login_accounts SET state = ?, updated_at = ? WHERE account_id IN ({placeholders})",
            [state, now] + account_ids
        )
        self.conn.commit()
        return True, f"已将 {len(account_ids)} 个账号状态修改为: {state}"
    
    def _mysql_batch_update_state(self, account_ids, state):
        if not self.mysql_conn:
            return False, "数据库未连接"
        
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        with self.mysql_conn.cursor() as cursor:
            placeholders = ','.join(['%s' for _ in account_ids])
            cursor.execute(
                f"UPDATE dnf_login_accounts SET state = %s, updated_at = %s WHERE account_id IN ({placeholders})",
                [state, now] + account_ids
            )
            self.mysql_conn.commit()
            return True, f"已将 {len(account_ids)} 个账号状态修改为: {state}"
    
    # 高级搜索（支持状态筛选）
    def search_accounts_advanced(self, keyword="", state="all"):
        """高级搜索 - 支持关键词和状态筛选"""
        if self.db_mode == "mysql":
            return self._mysql_search_advanced(keyword, state)
        else:
            return self._sqlite_search_advanced(keyword, state)
    
    def _sqlite_search_advanced(self, keyword="", state="all"):
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        query = "SELECT * FROM dnf_login_accounts WHERE 1=1"
        params = []
        
        if keyword:
            query += " AND (username LIKE ? OR account_id LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if state != "all":
            query += " AND state = ?"
            params.append(state)
        
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _mysql_search_advanced(self, keyword="", state="all"):
        if not self.mysql_conn:
            return []
        
        with self.mysql_conn.cursor() as cursor:
            query = "SELECT * FROM dnf_login_accounts WHERE 1=1"
            params = []
            
            if keyword:
                query += " AND (username LIKE %s OR account_id LIKE %s)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            if state != "all":
                query += " AND state = %s"
                params.append(state)
            
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return cursor.fetchall()


# ============== 添加账号对话框（独立窗口 - 简洁样式） ==============
class AddAccountDialog(FramelessWindow):
    def __init__(self, parent=None):
        super().__init__("添加账号", parent)
        self.setMinimumWidth(360)
        self.setMinimumHeight(280)
        self.init_content()
    
    def init_content(self):
        # 输入框（无标签，垂直排列）
        input_layout = QVBoxLayout()
        input_layout.setSpacing(4)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(32)
        input_layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(32)
        input_layout.addWidget(self.password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请确认密码")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(32)
        input_layout.addWidget(self.confirm_password_input)
        
        input_widget = QWidget()
        input_widget.setLayout(input_layout)
        self.add_content(input_widget)
        
        # 按钮 - 取消在左，添加在右，各占一半宽度（紧贴输入框）
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.on_cancel)
        
        self.add_btn = QPushButton("添加")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.on_add)
        
        self.add_button_layout(self.add_btn, self.cancel_btn)
    
    def on_add(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_password_input.text()
        
        if not username:
            self.show_error("请输入用户名")
            return
        if not password:
            self.show_error("请输入密码")
            return
        if len(password) < 6:
            self.show_error("密码长度至少6位")
            return
        if password != confirm:
            self.show_error("两次输入的密码不一致")
            return
        
        self.username = username
        self.password = password
        self.on_ok()
    
    def show_error(self, message):
        """显示错误提示（独立窗口 - 简洁样式）"""
        error_dialog = FramelessWindow("提示", self)
        error_dialog.setMinimumWidth(300)
        error_dialog.setMinimumHeight(150)
        
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        error_label.setStyleSheet("font-size: 14px; color: #ff6b6b;")
        error_dialog.add_content(error_label)
        
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("primaryButton")
        ok_btn.setMinimumHeight(48)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(error_dialog.on_ok)
        error_dialog.add_button_layout(ok_btn)
        
        error_dialog.exec_()


# ============== 修改密码对话框（独立窗口） ==============
class ChangePasswordDialog(FramelessWindow):
    def __init__(self, username, parent=None):
        super().__init__("修改密码", parent)
        self.setMinimumWidth(360)
        self.setMinimumHeight(240)
        self.username = username
        self.init_content()
    
    def init_content(self):
        # 用户名显示（左对齐）
        user_label = QLabel(f"当前账号：{self.username}")
        user_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        user_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        user_label.setMaximumHeight(20)
        self.add_content(user_label)
        
        # 输入框（无标签，垂直排列）
        input_layout = QVBoxLayout()
        input_layout.setSpacing(4)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setMinimumHeight(32)
        input_layout.addWidget(self.new_password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请确认新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(32)
        input_layout.addWidget(self.confirm_password_input)
        
        input_widget = QWidget()
        input_widget.setLayout(input_layout)
        self.add_content(input_widget)
        
        # 按钮 - 取消在左，修改在右（紧贴输入框）
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.on_cancel)
        
        self.change_btn = QPushButton("修改")
        self.change_btn.setObjectName("primaryButton")
        self.change_btn.setCursor(Qt.PointingHandCursor)
        self.change_btn.clicked.connect(self.on_change)
        
        self.add_button_layout(self.change_btn, self.cancel_btn)
    
    def on_change(self):
        new_password = self.new_password_input.text()
        confirm = self.confirm_password_input.text()
        
        if not new_password:
            self.show_error("请输入新密码")
            return
        if len(new_password) < 6:
            self.show_error("密码长度至少6位")
            return
        if new_password != confirm:
            self.show_error("两次输入的密码不一致")
            return
        
        self.new_password = new_password
        self.on_ok()
    
    def show_error(self, message):
        """显示错误提示（独立窗口）"""
        error_dialog = FramelessWindow("提示", self)
        error_dialog.setMinimumWidth(300)
        error_dialog.setMinimumHeight(150)
        
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        error_dialog.add_content(error_label)
        
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("primaryButton")
        ok_btn.setMinimumHeight(36)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(error_dialog.on_ok)
        error_dialog.add_button_layout(ok_btn)
        
        error_dialog.exec_()


# ============== 分组管理对话框（独立窗口） ==============
class GroupManagementDialog(FramelessWindow):
    """分组管理对话框 - 添加、删除、重命名分组（独立窗口风格）"""
    
    def __init__(self, enhanced_config, parent=None):
        super().__init__("分组管理", parent)
        self.enhanced_config = enhanced_config
        self.setMinimumWidth(360)
        self.setMinimumHeight(400)
        self.init_content()
    
    def init_content(self):
        # 分组列表
        self.group_list = QListWidget()
        self.group_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                color: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #4a90d9;
            }
        """)
        self.add_content(self.group_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.add_btn = QPushButton("添加分组")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_group)
        btn_layout.addWidget(self.add_btn)
        
        self.rename_btn = QPushButton("重命名")
        self.rename_btn.setCursor(Qt.PointingHandCursor)
        self.rename_btn.clicked.connect(self.rename_group)
        btn_layout.addWidget(self.rename_btn)
        
        self.delete_btn = QPushButton("删除分组")
        self.delete_btn.setStyleSheet("QPushButton { background-color: #8b0000; border-color: #aa0000; color: white; } QPushButton:hover { background-color: #aa0000; color: white; } QPushButton:pressed { background-color: #6b0000; color: white; } QPushButton:disabled { color: #666666; }")
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self.delete_group)
        btn_layout.addWidget(self.delete_btn)
        
        self.content_layout.addLayout(btn_layout)
        
        # 关闭按钮（添加按键反馈）
        self.close_btn = QPushButton("关闭")
        self.close_btn.setObjectName("primaryButton")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #4a90d9;
                color: #4a90d9;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
                border-color: #4a90d9;
                color: #4a90d9;
            }
        """)
        self.close_btn.clicked.connect(self.accept)
        self.add_button_layout(self.close_btn)
        
        self.refresh_group_list()
    
    def refresh_group_list(self):
        """刷新分组列表"""
        self.group_list.clear()
        groups = self.enhanced_config.get_groups()
        for group in groups:
            self.group_list.addItem(group)
    
    def add_group(self):
        """添加分组"""
        name, ok = QInputDialog.getText(self, "添加分组", "请输入分组名称:", QLineEdit.Normal, "")
        if ok and name.strip():
            name = name.strip()
            if self.enhanced_config.add_group(name):
                QMessageBox.information(self, "成功", f"分组「{name}」已添加")
                self.refresh_group_list()
            else:
                QMessageBox.warning(self, "警告", f"分组「{name}」已存在")
    
    def rename_group(self):
        """重命名分组"""
        current_item = self.group_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要重命名的分组")
            return
        
        old_name = current_item.text()
        if old_name == "默认分组":
            QMessageBox.warning(self, "警告", "默认分组不允许重命名")
            return
        
        new_name, ok = QInputDialog.getText(self, "重命名分组", f"将「{old_name}」重命名为:", QLineEdit.Normal, old_name)
        if ok and new_name.strip():
            new_name = new_name.strip()
            if self.enhanced_config.rename_group(old_name, new_name):
                QMessageBox.information(self, "成功", f"分组已重命名为「{new_name}」")
                self.refresh_group_list()
            else:
                QMessageBox.warning(self, "警告", "重命名失败（名称已存在或不允许修改默认分组）")
    
    def delete_group(self):
        """删除分组"""
        current_item = self.group_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要删除的分组")
            return
        
        group_name = current_item.text()
        if group_name == "默认分组":
            QMessageBox.warning(self, "警告", "默认分组不允许删除")
            return
        
        confirm = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除分组「{group_name}」吗？\n该分组下的账号将移动到默认分组。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            if self.enhanced_config.delete_group(group_name):
                QMessageBox.information(self, "成功", f"分组「{group_name}」已删除")
                self.refresh_group_list()
            else:
                QMessageBox.warning(self, "警告", "删除失败")


# ============== 主窗口（无边框 + 真正圆角） ==============
class AccountManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = LauncherConfig()
        self.enhanced_config = AccmgConfig(self.config.launcher_dir)
        self.db = None
        self.current_accounts = []
        self.selected_account_ids = set()  # 批量操作选中的账号ID
        self.dragging = False
        self.drag_position = QPoint()
        
        self.init_ui()
        # 延迟连接数据库，等窗口完全显示后再弹密码输入框
        QTimer.singleShot(100, self.connect_db)
    
    def init_ui(self):
        # 无边框 + 透明背景（与主程序完全一致）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setWindowTitle("accmg")
        self.setMinimumSize(1200, 650)
        self.resize(1200, 650)
        self.setStyleSheet(GLOBAL_QSS)
        
        # 中央部件 - 透明背景（圆角由paintEvent绘制）
        central = QWidget()
        central.setObjectName("mainRoundedContainer")
        central.setStyleSheet("""
            #mainRoundedContainer {
                background-color: transparent;
                border: none;
            }
        """)
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 自定义标题栏（和登录器一致 - 高度56px）
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet("background-color: transparent; border: none;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(24, 0, 16, 0)
        title_layout.setSpacing(8)
        
        # 标题文字（左上角）
        title_label = QLabel("账号管理工具")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; background-color: transparent;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        db_mode = self.config.get_db_mode().upper()
        self.db_mode_label = QLabel(f"数据库: {db_mode}")
        self.db_mode_label.setObjectName("dbModeLabel")
        self.db_mode_label.setStyleSheet("color: #888888; font-size: 13px; background-color: transparent;")
        title_layout.addWidget(self.db_mode_label)
        
        title_layout.addSpacing(8)
        
        # 关闭按钮（和登录器一致 - 大小32x28，字号13px，加粗）
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("titleBtn")
        self.close_btn.setProperty("class", "close")
        self.close_btn.setToolTip("关闭")
        self.close_btn.setFixedSize(32, 28)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888888; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 0px; }
            QPushButton:hover { background-color: #e81123; color: #ffffff; }
        """)
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.close_btn)
        
        # 双击标题栏最小化
        title_bar.mouseDoubleClickEvent = self.on_title_bar_double_click
        
        # 内容区域（透明背景）
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(16, 16, 16, 16)
        
        # 工具栏 - 第一行（搜索、筛选、操作）
        tool_bar = QWidget()
        tool_layout = QHBoxLayout(tool_bar)
        tool_layout.setSpacing(8)
        tool_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索用户名、账号ID或备注...")
        self.search_input.textChanged.connect(self.on_search)
        tool_layout.addWidget(self.search_input, 2)
        
        # 状态筛选
        self.state_filter = QLineEdit()
        self.state_filter.setPlaceholderText("状态筛选")
        self.state_filter.setReadOnly(True)
        self.state_filter.setFixedWidth(100)
        self.state_filter.mousePressEvent = lambda e: self.show_state_filter_menu()
        tool_layout.addWidget(self.state_filter)
        self.current_state_filter = "all"
        
        # 分组筛选
        self.group_filter = QLineEdit()
        self.group_filter.setPlaceholderText("分组筛选")
        self.group_filter.setReadOnly(True)
        self.group_filter.setFixedWidth(100)
        self.group_filter.mousePressEvent = lambda e: self.show_group_filter_menu()
        tool_layout.addWidget(self.group_filter)
        self.current_group_filter = "all"
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_accounts)
        tool_layout.addWidget(self.refresh_btn)
        
        self.group_mgmt_btn = QPushButton("分组管理")
        self.group_mgmt_btn.clicked.connect(self.show_group_management)
        tool_layout.addWidget(self.group_mgmt_btn)
        
        self.add_btn = QPushButton("添加账号")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.on_add_account)
        tool_layout.addWidget(self.add_btn)
        
        content_layout.addWidget(tool_bar)
        
        # 工具栏 - 第二行（批量操作）
        batch_bar = QWidget()
        batch_layout = QHBoxLayout(batch_bar)
        batch_layout.setSpacing(8)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setFixedWidth(70)
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.select_all_accounts)
        batch_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("取消")
        self.deselect_all_btn.setFixedWidth(70)
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(self.deselect_all_accounts)
        self.deselect_all_btn.setVisible(False)  # 未选择账号时不可见
        batch_layout.addWidget(self.deselect_all_btn)
        
        self.selected_count_label = QLabel("已选择: 0 个账号")
        self.selected_count_label.setObjectName("infoLabel")
        batch_layout.addWidget(self.selected_count_label)
        
        batch_layout.addStretch()
        
        self.batch_state_btn = QPushButton("批量修改状态")
        self.batch_state_btn.setFixedWidth(120)
        self.batch_state_btn.clicked.connect(self.batch_update_state)
        batch_layout.addWidget(self.batch_state_btn)
        
        self.batch_group_btn = QPushButton("批量移动分组")
        self.batch_group_btn.setFixedWidth(120)
        self.batch_group_btn.clicked.connect(self.batch_move_group)
        batch_layout.addWidget(self.batch_group_btn)
        
        self.batch_delete_btn = QPushButton("批量删除")
        self.batch_delete_btn.setFixedWidth(100)
        self.batch_delete_btn.setStyleSheet("QPushButton { background-color: #8b0000; border-color: #aa0000; color: white; } QPushButton:hover { background-color: #aa0000; color: white; } QPushButton:pressed { background-color: #6b0000; color: white; } QPushButton:disabled { color: #666666; }")
        self.batch_delete_btn.clicked.connect(self.batch_delete_accounts)
        batch_layout.addWidget(self.batch_delete_btn)
        
        content_layout.addWidget(batch_bar)
        
        # 表格（添加复选框列、分组列、备注列）
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "", "账号ID", "用户名", "分组", "状态", "备注",
            "创建时间", "最后登录", "操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Fixed)
        self.table.setColumnWidth(8, 320)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        content_layout.addWidget(self.table, 1)
        
        # 底部状态栏
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.count_label = QLabel("共 0 个账号")
        self.count_label.setObjectName("infoLabel")
        status_layout.addWidget(self.count_label)
        
        content_layout.addWidget(status_bar)
        
        # 按正确顺序添加到主布局
        main_layout.addWidget(title_bar)
        
        # 标题栏下横分割线（和登录器一致 - 颜色#2a2a2a）
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setAttribute(Qt.WA_StyledBackground, True)
        separator.setStyleSheet("background-color: #2a2a2a; border: none;")
        main_layout.addWidget(separator)
        
        main_layout.addWidget(content_widget, 1)
        
        # 底部光效栏（与主程序完全一致）
        glow_container = QWidget()
        glow_container.setStyleSheet("background-color: transparent;")
        glow_layout = QHBoxLayout(glow_container)
        glow_layout.setContentsMargins(20, 0, 20, 0)
        
        glow_bar = QFrame()
        glow_bar.setObjectName("glowBar")
        glow_bar.setFixedHeight(1)
        glow_layout.addWidget(glow_bar)
        
        main_layout.addWidget(glow_container)
    
    # 无边框窗口拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.pos().y() < 40:  # 标题栏区域
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def paintEvent(self, event):
        """绘制圆角背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1a1a1a"))
        painter.setPen(QPen(QColor("#3a3a3a"), 1))
        painter.drawRoundedRect(self.rect(), 8, 8)
    
    def on_title_bar_double_click(self, event):
        """双击标题栏最小化"""
        if event.button() == Qt.LeftButton:
            self.showMinimized()
    
    def connect_db(self):
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        import pymysql
        
        try:
            self.db = AccountDB(self.config)
            self.db.connect()
            db_mode = self.config.get_db_mode().upper()
            self.db_mode_label.setText(f"数据库: {db_mode}")
            self.status_label.setText("数据库连接成功")
            self.status_label.setObjectName("statusLabel")
            self.load_accounts()
        except ValueError as e:
            if str(e) == "DEFAULT_PASSWORD_FAILED":
                # 默认密码连接失败，弹出输入框让用户手动输入
                instance_config = self.config.get_instance_config()
                db_config = instance_config.get("database", {})
                host = db_config.get("host", "127.0.0.1")
                port = db_config.get("port", 13306)
                user = db_config.get("user", "root")
                
                password, ok = QInputDialog.getText(
                    self, 
                    "数据库密码", 
                    f"默认密码连接失败，请手动输入MySQL root用户密码：\n\n主机: {host}:{port}\n用户: {user}\n\n（密码通常在服务端目录 runtime/config/instance.json 中）",
                    mode=QInputDialog.Password
                )
                
                if ok and password:
                    # 用户输入了密码，临时设置到配置中，然后重新连接
                    if "database" not in instance_config:
                        instance_config["database"] = {}
                    instance_config["database"]["password"] = password
                    
                    try:
                        self.db.connect()
                        db_mode = self.config.get_db_mode().upper()
                        self.db_mode_label.setText(f"数据库: {db_mode}")
                        self.status_label.setText("数据库连接成功")
                        self.status_label.setObjectName("statusLabel")
                        self.load_accounts()
                        QMessageBox.information(self, "连接成功", "数据库连接成功！\n\n建议将密码保存到服务端目录的 instance.json 中，避免每次都要手动输入。")
                    except Exception as e2:
                        self._show_db_error(e2)
                else:
                    self.db_mode_label.setText("数据库: 未连接")
                    self.status_label.setText("用户取消了密码输入")
                    self.status_label.setObjectName("statusLabelError")
            else:
                self._show_db_error(e)
        except Exception as e:
            self._show_db_error(e)
    
    def _show_db_error(self, error):
        from PyQt5.QtWidgets import QMessageBox
        import pymysql
        
        error_msg = str(error)
        self.db_mode_label.setText("数据库: 连接失败")
        self.status_label.setText(f"连接失败: {error_msg}")
        self.status_label.setObjectName("statusLabelError")
        
        # 根据错误类型给出更明确的提示
        if "Access denied" in error_msg:
            QMessageBox.critical(
                self, 
                "数据库连接失败", 
                f"数据库密码错误或权限不足！\n\n错误信息: {error_msg}\n\n请检查：\n1. MySQL服务是否已启动\n2. 密码是否正确（在服务端目录 runtime/config/instance.json 中查看）\n3. root用户是否允许从localhost连接"
            )
        elif "Can't connect" in error_msg or "Connection refused" in error_msg:
            QMessageBox.critical(
                self, 
                "数据库连接失败", 
                f"无法连接到MySQL服务器！\n\n错误信息: {error_msg}\n\n请检查：\n1. MySQL服务是否已启动（先启动服务端）\n2. 主机地址和端口是否正确\n3. 防火墙是否阻止了连接"
            )
        elif "Unknown database" in error_msg:
            QMessageBox.critical(
                self, 
                "数据库连接失败", 
                f"数据库不存在！\n\n错误信息: {error_msg}\n\n请检查：\n1. 数据库是否已创建\n2. 数据库名称是否正确"
            )
        else:
            QMessageBox.critical(
                self, 
                "数据库连接失败", 
                f"数据库连接出错：\n\n{error_msg}"
            )
    
    def load_accounts(self):
        if not self.db:
            return
        
        try:
            keyword = self.search_input.text().strip()
            
            # 使用高级搜索（支持状态筛选）
            self.current_accounts = self.db.search_accounts_advanced(
                keyword=keyword,
                state=self.current_state_filter
            )
            
            # 分组筛选和备注搜索（在内存中过滤）
            filtered_accounts = []
            for account in self.current_accounts:
                account_id = str(account.get('account_id', ''))
                
                # 分组筛选
                if self.current_group_filter != "all":
                    account_group = self.enhanced_config.get_account_group(account_id)
                    if account_group != self.current_group_filter:
                        continue
                
                # 备注搜索（如果有关键词，且用户名/账号ID不匹配，则检查备注）
                if keyword:
                    remark = self.enhanced_config.get_account_remark(account_id)
                    username = str(account.get('username', ''))
                    if keyword.lower() not in username.lower() and keyword.lower() not in account_id.lower():
                        if keyword.lower() not in remark.lower():
                            continue
                
                filtered_accounts.append(account)
            
            self.current_accounts = filtered_accounts
            self.update_table()
            self.status_label.setText("加载完成")
            self.status_label.setObjectName("statusLabel")
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            import traceback
            traceback.print_exc()
    
    def update_table(self):
        self.table.setRowCount(len(self.current_accounts))
        
        for row, account in enumerate(self.current_accounts):
            try:
                account_id = str(account.get('account_id', ''))
                
                # 复选框列
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                
                checkbox = QCheckBox()
                checkbox.setChecked(account_id in self.selected_account_ids)
                checkbox.stateChanged.connect(lambda state, aid=account_id: self.on_checkbox_changed(aid, state))
                checkbox_layout.addWidget(checkbox)
                self.table.setCellWidget(row, 0, checkbox_widget)
                
                # 账号ID
                item_id = QTableWidgetItem(account_id)
                item_id.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, item_id)
                
                # 用户名
                item_user = QTableWidgetItem(str(account.get('username', '')))
                item_user.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, item_user)
                
                # 分组
                account_group = self.enhanced_config.get_account_group(account_id)
                item_group = QTableWidgetItem(account_group)
                item_group.setTextAlignment(Qt.AlignCenter)
                item_group.setForeground(QColor('#4a90d9'))
                self.table.setItem(row, 3, item_group)
                
                # 状态
                state = str(account.get('state', 'active'))
                state_cn = {
                    'active': '正常',
                    'disabled': '禁用',
                    'banned': '封禁',
                    'inactive': '未激活'
                }.get(state, state)
                item_state = QTableWidgetItem(state_cn)
                item_state.setTextAlignment(Qt.AlignCenter)
                if state == 'active':
                    item_state.setForeground(QColor('#88ff88'))
                else:
                    item_state.setForeground(QColor('#ff6b6b'))
                self.table.setItem(row, 4, item_state)
                
                # 备注（可双击编辑）
                remark = self.enhanced_config.get_account_remark(account_id)
                item_remark = QTableWidgetItem(remark)
                item_remark.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if remark:
                    item_remark.setForeground(QColor('#ffd700'))
                else:
                    item_remark.setForeground(QColor('#666666'))
                    item_remark.setText("双击添加备注")
                self.table.setItem(row, 5, item_remark)
                
                # 创建时间
                created = str(account.get('created_at', ''))
                if created:
                    created = created.split('.')[0].replace(' +0000 UTC', '')
                item_created = QTableWidgetItem(created)
                item_created.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 6, item_created)
                
                # 最后登录
                last_login = str(account.get('last_login_at', ''))
                if last_login:
                    last_login = last_login.split('.')[0].replace(' +0000 UTC', '')
                item_last = QTableWidgetItem(last_login)
                item_last.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 7, item_last)
                
                # 操作列（文字链接形式）
                op_widget = QWidget()
                op_widget.setStyleSheet("background-color: transparent;")
                op_layout = QHBoxLayout(op_widget)
                op_layout.setContentsMargins(4, 2, 4, 2)
                op_layout.setSpacing(10)
                op_layout.setAlignment(Qt.AlignCenter)
                
                # 修改密码链接
                pwd_link = ClickableLabel("修改密码", "normal")
                pwd_link.set_data(account)
                pwd_link.clicked.connect(lambda acc=account: self.on_change_password(acc))
                op_layout.addWidget(pwd_link)
                
                # 移动分组链接
                group_link = ClickableLabel("移动分组", "normal")
                group_link.set_data(account)
                group_link.clicked.connect(lambda acc=account: self.on_move_group(acc))
                op_layout.addWidget(group_link)
                
                # 启用/禁用链接
                state = str(account.get('state', 'active'))
                if state == 'active':
                    toggle_link = ClickableLabel("禁用", "warn")
                else:
                    toggle_link = ClickableLabel("启用", "success")
                toggle_link.set_data(account)
                toggle_link.clicked.connect(lambda acc=account: self.on_toggle_state(acc))
                op_layout.addWidget(toggle_link)
                
                # 删除链接
                del_link = ClickableLabel("删除", "danger")
                del_link.set_data(account)
                del_link.clicked.connect(lambda acc=account: self.on_delete_account(acc))
                op_layout.addWidget(del_link)
                
                self.table.setCellWidget(row, 8, op_widget)
            except Exception as e:
                # 如果某条数据处理失败，在该行显示错误信息
                error_item = QTableWidgetItem(f"加载失败: {str(e)}")
                error_item.setForeground(QColor('#ff6b6b'))
                self.table.setItem(row, 1, error_item)
                print(f"处理账号数据失败 (行 {row}): {e}")
                import traceback
                traceback.print_exc()
        
        self.count_label.setText(f"共 {len(self.current_accounts)} 个账号")
        self.update_selected_count()
    
    def on_search(self):
        self.load_accounts()
    
    def on_add_account(self):
        try:
            dialog = AddAccountDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                try:
                    success, msg = self.db.add_account(dialog.username, dialog.password)
                    if success:
                        QMessageBox.information(self, "成功", msg)
                        self.load_accounts()
                    else:
                        QMessageBox.warning(self, "失败", msg)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")
        except Exception as e:
            import traceback
            error_msg = f"打开添加账号对话框失败:\n{str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)
            # 同时写入错误日志
            try:
                with open("accmg_error.log", "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(error_msg)
                    f.write(f"\n{'='*50}\n")
            except:
                pass
    
    def on_change_password(self, account):
        try:
            dialog = ChangePasswordDialog(str(account.get('username', '')), self)
            if dialog.exec_() == QDialog.Accepted:
                try:
                    success, msg = self.db.update_password(
                        account['account_id'], dialog.new_password
                    )
                    if success:
                        QMessageBox.information(self, "成功", msg)
                        self.load_accounts()
                    else:
                        QMessageBox.warning(self, "失败", msg)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"修改密码失败: {str(e)}")
        except Exception as e:
            import traceback
            error_msg = f"打开修改密码对话框失败:\n{str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)
            try:
                with open("accmg_error.log", "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(error_msg)
                    f.write(f"\n{'='*50}\n")
            except:
                pass
    
    def on_toggle_state(self, account):
        current_state = str(account.get('state', 'active'))
        new_state = 'disabled' if current_state == 'active' else 'active'
        
        reply = QMessageBox.question(
            self, "确认", 
            f"确定要{ '禁用' if new_state == 'disabled' else '启用' }账号 "
            f"'{account.get('username', '')}' 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success, msg = self.db.update_state(account['account_id'], new_state)
                if success:
                    self.status_label.setText(msg)
                    self.load_accounts()
                else:
                    QMessageBox.warning(self, "失败", msg)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")
    
    def on_delete_account(self, account):
        reply = QMessageBox.warning(
            self, "确认删除",
            f"确定要删除账号 '{account.get('username', '')}' 吗？\n\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success, msg = self.db.delete_account(account['account_id'])
                if success:
                    self.status_label.setText(msg)
                    self.load_accounts()
                else:
                    QMessageBox.warning(self, "失败", msg)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def closeEvent(self, event):
        if self.db:
            self.db.disconnect()
        event.accept()
    
    # ============== 批量操作相关方法 ==============
    def on_checkbox_changed(self, account_id, state):
        """复选框状态变化处理"""
        if state == Qt.Checked:
            self.selected_account_ids.add(account_id)
        else:
            self.selected_account_ids.discard(account_id)
        self.update_selected_count()
    
    def select_all_accounts(self):
        """全选当前显示的账号"""
        for account in self.current_accounts:
            account_id = str(account.get('account_id', ''))
            self.selected_account_ids.add(account_id)
        self.update_table()
    
    def deselect_all_accounts(self):
        """取消全选"""
        self.selected_account_ids.clear()
        self.update_table()
    
    def update_selected_count(self):
        """更新选中数量显示"""
        count = len(self.selected_account_ids)
        self.selected_count_label.setText(f"已选择: {count} 个账号")
        # 启用/禁用批量操作按钮
        enabled = count > 0
        self.batch_state_btn.setEnabled(enabled)
        self.batch_group_btn.setEnabled(enabled)
        self.batch_delete_btn.setEnabled(enabled)
        # 显示/隐藏取消按钮（未选择账号时不可见）
        self.deselect_all_btn.setVisible(enabled)
    
    def batch_update_state(self):
        """批量修改状态"""
        if not self.selected_account_ids:
            QMessageBox.warning(self, "警告", "请先选择要操作的账号")
            return
        
        # 显示状态选择对话框
        states = [
            ("正常", "active"),
            ("禁用", "disabled"),
            ("封禁", "banned"),
            ("未激活", "inactive")
        ]
        
        state_names = [s[0] for s in states]
        choice, ok = QInputDialog.getItem(self, "批量修改状态", "选择目标状态:", state_names, 0, False)
        
        if ok and choice:
            state_value = dict(states)[choice]
            account_ids = list(self.selected_account_ids)
            
            confirm = QMessageBox.question(
                self, "确认", 
                f"确定要将 {len(account_ids)} 个账号状态修改为「{choice}」吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                success, msg = self.db.batch_update_state(account_ids, state_value)
                if success:
                    QMessageBox.information(self, "成功", msg)
                    self.selected_account_ids.clear()
                    self.load_accounts()
                else:
                    QMessageBox.critical(self, "错误", msg)
    
    def batch_delete_accounts(self):
        """批量删除账号"""
        if not self.selected_account_ids:
            QMessageBox.warning(self, "警告", "请先选择要删除的账号")
            return
        
        account_ids = list(self.selected_account_ids)
        confirm = QMessageBox.warning(
            self, "确认删除", 
            f"确定要删除选中的 {len(account_ids)} 个账号吗？\n此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            success, msg = self.db.batch_delete(account_ids)
            if success:
                # 同时删除增强配置中的分组和备注
                for aid in account_ids:
                    if aid in self.enhanced_config.config["account_group"]:
                        del self.enhanced_config.config["account_group"][aid]
                    if aid in self.enhanced_config.config["account_remark"]:
                        del self.enhanced_config.config["account_remark"][aid]
                self.enhanced_config.save_config()
                
                QMessageBox.information(self, "成功", msg)
                self.selected_account_ids.clear()
                self.load_accounts()
            else:
                QMessageBox.critical(self, "错误", msg)
    
    # ============== 筛选相关方法 ==============
    def show_state_filter_menu(self):
        """显示状态筛选菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2a2a2a; color: white; border: 1px solid #4a4a4a; } QMenu::item:selected { background-color: #4a90d9; }")
        
        actions = [
            ("全部状态", "all"),
            ("正常", "active"),
            ("禁用", "disabled"),
            ("封禁", "banned"),
            ("未激活", "inactive")
        ]
        
        for name, value in actions:
            action = menu.addAction(name)
            if value == self.current_state_filter:
                action.setCheckable(True)
                action.setChecked(True)
            action.triggered.connect(lambda checked, v=value, n=name: self.set_state_filter(v, n))
        
        menu.exec_(self.state_filter.mapToGlobal(QPoint(0, self.state_filter.height())))
    
    def set_state_filter(self, value, name):
        """设置状态筛选"""
        self.current_state_filter = value
        self.state_filter.setText(name if value != "all" else "状态筛选")
        self.load_accounts()
    
    def show_group_filter_menu(self):
        """显示分组筛选菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2a2a2a; color: white; border: 1px solid #4a4a4a; } QMenu::item:selected { background-color: #4a90d9; }")
        
        # 全部分组
        action = menu.addAction("全部分组")
        if self.current_group_filter == "all":
            action.setCheckable(True)
            action.setChecked(True)
        action.triggered.connect(lambda: self.set_group_filter("all", "分组筛选"))
        
        menu.addSeparator()
        
        # 各个分组
        groups = self.enhanced_config.get_groups()
        for group in groups:
            action = menu.addAction(group)
            if group == self.current_group_filter:
                action.setCheckable(True)
                action.setChecked(True)
            action.triggered.connect(lambda checked, g=group: self.set_group_filter(g, g))
        
        menu.exec_(self.group_filter.mapToGlobal(QPoint(0, self.group_filter.height())))
    
    def set_group_filter(self, value, name):
        """设置分组筛选"""
        self.current_group_filter = value
        self.group_filter.setText(name if value != "all" else "分组筛选")
        self.load_accounts()
    
    # ============== 分组管理相关方法 ==============
    def show_group_management(self):
        """显示分组管理对话框"""
        dialog = GroupManagementDialog(self.enhanced_config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_accounts()
    
    def on_move_group(self, account):
        """移动单个账号到指定分组"""
        account_id = str(account.get('account_id', ''))
        groups = self.enhanced_config.get_groups()
        
        choice, ok = QInputDialog.getItem(self, "移动分组", f"将账号 {account.get('username', '')} 移动到:", groups, 0, False)
        
        if ok and choice:
            self.enhanced_config.set_account_group(account_id, choice)
            QMessageBox.information(self, "成功", f"账号已移动到分组「{choice}」")
            self.load_accounts()
    
    def batch_move_group(self):
        """批量移动分组"""
        if not self.selected_account_ids:
            QMessageBox.warning(self, "警告", "请先选择要操作的账号")
            return
        
        groups = self.enhanced_config.get_groups()
        choice, ok = QInputDialog.getItem(self, "批量移动分组", f"将选中的 {len(self.selected_account_ids)} 个账号移动到:", groups, 0, False)
        
        if ok and choice:
            # 防呆操作：确认移动
            confirm = QMessageBox.question(
                self, "确认移动",
                f"确定要将选中的 {len(self.selected_account_ids)} 个账号移动到分组「{choice}」吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                for account_id in self.selected_account_ids:
                    self.enhanced_config.set_account_group(account_id, choice)
                QMessageBox.information(self, "成功", f"已将 {len(self.selected_account_ids)} 个账号移动到分组「{choice}」")
                self.selected_account_ids.clear()
                self.load_accounts()
    
    # ============== 备注编辑相关方法 ==============
    def on_table_double_clicked(self, index):
        """双击表格单元格 - 编辑备注"""
        if index.column() == 5:  # 备注列
            row = index.row()
            if row < len(self.current_accounts):
                account = self.current_accounts[row]
                account_id = str(account.get('account_id', ''))
                current_remark = self.enhanced_config.get_account_remark(account_id)
                
                remark, ok = QInputDialog.getText(
                    self, "编辑备注", 
                    f"账号: {account.get('username', '')}\n备注:",
                    QLineEdit.Normal,
                    current_remark
                )
                
                if ok:
                    self.enhanced_config.set_account_remark(account_id, remark.strip())
                    self.load_accounts()


# ============== 主程序调用检测 ==============
def is_called_from_launcher():
    # 先检查命令行参数（不需要导入任何库）
    if '--from-launcher' in sys.argv:
        return True
    
    # 再检查父进程
    try:
        import psutil
        parent = psutil.Process(os.getppid())
        if parent.name().lower() == LAUNCHER_NAME.lower():
            return True
    except:
        pass
    
    return False


# ============== 主函数 ==============
def main():
    # 检查是否从主程序调用（用于记录日志，不限制启动）
    from_launcher = is_called_from_launcher()
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # 优先从fonts目录加载思源黑体，失败则使用系统字体 - 和登录器一致
    font_family = "Microsoft YaHei"  # 默认回退字体
    font_loaded = False
    
    # 尝试从fonts目录加载（accmg在module目录下，需要向上找一级）
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        font_paths = [
            os.path.join(os.path.dirname(exe_dir), "fonts", "NotoSansSC-Bold.ttf"),
            os.path.join(exe_dir, "fonts", "NotoSansSC-Bold.ttf"),
        ]
    else:
        font_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "launcher", "fonts", "NotoSansSC-Bold.ttf"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansSC-Bold.ttf"),
        ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    font_family = families[0]
                    font_loaded = True
                    print(f"字体加载成功(本地): {font_family}")
            break
    
    # 如果本地加载失败，尝试使用系统已安装的思源黑体
    if not font_loaded:
        available_fonts = QFontDatabase().families()
        if "Noto Sans SC" in available_fonts:
            font_family = "Noto Sans SC"
            print(f"使用系统字体: {font_family}")
        elif "Microsoft YaHei" in available_fonts:
            font_family = "Microsoft YaHei"
            print(f"思源黑体不可用，使用回退字体: {font_family}")
        elif "SimHei" in available_fonts:
            font_family = "SimHei"
            print(f"思源黑体不可用，使用回退字体: {font_family}")
    
    # 设置全局字体 - 和登录器一致
    font = QFont(font_family, 10)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    app.setFont(font)
    
    window = AccountManager()
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
