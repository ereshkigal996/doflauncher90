#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNF轮回启动器 - 自动升级程序
从Gitee检查并下载最新版本
"""

import sys
import os
import json
import re
import subprocess
import tempfile
import threading
from urllib.request import urlopen, Request
from urllib.parse import urlencode

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QMessageBox,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QFontDatabase, QIcon

# 版本信息
APP_VERSION = "3.0.3"
APP_NAME = "DNF轮回启动器升级程序"

# Gitee仓库信息
GITEE_OWNER = "ereshkigal996"
GITEE_REPO = "doflauncher90"
GITEE_BRANCH = "master"
GITEE_TOKEN = "7d694e1f6948f22c4330c7561017e479"

# 安装包文件名模式
INSTALLER_PATTERN = r"DNFLauncher_([\d.]+)_release_installer\.exe"

# 配色（Win11黑暗模式）
COLOR_BG = "#202020"
COLOR_CARD = "#252525"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_SECONDARY = "#a0a0a0"
COLOR_PRIMARY = "#0078d4"
COLOR_BORDER = "#2a2a2a"
COLOR_HOVER = "#2a2a2a"
COLOR_SUCCESS = "#107c10"
COLOR_WARNING = "#ff8c00"
COLOR_ERROR = "#e81123"


def get_app_dir():
    """获取程序所在目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_current_version():
    """获取当前launcher版本号"""
    app_dir = get_app_dir()
    launcher_exe = os.path.join(app_dir, "launcher.exe")
    
    # 方式0：优先从根目录的版本信息文件读取
    version = get_version_from_info_file(app_dir)
    if version:
        return version
    
    # 尝试从配置文件读取
    config_file = os.path.join(app_dir, "config", "config.lau")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'launcher' in config and 'version' in config['launcher']:
                print(f"从配置文件读取版本: {config['launcher']['version']}")
                return config['launcher']['version']
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 尝试从exe文件属性读取（优先使用PowerShell，备用ctypes）
    if os.path.exists(launcher_exe):
        # 方式1：使用PowerShell（更可靠）
        try:
            version = get_exe_version_powershell(launcher_exe)
            if version:
                print(f"从exe属性(PowerShell)读取版本: {version}")
                return version
        except Exception as e:
            print(f"PowerShell读取exe版本失败: {e}")
        
        # 方式2：使用ctypes（备用）
        try:
            version = get_exe_version_ctypes(launcher_exe)
            if version:
                print(f"从exe属性(ctypes)读取版本: {version}")
                return version
        except Exception as e:
            print(f"ctypes读取exe版本失败: {e}")
    
    # 默认版本
    print("使用默认版本: 3.0.1")
    return "3.0.1"



def get_version_from_info_file(app_dir):
    """从根目录的版本信息文件读取版本号"""
    # 可能的版本信息文件名
    possible_names = [
        "version_info.txt",
        "version_info_3.0.txt",
        "version.txt",
        "VERSION",
    ]
    
    for filename in possible_names:
        file_path = os.path.join(app_dir, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析PyInstaller version_info格式
                # 查找 filevers=(3, 0, 0, 0) 或 FileVersion
                import re
                
                # 方式1：查找 filevers=(x, x, x, x)
                match = re.search(r'filevers=\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', content)
                if match:
                    major, minor, patch, build = match.groups()
                    version = f"{major}.{minor}.{patch}"
                    print(f"从版本信息文件({filename})读取版本: {version}")
                    return version
                
                # 方式2：查找 StringStruct(u'FileVersion', u'x.x.x.x')
                match = re.search(r"StringStruct\(u'FileVersion',\s*u'([\d.]+)'\)", content)
                if match:
                    version_str = match.group(1)
                    parts = version_str.split('.')
                    if len(parts) >= 3:
                        version = '.'.join(parts[:3])
                    else:
                        version = version_str
                    print(f"从版本信息文件({filename})读取版本: {version}")
                    return version
                
                # 方式3：简单的文本文件，第一行就是版本号
                first_line = content.strip().split('\n')[0].strip()
                if re.match(r'^\d+\.\d+\.\d+', first_line):
                    print(f"从版本信息文件({filename})读取版本: {first_line}")
                    return first_line
                    
            except Exception as e:
                print(f"读取版本信息文件({filename})失败: {e}")
    
    return None

def get_exe_version_powershell(exe_path):
    """使用PowerShell获取exe版本号（更可靠）"""
    try:
        import subprocess
        # 使用PowerShell获取文件版本
        ps_command = f"(Get-Item '{exe_path}').VersionInfo.FileVersion"
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_command],
            capture_output=True, text=True, timeout=15,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            if version and version != '':
                # 只保留前3段版本号（如3.0.1.0 -> 3.0.1）
                parts = version.split('.')
                if len(parts) >= 3:
                    return '.'.join(parts[:3])
                return version
    except Exception as e:
        print(f"PowerShell读取版本失败: {e}")
    return None


