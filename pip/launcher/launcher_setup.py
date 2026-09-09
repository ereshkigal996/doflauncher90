# -*- coding: utf-8 -*-
"""
DNF轮回 - 安装程序（从_MEIPASS读取文件版本）
使用 PyInstaller --add-data 将文件直接打包进 exe
安装时从 sys._MEIPASS 读取并复制到目标目录
"""
import os
import sys
import shutil
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QProgressBar, QMessageBox,
                             QLineEdit, QFileDialog, QSizePolicy, QFrame, QStackedWidget)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QFont

def get_resource_dir():
    """获取资源文件所在目录（PyInstaller打包后为_MEIPASS）"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_desktop_path():
    try:
        CSIDL_DESKTOP = 0
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_DESKTOP, 0, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    except:
        return os.path.join(os.path.expanduser("~"), "Desktop")

def create_shortcut(target_path, shortcut_path, working_dir, description):
    """使用PowerShell创建快捷方式，隐藏控制台窗口"""
    try:
        import subprocess
        # 使用PowerShell创建快捷方式，CREATE_NO_WINDOW隐藏控制台
        ps_script = f'''
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{target_path}"
        $Shortcut.WorkingDirectory = "{working_dir}"
        $Shortcut.Description = "{description}"
        $Shortcut.IconLocation = "{target_path},0"
        $Shortcut.Save()
        '''
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(['powershell', '-Command', ps_script], 
                      capture_output=True, timeout=10,
                      creationflags=subprocess.CREATE_NO_WINDOW,
                      startupinfo=startupinfo)
    except Exception as e:
        # 备用方案：使用VBS但隐藏窗口
        try:
            vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\n'
            vbs_content += 'Set Shortcut = WshShell.CreateShortcut("' + shortcut_path + '")\n'
            vbs_content += 'Shortcut.TargetPath = "' + target_path + '"\n'
            vbs_content += 'Shortcut.WorkingDirectory = "' + working_dir + '"\n'
            vbs_content += 'Shortcut.Description = "' + description + '"\n'
            vbs_content += 'Shortcut.IconLocation = "' + target_path + ',0"\n'
            vbs_content += 'Shortcut.Save\n'
            vbs_path = os.path.join(os.environ.get('TEMP', '.'), 'create_shortcut.vbs')
            with open(vbs_path, 'w', encoding='gbk') as f:
                f.write(vbs_content)
            import subprocess
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(['cscript', '//nologo', vbs_path], 
                          capture_output=True, timeout=10,
                          creationflags=subprocess.CREATE_NO_WINDOW,
                          startupinfo=startupinfo)
            if os.path.exists(vbs_path):
                try:
                    os.remove(vbs_path)
                except:
                    pass
        except:
            pass

class InstallThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, install_dir):
        super().__init__()
        self.install_dir = install_dir
    
    def run(self):
        try:
            self.progress.emit(5)
            self.status.emit("正在创建目录...")
            os.makedirs(self.install_dir, exist_ok=True)
            
            # 创建空的backup文件夹
            backup_dir = os.path.join(self.install_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            self.progress.emit(15)
            self.status.emit("正在复制文件...")
            
            resource_dir = get_resource_dir()
            
            # 需要复制的文件和目录列表
            items_to_copy = []
            
            # launcher.exe（打包时文件名为 launcher_2.5.7_release.exe，安装时重命名为 launcher.exe）
            launcher_src = os.path.join(resource_dir, "launcher_2.5.7_release.exe")
            if not os.path.exists(launcher_src):
                # 兼容旧版本，尝试查找 launcher.exe
                launcher_src = os.path.join(resource_dir, "launcher.exe")
            if os.path.exists(launcher_src):
                items_to_copy.append(("launcher.exe", launcher_src))
            
            # README.md
            readme_src = os.path.join(resource_dir, "README.md")
            if os.path.exists(readme_src):
                items_to_copy.append(("README.md", readme_src))
            
            # 常见问题.md
            faq_src = os.path.join(resource_dir, "常见问题.md")
            if os.path.exists(faq_src):
                items_to_copy.append(("常见问题.md", faq_src))
            
            # backup 目录（只复制结构，不复制内容，保持为空）
            backup_src = os.path.join(resource_dir, "backup")
            if os.path.isdir(backup_src):
                # 只创建目录，不复制文件，保持为空
                pass
            
            if not items_to_copy:
                self.finished.emit(False, "未找到 launcher.exe、README.md 或 常见问题.md")
                return
            
            # 复制文件
            total = len(items_to_copy)
            for i, (rel_path, src_path) in enumerate(items_to_copy):
                dst_path = os.path.join(self.install_dir, rel_path)
                parent_dir = os.path.dirname(dst_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                self.progress.emit(15 + int(70 * (i + 1) / total))
                self.status.emit(f"已复制: {rel_path}")
            
            self.progress.emit(85)
            self.status.emit("正在创建桌面快捷方式...")
            
            launcher_path = os.path.join(self.install_dir, "launcher.exe")
            if os.path.exists(launcher_path):
                desktop = get_desktop_path()
                shortcut_path = os.path.join(desktop, "DNF轮回.lnk")
                create_shortcut(launcher_path, shortcut_path, self.install_dir, "DNF轮回 - 简易启动器")
            
            self.progress.emit(95)
            self.status.emit("正在完成安装...")
            
            # 启动器已内置管理员权限，每次运行自动请求UAC提升
            # 无需额外创建批处理文件
            
            self.progress.emit(100)
            self.status.emit("安装完成！桌面已创建快捷方式，2秒后自动关闭...")
            self.finished.emit(True, "安装成功")
            
        except Exception as e:
            self.finished.emit(False, str(e))

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(32)
        self.parent_window = parent
        self.dragging = False
        self.drag_position = QPoint()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 左侧占位，使关闭按钮靠右
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(left_spacer)
        
        # 关闭按钮
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(45, 32)
        self.close_btn.clicked.connect(self.close_window)
        layout.addWidget(self.close_btn)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.parent_window.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def mouseDoubleClickEvent(self, event):
        """双击标题栏最小化窗口"""
        if event.button() == Qt.LeftButton:
            self.parent_window.showMinimized()
            event.accept()
    
    def close_window(self):
        self.parent_window.close()

class PathPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)
        
        title = QLabel("选择安装目录")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 路径输入框
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请输入或选择安装目录")
        self.path_input.setMinimumHeight(36)
        self.path_input.setStyleSheet("font-size: 12px;")
        path_layout.addWidget(self.path_input)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setMinimumHeight(36)
        browse_btn.setMinimumWidth(70)
        browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # 提示文字
        desc = QLabel("默认安装到系统盘的 \\launcher_start 目录")
        desc.setStyleSheet("color: #888888; font-size: 11px;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addStretch()
        
        # 确认按钮
        confirm_btn = QPushButton("确认安装")
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.setMinimumHeight(40)
        confirm_btn.clicked.connect(self.confirm_install)
        layout.addWidget(confirm_btn)
    
    def browse_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择安装目录")
        if dir_path:
            self.path_input.setText(dir_path)
    
    def confirm_install(self):
        install_dir = self.path_input.text().strip()
        if not install_dir:
            install_dir = os.path.join(os.environ.get('SystemDrive', 'C:'), os.sep, "launcher_start")
            self.path_input.setText(install_dir)
        
        install_dir = install_dir.rstrip(os.sep)
        
        if not install_dir:
            QMessageBox.warning(self, "警告", "请输入安装目录！")
            return
        
        self.main_window.start_install(install_dir)

class InstallPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.install_dir = ""
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(18)
        
        self.title = QLabel("正在安装...")
        self.title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFixedHeight(28)
        layout.addWidget(self.title)
        
        # 进度条容器，确保进度条有固定空间
        progress_container = QWidget()
        progress_container.setFixedHeight(35)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
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
                text-align: center;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4a90d9;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_container)
        
        # 状态标签容器，固定高度防止换行挤占
        status_container = QWidget()
        status_container.setFixedHeight(25)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("准备安装...")
        self.status_label.setStyleSheet("color: #88ff88; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(False)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_container)
        
        # 弹性空间
        layout.addStretch()
        
        # 完成按钮（默认隐藏，安装完成后显示）
        self.finish_btn = QPushButton("关闭")
        self.finish_btn.setMinimumHeight(40)
        self.finish_btn.clicked.connect(self.main_window.close)
        self.finish_btn.setVisible(False)
        layout.addWidget(self.finish_btn)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, text):
        self.status_label.setText(text)
    
    def install_finished(self, success, message):
        if success:
            self.status_label.setText("安装完成！桌面已创建快捷方式")
            self.title.setText("安装完成")
            # 保持进度条显示100%，不隐藏，防止布局变化
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(True)
            # 显示关闭按钮
            self.finish_btn.setVisible(True)
        else:
            self.status_label.setText(f"安装失败: {message}")
            self.title.setText("安装失败")
            QTimer.singleShot(5000, self.main_window.close)

class InstallWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.installing = False
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("install")
        self.setFixedSize(420, 310)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        self.path_page = PathPage(self)
        self.stacked_widget.addWidget(self.path_page)
        
        self.install_page = InstallPage(self)
        self.stacked_widget.addWidget(self.install_page)
        
        default_path = os.path.join(os.environ.get('SystemDrive', 'C:'), os.sep, "launcher_start")
        self.path_page.path_input.setText(default_path)
        
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
        
        # 底部信息
        self.scroll_label = QLabel("仅供单机使用  ·  免费发布")
        self.scroll_label.setObjectName("scrollLabel")
        self.scroll_label.setAlignment(Qt.AlignCenter)
        self.scroll_label.setFixedHeight(28)
        main_layout.addWidget(self.scroll_label)
        
        self.setStyleSheet("""
            QMainWindow, QWidget#centralWidget {
                background-color: #0d0d0d;
            }
            QWidget#titleBar {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333333;
            }
            QLabel#titleLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#minBtn {
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 16px;
            }
            QPushButton#minBtn:hover {
                background-color: #333333;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #4a90d9;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #4a90d9;
            }
            QPushButton#primaryBtn {
                background-color: #4a90d9;
                color: #ffffff;
                border: 1px solid #4a90d9;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #5aa0e9;
            }
            QFrame#glowBar {
                background-color: #4a90d9;
            }
            QLabel#scrollLabel {
                color: #666666;
                font-size: 10px;
            }
        """)
    
    def start_install(self, install_dir):
        self.install_page.install_dir = install_dir
        self.stacked_widget.setCurrentWidget(self.install_page)
        self.install_thread = InstallThread(install_dir)
        self.install_thread.progress.connect(self.install_page.update_progress)
        self.install_thread.status.connect(self.install_page.update_status)
        self.install_thread.finished.connect(self.install_page.install_finished)
        self.install_thread.start()

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        font = QFont("Noto Sans SC", 9)
        app.setFont(font)
        window = InstallWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        try:
            QMessageBox.critical(None, "程序错误", f"程序运行出错:\n{e}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