def get_exe_version_ctypes(exe_path):
    """使用ctypes调用Windows API获取exe版本号（备用方式）"""
    try:
        import ctypes
        from ctypes import wintypes
        
        GetFileVersionInfoSizeW = ctypes.windll.version.GetFileVersionInfoSizeW
        GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        GetFileVersionInfoSizeW.restype = wintypes.DWORD
        
        handle = wintypes.DWORD(0)
        size = GetFileVersionInfoSizeW(exe_path, ctypes.byref(handle))
        if size == 0:
            return None
        
        GetFileVersionInfoW = ctypes.windll.version.GetFileVersionInfoW
        GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        GetFileVersionInfoW.restype = wintypes.BOOL
        
        buffer = ctypes.create_string_buffer(size)
        result = GetFileVersionInfoW(exe_path, 0, size, buffer)
        if not result:
            return None
        
        VerQueryValueW = ctypes.windll.version.VerQueryValueW
        VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
        VerQueryValueW.restype = wintypes.BOOL
        
        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD),
                ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD),
                ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD),
                ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]
        
        value = ctypes.c_void_p()
        length = wintypes.UINT(0)
        result = VerQueryValueW(ctypes.cast(buffer, ctypes.c_void_p), "\\", ctypes.byref(value), ctypes.byref(length))
        if not result or length.value == 0:
            return None
        
        fixed_info = ctypes.cast(value, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        
        ms = fixed_info.dwFileVersionMS
        ls = fixed_info.dwFileVersionLS
        major = (ms >> 16) & 0xFFFF
        minor = ms & 0xFFFF
        patch = (ls >> 16) & 0xFFFF
        build = ls & 0xFFFF
        
        if build > 0:
            return f"{major}.{minor}.{patch}"
        else:
            return f"{major}.{minor}.{patch}"
            
    except Exception as e:
        print(f"ctypes读取版本失败: {e}")
        return None


def compare_versions(v1, v2):
    """比较版本号，返回1如果v1>v2，-1如果v1<v2，0如果相等"""
    def parse_version(v):
        parts = re.findall(r'\d+', v)
        return [int(p) for p in parts]
    
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    
    # 补齐长度
    max_len = max(len(p1), len(p2))
    p1.extend([0] * (max_len - len(p1)))
    p2.extend([0] * (max_len - len(p2)))
    
    for a, b in zip(p1, p2):
        if a > b:
            return 1
        elif a < b:
            return -1
    return 0


class GiteeAPI:
    """Gitee API 封装"""
    
    BASE_URL = "https://gitee.com/api/v5"
    
    @staticmethod
    def get_repo_contents(path=""):
        """获取仓库文件列表"""
        url = f"{GiteeAPI.BASE_URL}/repos/{GITEE_OWNER}/{GITEE_REPO}/contents/{path}?ref={GITEE_BRANCH}&access_token={GITEE_TOKEN}"
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"获取仓库内容失败: {e}")
            print(f"URL: {url}")
            return None
    
    @staticmethod
    def get_latest_release():
        """获取最新发布"""
        url = f"{GiteeAPI.BASE_URL}/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/latest?access_token={GITEE_TOKEN}"
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"获取最新发布失败: {e}")
            print(f"URL: {url}")
            return None
    
    @staticmethod
    def get_latest_version():
        """从发布中获取最新版本号，返回多个可能的下载链接"""
        release = GiteeAPI.get_latest_release()
        if not release:
            return None, None
        
        tag_name = release.get('tag_name', '')
        # 从标签名提取版本号，如 v3.0.1 -> 3.0.1
        version_match = re.search(r'([\d.]+)', tag_name)
        if version_match:
            latest_version = version_match.group(1)
        else:
            latest_version = tag_name
        
        # 收集所有可能的下载链接
        download_urls = []
        installer_name = f'DNFLauncher_{latest_version}_release_installer.exe'
        
        # 1. 优先从release附件查找
        assets = release.get('assets', [])
        for asset in assets:
            name = asset.get('name', '')
            match = re.match(INSTALLER_PATTERN, name)
            if match:
                url = asset.get('browser_download_url', '')
                if url and url not in download_urls:
                    download_urls.append(url)
                    print(f"找到release附件下载链接: {url}")
        
        # 2. 仓库根目录
        root_url = f'https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/raw/{GITEE_BRANCH}/{installer_name}'
        if root_url not in download_urls:
            download_urls.append(root_url)
            print(f"添加仓库根目录下载链接: {root_url}")
        
        # 3. 仓库releases目录
        releases_url = f'https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/raw/{GITEE_BRANCH}/releases/{installer_name}'
        if releases_url not in download_urls:
            download_urls.append(releases_url)
            print(f"添加仓库releases目录下载链接: {releases_url}")
        
        # 4. 尝试检测仓库中是否有安装包（通过API）
        try:
            contents = GiteeAPI.get_repo_contents("")
            if contents and isinstance(contents, list):
                for item in contents:
                    name = item.get('name', '')
                    if re.match(INSTALLER_PATTERN, name):
                        download_url = item.get('download_url', '')
                        if download_url and download_url not in download_urls:
                            download_urls.append(download_url)
                            print(f"从仓库根目录API找到安装包: {download_url}")
        except Exception as e:
            print(f"检测仓库根目录安装包失败: {e}")
        
        # 5. 尝试检测releases目录
        try:
            contents = GiteeAPI.get_repo_contents("releases")
            if contents and isinstance(contents, list):
                for item in contents:
                    name = item.get('name', '')
                    if re.match(INSTALLER_PATTERN, name):
                        download_url = item.get('download_url', '')
                        if download_url and download_url not in download_urls:
                            download_urls.append(download_url)
                            print(f"从releases目录API找到安装包: {download_url}")
        except Exception as e:
            print(f"检测releases目录安装包失败: {e}")
        
        # 构造latest_file对象，包含所有下载链接
        latest_file = {
            'name': installer_name,
            'size': 0,
            'browser_download_url': download_urls[0] if download_urls else '',
            'all_download_urls': download_urls
        }
        
        print(f"共找到 {len(download_urls)} 个可能的下载链接")
        return latest_version, latest_file
    
    @staticmethod
    def get_file_download_url(file_info):
        """获取文件下载链接"""
        if isinstance(file_info, dict):
            url = file_info.get('browser_download_url', '')
            # 如果是gitee的下载链接，确保包含access_token
            if url and 'gitee.com' in url and 'access_token' not in url:
                if '?' in url:
                    url += f'&access_token={GITEE_TOKEN}'
                else:
                    url += f'?access_token={GITEE_TOKEN}'
            return url
        return f"https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/raw/{GITEE_BRANCH}/{file_info}?access_token={GITEE_TOKEN}"


class DownloadThread(QThread):
    """下载线程，支持多个下载链接自动切换"""
    progress = pyqtSignal(int, int)  # 当前下载大小, 总大小
    finished = pyqtSignal(bool, str)  # 是否成功, 文件路径或错误信息
    
    def __init__(self, urls, save_path):
        super().__init__()
        # 支持单个url或url列表
        if isinstance(urls, str):
            self.urls = [urls]
        else:
            self.urls = urls
        self.save_path = save_path
        self.current_url_index = 0
    
    def run(self):
        errors = []
        for url_index, url in enumerate(self.urls):
            self.current_url_index = url_index
            print(f"\n=== 尝试下载链接 {url_index + 1}/{len(self.urls)} ===")
            print(f"URL: {url}")
            
            try:
                success = self._download_single_url(url)
                if success:
                    print(f"下载成功！使用链接 {url_index + 1}")
                    self.finished.emit(True, self.save_path)
                    return
                else:
                    errors.append(f"链接{url_index + 1}: 下载失败")
            except Exception as e:
                error_msg = f"链接{url_index + 1}: {str(e)}"
                print(f"下载失败: {error_msg}")
                errors.append(error_msg)
                continue
        
        # 所有链接都失败
        error_summary = "所有下载方式均失败:\n" + "\n".join(errors)
        print(error_summary)
        self.finished.emit(False, error_summary)
    
    def _download_single_url(self, url):
        """使用单个URL下载，返回是否成功"""
        # 构建下载URL和请求头
        download_url = url
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
        }
        
        # 如果是gitee的下载链接，添加access_token
        if 'gitee.com' in download_url and 'access_token' not in download_url:
            if '?' in download_url:
                download_url += f'&access_token={GITEE_TOKEN}'
            else:
                download_url += f'?access_token={GITEE_TOKEN}'
        
        # 方式1：使用urllib
        try:
            print("  尝试urllib下载...")
            req = Request(download_url, headers=headers)
            with urlopen(req, timeout=300) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(self.save_path, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        downloaded += len(buffer)
                        self.progress.emit(downloaded, total_size)
                
                # 验证文件是否下载成功（大小>0）
                if os.path.exists(self.save_path) and os.path.getsize(self.save_path) > 0:
                    print("  urllib下载成功！")
                    return True
                else:
                    print("  urllib下载文件为空")
        except Exception as e:
            print(f"  urllib下载失败: {e}")
        
        # 方式2：使用requests（如果可用）
        try:
            import requests
            print("  尝试requests下载...")
            response = requests.get(download_url, headers=headers, stream=True, timeout=300, allow_redirects=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            block_size = 8192
            
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
            
            if os.path.exists(self.save_path) and os.path.getsize(self.save_path) > 0:
                print("  requests下载成功！")
                return True
            else:
                print("  requests下载文件为空")
        except ImportError:
            print("  requests库不可用")
        except Exception as e:
            print(f"  requests下载失败: {e}")
        
        # 方式3：使用PowerShell的Invoke-WebRequest
        try:
            import subprocess
            print("  尝试PowerShell下载...")
            ps_command = f"""
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri '{download_url}' -OutFile '{self.save_path}' -UseBasicParsing -Headers @{{'User-Agent'='Mozilla/5.0'}}
            """
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_command],
                capture_output=True, text=True, timeout=300,
                creationflags=0x08000000
            )
            if result.returncode == 0 and os.path.exists(self.save_path):
                file_size = os.path.getsize(self.save_path)
                if file_size > 0:
                    self.progress.emit(file_size, file_size)
                    print("  PowerShell下载成功！")
                    return True
                else:
                    print("  PowerShell下载文件为空")
            else:
                print(f"  PowerShell下载失败: {result.stderr}")
        except Exception as e:
            print(f"  PowerShell下载失败: {e}")
        
        return False


class CheckUpdateThread(QThread):
    """检查更新线程"""
    finished = pyqtSignal(bool, str, str, object)  # 是否有更新, 最新版本, 错误信息, 文件信息
    
    def run(self):
        try:
            latest_version, latest_file = GiteeAPI.get_latest_version()
            if not latest_version:
                self.finished.emit(False, "", "未找到版本信息", None)
                return
            
            current_version = get_current_version()
            has_update = compare_versions(latest_version, current_version) > 0
            
            self.finished.emit(has_update, latest_version, "", latest_file)
        except Exception as e:
            self.finished.emit(False, "", str(e), None)


class UpdaterWindow(QMainWindow):
    """升级程序主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_version = get_current_version()
        self.latest_version = None
        self.latest_file = None
        self.download_thread = None
        self.temp_installer = None
        
        self.init_ui()
        self.load_font()
        
        # 显示调试信息
        app_dir = get_app_dir()
        launcher_exe = os.path.join(app_dir, "launcher.exe")
        launcher_exists = os.path.exists(launcher_exe)
        
        # 检查版本信息文件
        version_file_found = "无"
        for vf in ["version_info.txt", "version_info_3.0.txt", "version.txt", "VERSION"]:
            if os.path.exists(os.path.join(app_dir, vf)):
                version_file_found = vf
                break
        
        debug_text = f"目录: {app_dir}\nlauncher: {'存在' if launcher_exists else '不存在'} | 版本文件: {version_file_found}\n当前版本: {self.current_version}"
        if hasattr(self, 'debug_label'):
            self.debug_label.setText(debug_text)
        
        self.check_update()
    
    def load_font(self):
        """加载字体"""
        app_dir = get_app_dir()
        font_paths = [
            os.path.join(app_dir, "fonts", "NotoSansSC-Bold.ttf"),
            os.path.join(os.path.dirname(app_dir), "fonts", "NotoSansSC-Bold.ttf"),
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id >= 0:
                    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                    self.app_font = QFont(font_family, 10)
                    self.app_font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
                    QApplication.setFont(self.app_font)
                    break
    
    def init_ui(self):
        """初始化UI - 与launcher统一风格，紧凑布局"""
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(380, 300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 窗口容器（与launcher的main_container一致：#1d1d1d背景，圆角8px，描边1px #333）
        window_container = QFrame()
        window_container.setObjectName("mainContainer")
        window_container.setStyleSheet("""
            QFrame#mainContainer {
                background-color: #1d1d1d;
                border-radius: 8px;
                border: 1px solid #333333;
            }
        """)
        window_layout = QVBoxLayout(window_container)
        window_layout.setContentsMargins(16, 12, 16, 14)
        window_layout.setSpacing(10)
        
        # 标题栏（与launcher一致）
        title_container = QWidget()
        title_container.setStyleSheet("background-color: transparent; border: none;")
        title_row = QHBoxLayout(title_container)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        
        title_label = QLabel("程序更新")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            background-color: transparent;
            border: none;
        """)
        title_row.addWidget(title_label)
        title_row.addStretch()
        
        # 关闭按钮（与launcher一致）
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(28, 24)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton#closeBtn {
                background-color: transparent; color: #999999; border: none;
                font-size: 13px; font-weight: bold; border-radius: 4px;
            }
            QPushButton#closeBtn:hover {
                background-color: #c42b1c; color: #ffffff;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        title_row.addWidget(self.close_btn)
        
        window_layout.addWidget(title_container)
        
        # 内容区域（透明背景，无边框）
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #1d1d1d; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        
        # 版本信息（透明背景，无卡片）
        current_version_layout = QHBoxLayout()
        current_label = QLabel("当前版本：")
        current_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent; border: none;")
        self.current_version_label = QLabel(self.current_version)
        self.current_version_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background-color: transparent; border: none;")
        current_version_layout.addWidget(current_label)
        current_version_layout.addWidget(self.current_version_label)
        current_version_layout.addStretch()
        self.content_layout.addLayout(current_version_layout)
        
        latest_version_layout = QHBoxLayout()
        latest_label = QLabel("最新版本：")
        latest_label.setStyleSheet("color: #b0b0b0; font-size: 13px; background-color: transparent; border: none;")
        self.latest_version_label = QLabel("检查中...")
        self.latest_version_label.setStyleSheet("color: #ff8c00; font-size: 13px; font-weight: bold; background-color: transparent; border: none;")
        latest_version_layout.addWidget(latest_label)
        latest_version_layout.addWidget(self.latest_version_label)
        latest_version_layout.addStretch()
        self.content_layout.addLayout(latest_version_layout)
        
        self.content_layout.addSpacing(4)
        
        # 状态信息
        self.status_label = QLabel("正在检查更新...")
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 13px; background-color: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.status_label)
        
        # 调试信息（显示当前目录和launcher路径）
        self.debug_label = QLabel("")
        self.debug_label.setStyleSheet("color: #666666; font-size: 11px; background-color: transparent; border: none;")
        self.debug_label.setAlignment(Qt.AlignCenter)
        self.debug_label.setWordWrap(True)
        self.content_layout.addWidget(self.debug_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2a2a2a;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        self.content_layout.addWidget(self.progress_bar)
        
        # 进度信息
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888888; font-size: 11px; background-color: transparent; border: none;")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setVisible(False)
        self.content_layout.addWidget(self.progress_label)
        
        self.content_layout.addStretch()
        
        window_layout.addWidget(self.content_widget)
        
        # 按钮区域（透明背景，无边框，紧凑按钮）
        self.button_widget = QWidget()
        self.button_widget.setStyleSheet("background-color: #1d1d1d; border: none;")
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(8)
        self.button_layout.addStretch()
        
        self.check_btn = QPushButton("重新检查")
        self.check_btn.setFixedHeight(32)
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4; color: #ffffff; border: none;
                border-radius: 4px; font-size: 13px; font-weight: bold; padding: 4px 14px;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        self.check_btn.clicked.connect(self.check_update)
        self.check_btn.setVisible(False)
        self.button_layout.addWidget(self.check_btn)
        
        self.update_btn = QPushButton("立即更新")
        self.update_btn.setFixedHeight(32)
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10; color: #ffffff; border: none;
                border-radius: 4px; font-size: 13px; font-weight: bold; padding: 4px 14px;
            }
            QPushButton:hover { background-color: #0c5a0c; }
            QPushButton:pressed { background-color: #0a4a0a; }
        """)
        self.update_btn.clicked.connect(self.start_update)
        self.update_btn.setVisible(False)
        self.button_layout.addWidget(self.update_btn)
        
        self.cancel_btn = QPushButton("关闭")
        self.cancel_btn.setFixedHeight(32)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a; color: #e0e0e0;
                border: 1px solid #555555; border-radius: 4px; font-size: 13px; padding: 4px 14px;
            }
            QPushButton:hover { background-color: #4a4a4a; border-color: #666666; }
        """)
        self.cancel_btn.clicked.connect(self.close)
        self.button_layout.addWidget(self.cancel_btn)
        
        window_layout.addWidget(self.button_widget)
        
        main_layout.addWidget(window_container)
        
        # 窗口拖动
        self.dragging = False
        self.drag_position = None
        
        # 拖动支持
        window_container.mousePressEvent = self.mousePressEvent
        window_container.mouseMoveEvent = self.mouseMoveEvent
        window_container.mouseReleaseEvent = self.mouseReleaseEvent
    
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
    
    def log(self, message):
        """添加日志 - 显示在状态标签中"""
        self.status_label.setText(message)
    
    def check_update(self):
        """检查更新"""
        self.status_label.setText("正在检查更新...")
        self.latest_version_label.setText("检查中...")
        self.latest_version_label.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 13px; font-weight: bold;")
        self.check_btn.setVisible(False)
        self.update_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        self.log("开始检查更新...")
        self.log(f"当前版本: {self.current_version}")
        
        self.check_thread = CheckUpdateThread()
        self.check_thread.finished.connect(self.on_check_finished)
        self.check_thread.start()
    
    def on_check_finished(self, has_update, latest_version, error, latest_file):
        """检查更新完成"""
        print(f"检查更新完成: has_update={has_update}, latest={latest_version}, error={error}")
        print(f"当前版本: {self.current_version}, 最新版本: {latest_version}")
        
        if error:
            self.status_label.setText(f"检查失败: {error}")
            self.status_label.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 13px;")
            self.latest_version_label.setText("未知")
            self.latest_version_label.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 13px; font-weight: bold;")
            self.check_btn.setVisible(True)
            self.log(f"检查更新失败: {error}")
            return
        
        self.latest_version = latest_version
        self.latest_file = latest_file
        self.latest_version_label.setText(latest_version)
        
        if has_update:
            self.status_label.setText(f"发现新版本 {latest_version}，是否更新？")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 13px;")
            self.latest_version_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 13px; font-weight: bold;")
            self.update_btn.setVisible(True)
            self.log(f"发现新版本: {latest_version}")
            if latest_file:
                self.log(f"安装包: {latest_file.get('name', '未知')}")
                self.log(f"大小: {latest_file.get('size', 0) / 1024 / 1024:.2f} MB")
        else:
            self.status_label.setText("当前已是最新版本")
            self.status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")
            self.latest_version_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px; font-weight: bold;")
            self.check_btn.setVisible(True)
            self.log("当前已是最新版本")
    
    def start_update(self):
        """开始更新"""
        if not self.latest_file:
            QMessageBox.warning(self, "错误", "未找到安装包信息")
            return
        
        file_name = self.latest_file.get('name', 'installer.exe')
        
        # 获取所有下载链接
        all_urls = self.latest_file.get('all_download_urls', [])
        if not all_urls:
            # 如果没有all_download_urls，使用单个url
            single_url = GiteeAPI.get_file_download_url(self.latest_file)
            all_urls = [single_url]
        
        # 临时文件路径
        temp_dir = tempfile.gettempdir()
        self.temp_installer = os.path.join(temp_dir, file_name)
        
        self.log(f"开始下载: {file_name}")
        self.log(f"共找到 {len(all_urls)} 个下载链接")
        for i, url in enumerate(all_urls):
            self.log(f"  链接{i+1}: {url}")
        self.log(f"保存到: {self.temp_installer}")
        
        self.status_label.setText("正在下载更新包...")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.update_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # 传入所有下载链接，支持自动切换
        self.download_thread = DownloadThread(all_urls, self.temp_installer)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()
    
    def on_download_progress(self, downloaded, total):
        """下载进度"""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"{downloaded / 1024 / 1024:.2f} MB / {total / 1024 / 1024:.2f} MB ({percent}%)")
        else:
            self.progress_label.setText(f"{downloaded / 1024 / 1024:.2f} MB")
    
    def on_download_finished(self, success, message):
        """下载完成"""
        self.update_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        if not success:
            self.status_label.setText(f"下载失败: {message}")
            self.status_label.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 13px;")
            self.log(f"下载失败: {message}")
            QMessageBox.critical(self, "下载失败", f"下载更新包失败:\n{message}")
            return
        
        self.status_label.setText("下载完成，准备安装...")
        self.log("下载完成！")
        self.log(f"文件大小: {os.path.getsize(self.temp_installer) / 1024 / 1024:.2f} MB")
        
        # 确认安装
        reply = QMessageBox.question(
            self, "确认更新",
            f"更新包已下载完成，是否立即安装？\n\n安装过程中程序将关闭。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.install_update()
        else:
            self.status_label.setText("已取消安装")
            self.log("用户取消安装")
    
    def install_update(self):
        """安装更新"""
        if not self.temp_installer or not os.path.exists(self.temp_installer):
            QMessageBox.critical(self, "错误", "安装包不存在")
            return
        
        self.log("开始安装更新...")
        self.log("关闭当前程序...")
        
        # 关闭launcher
        app_dir = get_app_dir()
        launcher_exe = os.path.join(app_dir, "launcher.exe")
        
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'launcher.exe'], 
                         capture_output=True, timeout=10)
            self.log("已关闭launcher")
        except:
            pass
        
        # 运行安装包
        self.log("运行安装包...")
        try:
            os.startfile(self.temp_installer)
            self.log("安装包已启动")
        except Exception as e:
            self.log(f"启动安装包失败: {e}")
            QMessageBox.critical(self, "错误", f"启动安装包失败:\n{e}")
            return
        
        # 关闭升级程序
        QTimer.singleShot(1000, self.close)
    


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    window = UpdaterWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
