# -*- coding: utf-8 -*-
"""
GM工具 - 游戏管理工具
功能：账号管理、角色管理、物品管理、邮件系统、日志记录
适用范围：单机版
"""

import os
import sys
import json
import struct
import sqlite3
import shutil
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

# PVF解析器（用于从PVF文件直接读取物品列表）
try:
    from pvf_parser import PVFParser
    PVF_PARSER_AVAILABLE = True
except ImportError:
    PVF_PARSER_AVAILABLE = False

# 全局PVF物品缓存
_pvf_items_cache = None
_pvf_parser_instance = None

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QMessageBox, QDialog, QFormLayout, QComboBox, QTabWidget,
    QTextEdit, QSplitter, QFrame, QScrollArea, QHeaderView, QSizePolicy,
    QAbstractItemView, QInputDialog, QFileDialog,
    QListWidget, QListWidgetItem, QCheckBox, QProgressBar
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QCursor, QPainter, QPen, QBrush, QIcon, QFontDatabase

# ============== 全局配置 ==============
APP_NAME = "GM工具"
APP_VERSION = "3.2.0"

def get_resource_path(relative_path):
    """获取资源文件的正确路径（支持PyInstaller打包后）"""
    import os
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后，先检查exe同级目录，再检查_internal目录
        exe_dir = os.path.dirname(sys.executable)
        local_path = os.path.join(exe_dir, relative_path)
        if os.path.exists(local_path):
            return local_path
        # onefile模式下，资源文件在sys._MEIPASS目录中
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return local_path
    else:
        # 开发环境下，使用当前目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

# ============== PVF物品加载功能 ==============
# .lst文件ID映射（文件路径 -> 物品ID）
_lst_id_map = {}
_lst_loaded = False

def load_lst_files(parser):
    """从PVF加载.lst文件，建立文件路径到物品ID的映射（大小写不敏感）"""
    global _lst_id_map, _lst_loaded
    if _lst_loaded:
        return
    
    import re
    _lst_id_map = {}
    
    # 解析stackable.lst
    try:
        content = parser.read_file_text('stackable/stackable.lst')
        pattern = r'(\d+)\s+`([^`]+)`'
        matches = re.findall(pattern, content)
        for item_id, file_path in matches:
            full_path = f"stackable/{file_path}" if not file_path.startswith('stackable/') else file_path
            _lst_id_map[full_path.lower()] = item_id
        print(f"从stackable.lst加载了 {len(matches)} 个消耗品ID")
    except Exception as e:
        print(f"加载stackable.lst失败: {e}")
    
    # 解析equipment.lst
    try:
        content = parser.read_file_text('equipment/equipment.lst')
        pattern = r'(\d+)\s+`([^`]+)`'
        matches = re.findall(pattern, content)
        for item_id, file_path in matches:
            full_path = f"equipment/{file_path}" if not file_path.startswith('equipment/') else file_path
            _lst_id_map[full_path.lower()] = item_id
        print(f"从equipment.lst加载了 {len(matches)} 个装备ID")
    except Exception as e:
        print(f"加载equipment.lst失败: {e}")
    
    _lst_loaded = True
    print(f".lst文件ID映射建立完成，共 {len(_lst_id_map)} 个条目")

def get_item_id_from_lst(archive_path):
    """从.lst映射获取物品ID（大小写不敏感），找不到则返回None"""
    return _lst_id_map.get(archive_path.lower())

# 物品数据字典缓存（ID -> 物品信息）
_pvf_items_dict_cache = None

def get_items_data_dict():
    """获取字典格式的物品数据（从全局缓存转换）"""
    global _pvf_items_dict_cache, _pvf_items_cache
    if _pvf_items_dict_cache is not None:
        return _pvf_items_dict_cache
    
    if _pvf_items_cache is None:
        return {}
    
    # 转换为字典格式
    items_dict = {}
    for item in _pvf_items_cache:
        item_id = str(item.get('id', ''))
        if item_id:
            items_dict[item_id] = item
    
    _pvf_items_dict_cache = items_dict
    return items_dict

def get_config_dir():
    """获取config目录路径"""
    try:
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        if os.path.basename(exe_dir) == "module":
            return os.path.join(exe_dir, 'config')
        else:
            # 优先当前目录的module/config
            config_dir = os.path.join(exe_dir, 'module', 'config')
            if os.path.exists(config_dir):
                return config_dir
            # 其次父目录的module/config
            config_dir = os.path.join(os.path.dirname(exe_dir), 'module', 'config')
            if os.path.exists(config_dir):
                return config_dir
            # 默认返回当前目录的module/config
            return os.path.join(exe_dir, 'module', 'config')
    except Exception:
        return os.path.join(os.getcwd(), 'module', 'config')


def get_pvf_path(config=None):
    """获取PVF文件路径（优先从配置读取，其次常见位置查找）"""
    # 如果传入了config对象，优先使用config的路径
    if config and hasattr(config, 'get_pvf_path'):
        pvf_path = config.get_pvf_path()
        if pvf_path and os.path.exists(pvf_path):
            return pvf_path
    
    # 从module/config/config.lau读取配置（由登录器创建）
    try:
        # 获取exe所在目录（打包后正确路径）
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 如果当前目录是module，配置在config子目录；否则在父目录的module/config
        if os.path.basename(exe_dir) == "module":
            possible_config_paths = [
                os.path.join(exe_dir, 'config', 'config.lau'),
            ]
        else:
            possible_config_paths = [
                os.path.join(exe_dir, 'module', 'config', 'config.lau'),
                os.path.join(os.path.dirname(exe_dir), 'module', 'config', 'config.lau'),
            ]
        
        for config_path in possible_config_paths:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                # 优先服务端路径
                server_path = cfg.get('server_path', '')
                if server_path:
                    server_pvf = os.path.join(server_path, 'runtime', 'data', 'dnf', 'Script.pvf')
                    if os.path.exists(server_pvf):
                        return server_pvf
                # 其次客户端路径
                client_path = cfg.get('client_path', '')
                if client_path:
                    client_pvf = os.path.join(client_path, 'Script.pvf')
                    if os.path.exists(client_pvf):
                        return client_pvf
    except Exception:
        pass
    
    # 常见位置
    possible_paths = [
        r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf',
        r'C:\Users\56518\Downloads\DNF_90S6A1\Script.pvf',
        os.path.join(os.getcwd(), 'Script.pvf'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def extract_item_name_from_pvf(parser, archive_path):
    """从PVF文件中解析物品的[name]标签，返回中文名称"""
    try:
        import struct
        raw = parser.read_file_raw(archive_path)
        if not raw or len(raw) < 5:
            return None
        
        # 解析脚本类型文件（data_type=1，5字节token）
        line_count = len(raw) // 5
        found_name = False
        
        for idx in range(line_count):
            off = idx * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            
            if token_type == 3:
                # 换行+字符串，检查是否是[name]标签
                text = parser._resolve_string(value)
                if text == '[name]':
                    found_name = True
                    continue
            
            if found_name and token_type == 6:
                # 反引号包裹的字符串，这就是物品名称
                name = parser._resolve_string(value)
                if name and not name.startswith('name_') and not name.startswith('flavor_'):
                    return name
                # 如果是引用格式，继续找下一个
                found_name = False
        
        return None
    except Exception as e:
        print(f"从PVF解析物品名称失败 ({archive_path}): {e}")
        return None

def has_chinese_name(name):
    """检查物品名称是否包含中文字符（用于过滤无中文名称的物品）"""
    if not name:
        return False
    # 检查是否包含中文字符
    for ch in name:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def should_filter_item(name):
    """检查物品是否应该被过滤（后续确认、测试物品、无中文名称等）"""
    if not name:
        return True
    
    # 过滤"后续确认"相关物品（包括((后续确认、后续确认等）
    if '后续确认' in name:
        return True
    
    # 过滤以"(("开头的物品（通常是未完成的测试物品）
    if name.startswith('(('):
        return True
    
    # 过滤以"物品_"开头的物品（通常是名称解析失败的默认名称）
    if name.startswith('物品_'):
        return True
    
    # 过滤无中文名称的物品
    if not has_chinese_name(name):
        return True
    
    return False

def extract_item_info_from_pvf(parser, archive_path, file_name=''):
    """从PVF文件解析物品完整信息（名称、类型、分类等）"""
    try:
        raw = parser.read_file_raw(archive_path)
        if not raw or len(raw) < 5:
            return None
        
        line_count = len(raw) // 5
        item_name = None
        item_type = None
        current_tag = None
        
        for i in range(line_count):
            off = i * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            
            if token_type == 3:
                text = parser._resolve_string(value)
                if text:
                    current_tag = text.strip('[]')
            elif token_type == 6 and current_tag:
                text = parser._resolve_string(value)
                if text:
                    if current_tag == 'name' and not item_name:
                        if not text.startswith('name_') and not text.startswith('flavor_'):
                            item_name = text
                    elif current_tag == 'stackable type' and not item_type:
                        item_type = text
                    elif current_tag == 'equipment type' and not item_type:
                        item_type = text
                current_tag = None
        
        # 从.lst映射获取准确的物品ID（优先）
        item_id = get_item_id_from_lst(archive_path)
        if not item_id:
            # 备用：从文件名提取最后一个数字作为ID（确保不与lst中的ID冲突）
            file_base = os.path.splitext(file_name)[0] if file_name else ''
            import re
            id_matches = re.findall(r'\d+', file_base)
            if id_matches:
                candidate_id = id_matches[-1]
                # 检查是否与lst中的ID冲突（通过反向查找）
                # 简单处理：如果数字长度>=6，认为是有效ID，否则用完整文件名
                if len(candidate_id) >= 6:
                    item_id = candidate_id
                else:
                    item_id = file_base
            else:
                item_id = file_base
        
        # 从路径推断分类和类型
        path_lower = archive_path.lower().replace('\\', '/')
        kind = 'stackable' if path_lower.startswith('stackable/') else 'equipment'
        category = '消耗品' if kind == 'stackable' else '装备'
        
        # 如果没有从标签获取到类型，从路径推断
        if not item_type:
            parts = path_lower.split('/')
            if len(parts) >= 2 and parts[0] == 'stackable':
                item_type = parts[1]
        
        return {
            'id': item_id,
            'name': item_name if item_name else f'物品_{item_id}',
            'path': archive_path,
            'category': category,
            'kind': kind,
            'type': item_type if item_type else '',
            'stackable_type': item_type if kind == 'stackable' and item_type else '',
            'equipment_type': item_type if kind == 'equipment' and item_type else '',
            'destination': '',
            'stack_limit': 0,
        }
    except Exception as e:
        print(f"从PVF解析物品信息失败 ({archive_path}): {e}")
        return None

def load_pvf_parser():
    """加载PVF解析器（单例模式）"""
    global _pvf_parser_instance
    if _pvf_parser_instance is not None:
        return _pvf_parser_instance
    
    if not PVF_PARSER_AVAILABLE:
        return None
    
    pvf_path = get_pvf_path()
    if not pvf_path:
        print("PVF文件未找到")
        return None
    
    try:
        print(f"正在加载PVF文件: {pvf_path}")
        parser = PVFParser(pvf_path)
        parser.load()
        _pvf_parser_instance = parser
        print(f"PVF加载成功，共 {parser.file_count} 个文件")
        
        # 加载.lst文件，建立物品ID映射
        load_lst_files(parser)
        
        return parser
    except Exception as e:
        print(f"PVF加载失败: {e}")
        return None

def load_items_from_pvf(progress_callback=None):
    """从PVF文件加载物品列表（完全基于PVF，不依赖items.json）"""
    global _pvf_items_cache
    if _pvf_items_cache is not None:
        if progress_callback:
            progress_callback(100, "使用缓存")
        return _pvf_items_cache
    
    parser = load_pvf_parser()
    if not parser:
        return None
    
    try:
        print("正在从PVF提取物品列表...")
        if progress_callback:
            progress_callback(5, "正在扫描PVF文件...")
        items = []
        
        # 查找所有.stk和.equ文件（物品文件）
        stk_files = parser.find_files_by_extension('.stk')
        equ_files = parser.find_files_by_extension('.equ')
        print(f"找到 {len(stk_files)} 个.stk文件, {len(equ_files)} 个.equ文件")
        
        # 用于记录已添加的物品ID（避免重复）
        added_item_ids = set()
        
        total_stk = len(stk_files)
        total_equ = len(equ_files)
        
        # 处理.stk文件（消耗品、材料等）
        for idx, file_info in enumerate(stk_files):
            archive_path = file_info['archive_path']
            file_name = file_info['name']
            
            # 进度回调（每100个文件更新一次，避免太频繁）
            if progress_callback and (idx % 100 == 0 or idx == total_stk - 1):
                progress = 10 + int((idx / max(total_stk, 1)) * 50)
                progress_callback(progress, f"处理消耗品: {idx}/{total_stk}")
            
            # 从PVF直接解析物品完整信息
            item_info = extract_item_info_from_pvf(parser, archive_path, file_name)
            if not item_info:
                continue
            
            item_id = item_info['id']
            item_name = item_info['name']
            category = item_info['category']
            kind = item_info['kind']
            item_type = item_info['type']
            
            # 过滤不可被玩家直接使用的道具类型
            type_for_check = item_type if item_type.startswith('[') else f'[{item_type}]'
            if kind == 'stackable' and type_for_check in FILTERED_STACKABLE_TYPES:
                continue
            
            # 过滤后续确认、测试物品、无中文名称等不可用物品
            if should_filter_item(item_name):
                continue
            
            # 翻译物品类型为中文
            translated_type = translate_item_type(
                kind=kind,
                equipment_type=item_info.get('equipment_type', ''),
                stackable_type=item_info.get('stackable_type', '')
            )
            item_info['type'] = translated_type
            
            # 避免重复添加
            if item_id and item_id not in added_item_ids:
                added_item_ids.add(item_id)
                items.append(item_info)
        
        # 处理.equ文件（装备、时装等）
        for idx, file_info in enumerate(equ_files):
            archive_path = file_info['archive_path']
            file_name = file_info['name']
            
            # 进度回调（每100个文件更新一次，避免太频繁）
            if progress_callback and (idx % 100 == 0 or idx == total_equ - 1):
                progress = 60 + int((idx / max(total_equ, 1)) * 35)
                progress_callback(progress, f"处理装备: {idx}/{total_equ}")
            
            # 只处理角色装备、时装和宠物（排除怪物装备等）
            path_lower = archive_path.lower().replace('\\', '/')
            is_character_equip = False
            if 'equipment/character/' in path_lower:
                is_character_equip = True
            elif '/avatar/' in path_lower and 'character/' in path_lower:
                is_character_equip = True
            elif 'equipment/creature/' in path_lower:
                is_character_equip = True  # 宠物
            
            if not is_character_equip:
                continue
            
            # 从PVF直接解析物品完整信息
            item_info = extract_item_info_from_pvf(parser, archive_path, file_name)
            if not item_info:
                continue
            
            item_id = item_info['id']
            item_name = item_info['name']
            
            # 过滤后续确认、测试物品、无中文名称等不可用物品
            if should_filter_item(item_name):
                continue
            
            # 翻译物品类型为中文
            kind = item_info.get('kind', 'equipment')
            translated_type = translate_item_type(
                kind=kind,
                equipment_type=item_info.get('equipment_type', ''),
                stackable_type=item_info.get('stackable_type', '')
            )
            item_info['type'] = translated_type
            
            # 避免重复添加
            if item_id and item_id not in added_item_ids:
                added_item_ids.add(item_id)
                items.append(item_info)
        
        print(f"从PVF提取了 {len(items)} 个物品（.stk:{len(stk_files)} + .equ:{len(equ_files)}）")
        if progress_callback:
            progress_callback(100, f"加载完成，共 {len(items)} 个物品")
        _pvf_items_cache = items
        return items
        
    except Exception as e:
        print(f"从PVF加载物品失败: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============== 样式定义（与launcher一致 - Win11黑色模式配色） ==============
GLOBAL_QSS = """
QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
    font-family: "Noto Sans SC", "Microsoft YaHei";
    font-size: 13px;
}

/* 表格选中高亮效果（蓝色） */
QTableWidget {
    gridline-color: #3a3a3a;
}

QTableWidget::item {
    padding: 4px 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #2a5a9a;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #2a4a7a;
}

QHeaderView::section {
    background-color: #2a2a2a;
    color: #cccccc;
    padding: 6px 8px;
    border: 1px solid #3a3a3a;
    font-weight: bold;
}

/* 列表选中高亮效果（蓝色） */
QListWidget {
    background-color: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
}

QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #2a5a9a;
    color: #ffffff;
}

QListWidget::item:hover {
    background-color: #2a4a7a;
}

/* 对话框中的按钮背景不透明 */
QDialog QPushButton {
    background-color: #1a2a4a;
    color: #ffffff;
    border: 1px solid #4a90d9;
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 13px;
    font-weight: bold;
}

QLabel {
    background-color: transparent;
}

QCheckBox {
    background-color: transparent;
}

QCheckBox::indicator {
    background-color: transparent;
    border: 1px solid #555555;
    border-radius: 3px;
    width: 14px;
    height: 14px;
}

QCheckBox::indicator:checked {
    background-color: #4a90d9;
    border: 1px solid #4a90d9;
}

QMainWindow {
    background-color: transparent;
}

#mainContainer {
    background-color: #2a2a2a;
    border: 1px solid #444444;
    border-radius: 10px;
}

#titleBar {
    background-color: transparent;
    border: none;
}

#titleLabel {
    color: #cccccc;
    font-size: 14px;
    font-weight: bold;
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

#titleBtn:pressed {
    background-color: #4a4a4a;
}

/* 关闭按钮样式 - 同步登录器Windows风格 */
#closeBtn {
    background-color: transparent;
    color: #888888;
    border: none;
    border-radius: 4px;
    padding: 0px;
    font-size: 13px;
    font-weight: bold;
}

#closeBtn:hover {
    background-color: #e81123;
    color: #ffffff;
}

#closeBtn:pressed {
    background-color: #c4101f;
}

#sidebar {
    background-color: #1e1e1e;
    border-right: 1px solid #2a2a2a;
}

/* 导航按钮样式 - 同步登录器风格 */
#navBtn {
    background-color: transparent;
    color: #a0a0a0;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    min-height: 28px;
}

#navBtn:hover {
    background-color: #252525;
    color: #e0e0e0;
}

#navBtn:pressed {
    background-color: #1a1a1a;
}

#navBtn.active {
    background-color: rgba(0,120,212,0.15);
    color: #4da6ff;
    border: none;
}

#contentArea {
    background-color: #202020;
}

QTableWidget {
    background-color: #1a1a1a;
    alternate-background-color: #222222;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    gridline-color: #333333;
    selection-background-color: #1a2a4a;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px;
    border: none;
    background-color: transparent;
}

QHeaderView::section {
    background-color: #252525;
    color: #ffffff;
    padding: 8px;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
    font-weight: bold;
}

QHeaderView::section:horizontal {
    background-color: #252525;
    border-bottom: 1px solid #333333;
}

QHeaderView::section:vertical {
    background-color: #252525;
    border-right: 1px solid #333333;
}

QTableCornerButton::section {
    background-color: #252525;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
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
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #4a4a4a;
    border-color: #5a5a5a;
    color: #ffffff;
    padding-top: 9px;
    padding-bottom: 7px;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #666666;
    border-color: #3a3a3a;
}

/* 刷新按钮样式 - 普通样式，宽高与全选/反选同步 */
QPushButton#refreshBtn {
    background-color: transparent;
    color: #cccccc;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 0px 12px;
    font-size: 13px;
}

QPushButton#refreshBtn:hover {
    background-color: #2a2a2a;
    border-color: #555555;
    color: #ffffff;
}

QPushButton#refreshBtn:pressed {
    background-color: #1a1a1a;
    border-color: #444444;
    color: #cccccc;
}

/* 对话框中的按钮样式 */
QDialog QPushButton#primaryBtn {
    background-color: #2d6cdf;
    color: #ffffff;
    border: 1px solid #2d6cdf;
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 13px;
    font-weight: bold;
}

QDialog QPushButton#primaryBtn:hover {
    background-color: #1a56c4;
    border-color: #1a56c4;
}

QDialog QPushButton#primaryBtn:pressed {
    background-color: #154a9e;
}

QDialog QPushButton#dangerBtn {
    background-color: #dc3545;
    color: #ffffff;
    border: 1px solid #dc3545;
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 13px;
    font-weight: bold;
}

QDialog QPushButton#dangerBtn:hover {
    background-color: #c82333;
    border-color: #c82333;
}

QDialog QPushButton#dangerBtn:pressed {
    background-color: #bd2130;
}

QDialog QPushButton#successBtn {
    background-color: #28a745;
    color: #ffffff;
    border: 1px solid #28a745;
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 13px;
    font-weight: bold;
}

QDialog QPushButton#successBtn:hover {
    background-color: #218838;
    border-color: #218838;
}

QDialog QPushButton#successBtn:pressed {
    background-color: #1e7e34;
}

QDialog QPushButton#normalBtn {
    background-color: #444444;
    color: #dddddd;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 13px;
    font-weight: bold;
}

QDialog QPushButton#normalBtn:hover {
    background-color: #555555;
    color: #ffffff;
    border-color: #666666;
}

QDialog QPushButton#normalBtn:pressed {
    background-color: #333333;
}

QLineEdit {
    background-color: #202020;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 8px 12px;
    selection-background-color: #4a90d9;
}

QLineEdit:focus {
    border: 1px solid #4a90d9;
}

QComboBox {
    background-color: #202020;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 8px 12px;
}

QComboBox:focus {
    border: 1px solid #4a90d9;
}

QComboBox QAbstractItemView {
    background-color: #202020;
    color: #ffffff;
    selection-background-color: #1a2a4a;
    border: 1px solid #4a4a4a;
}

QTextEdit {
    background-color: #202020;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 8px;
}

QTabWidget::pane {
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    background-color: #1a1a1a;
}

QTabBar::tab {
    background-color: #252525;
    color: #cccccc;
    padding: 8px 16px;
    border: 1px solid #333333;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #1a1a1a;
    color: #ffffff;
}

QTabBar::tab:hover {
    background-color: #333333;
}

QLabel#sectionTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
}

QLabel#statusLabel {
    color: #888888;
    font-size: 12px;
}

QLabel#statusLabelError {
    color: #ff4444;
    font-size: 12px;
}

QLabel#statusLabelSuccess {
    color: #4ade80;
    font-size: 12px;
}

#formCard {
    background-color: #202020;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
}

QLabel#formLabel {
    color: #cccccc;
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 4px;
    background-color: transparent;
}

QLineEdit#formInput, QComboBox#formInput {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit#formInput:focus, QComboBox#formInput:focus {
    border: 1px solid #4a90d9;
}

/* 主窗口中的发送按钮样式，和输入框同色 */
QPushButton#primaryBtn {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton#primaryBtn:hover {
    background-color: #3a3a3a;
    border-color: #5a5a5a;
}

QPushButton#primaryBtn:pressed {
    background-color: #4a4a4a;
}

QLabel#tipLabel {
    color: #888888;
    font-size: 11px;
    padding: 8px;
}

QListWidget {
    background-color: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 6px 8px;
    border-radius: 3px;
}

QListWidget::item:hover {
    background-color: #2a2a2a;
}

QListWidget::item:selected {
    background-color: #1a2a4a;
    color: #ffffff;
}

QScrollBar:vertical {
    width: 0px;
    background: transparent;
}

QScrollBar::handle:vertical {
    background: transparent;
    min-height: 0px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    height: 0px;
    background: transparent;
}

QScrollBar::handle:horizontal {
    background: transparent;
    min-width: 0px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QPushButton[linkButton="true"] {
    background-color: transparent;
    border: none;
    color: #4a90d9;
    text-decoration: underline;
    padding: 2px 8px;
    font-size: 12px;
}

QPushButton[linkButton="true"]:hover {
    color: #6ab0f9;
    background-color: rgba(74, 144, 217, 30);
}

QPushButton[linkButton="true"]:pressed {
    color: #3a7bc8;
}

QGroupBox {
    color: #4a90d9;
    font-size: 12px;
    font-weight: bold;
    border: 1px solid #2a4a6a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 15px;
    background-color: #1a2030;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
"""

# ============== 物品类型中文翻译 ==============
EQUIP_TYPE_MAP = {
    '[weapon]': '武器',
    '[coat]': '上衣',
    '[pants]': '下装',
    '[shoes]': '鞋子',
    '[shoulder]': '护肩',
    '[waist]': '腰带',
    '[ring]': '戒指',
    '[amulet]': '项链',
    '[wrist]': '手镯',
    '[support]': '辅助装备',
    '[magic stone]': '魔法石',
    '[earring]': '耳环',
    '[title name]': '称号',
    '[creature]': '宠物',
    '[charm]': '快捷栏装备',
    '[flag]': '旗帜',
    '[name tag]': '名称标签',
    '[support weapon]': '辅助武器',
    '[artifact red]': '红色宠物装备',
    '[artifact blue]': '蓝色宠物装备',
    '[artifact green]': '绿色宠物装备',
    '[coat avatar]': '上衣装扮',
    '[hat avatar]': '帽子装扮',
    '[pants avatar]': '下装装扮',
    '[shoes avatar]': '鞋子装扮',
    '[hair avatar]': '头发装扮',
    '[breast avatar]': '胸部装扮',
    '[face avatar]': '脸部装扮',
    '[waist avatar]': '腰带装扮',
    '[skin avatar]': '皮肤装扮',
    '[weapon avatar]': '武器装扮',
    '[aurora avatar]': '光环装扮',
    '[booster_item]': '礼盒内容物',
    '[booster]': '礼盒',
    '[skill weapon]': '技能武器',
    '[skill coat]': '技能上衣',
}

# 消耗品类型中文翻译
STACKABLE_TYPE_MAP = {
    '[recipe]': '设计图',
    '[material expert job]': '副职业材料',
    '[usable cera package]': '可用点券礼包',
    '[booster selection]': '自选礼盒',
    '[etc]': '其他',
    '[waste]': '消耗品',
    '[material]': '材料',
    '[upgradable legacy]': '传承',
    '[enchant waste]': '附魔材料',
    '[cera package]': '点券礼包',
    '[avatar emblem]': '装扮徽章',
    '[quest]': '任务物品',
    '[expert town potion]': '城镇专用药水',
    '[cera booster]': '点券礼盒',
    '[town and dungeon]': '城镇地下城通用',
    '[disguise]': '变身道具',
    '[unlimited waste]': '无限消耗品',
    '[couple room item]': '婚房物品',
    '[throw]': '投掷道具',
    '[auto enchant]': '自动附魔',
    '[dye]': '染色剂',
    '[legacy]': '传承',
    '[quest receive]': '任务获得',
    '[coupon]': '优惠券',
    '[contract]': '契约',
    '[flag gem]': '旗帜宝石',
    '[upgrade limit cube]': '升级限制方块',
    '[booster random]': '随机礼盒',
    '[random reward item]': '随机奖励物品',
    '[booster]': '礼盒',
    '[creature]': '宠物',
    '[feed]': '宠物饲料',
    '[set]': '套装',
    '[teleport potion]': '传送药水',
    '[gold kaleido]': '黄金品级调整箱',
    '[monster tarot card]': '怪物塔罗牌',
    '[random upgradable legacy]': '随机传承',
    '[auto use special buff]': '自动使用特殊Buff',
    '[unlimited town and dungeon]': '无限城镇地下城通用',
    '[waste instant item]': '杂物即时物品',
    '[multi upgradable legacy]': '多种传承',
    '[scale effect]': '缩放效果',
    '[only effect]': '仅效果',
    '[item upgrad buff usual upgrade]': '强化Buff药剂',
    '[creature expitem]': '宠物经验物品',
    '[avatar gift]': '装扮礼品',
}

# 不可被玩家直接使用的道具类型（过滤用）
FILTERED_STACKABLE_TYPES = {
    '[virtual]',                    # 虚拟物品
    '[global effect]',              # 全局效果
    '[equipment effect]',           # 装备特效
    '[item upgrad buff amplify upgrade]',  # 增幅Buff药剂
    '[roulette buff]',              # 轮盘Buff
    '[quiz item]',                  # 答题物品
    '[random goblin upgradable legacy]',   # 随机哥布林传承
    '[random ss upgradable legacy]',       # 随机史诗传承
    '[apc legacy]',                 # APC传承
    '[multi upgradable legacy bonus cera]', # 多种传承奖励点券
    '[stackable]',                  # 格式异常-通用可堆叠
    '[unlimited etc]',              # 无限其他
    '[npc teleport potion]',        # NPC传送药水
    '[random disguise]',            # 随机变身
    '[material instant item]',      # 材料即时物品
    '[stackable legacy]',           # 可堆叠传承（活动货币类）
}

# 附加类型中文翻译（交易属性等）
ATTACH_TYPE_MAP = {
    '[trade]': '可交易',
    '[account]': '账号绑定',
    '[free]': '无法交易',
    '[sealing]': '可密封',
    '[trade delete]': '交易后删除',
    '[trade limit]': '交易限制',
    '[sealing trade]': '密封交易',
}

KIND_MAP = {
    'equipment': '装备',
    'stackable': '消耗品',
    'booster_item': '礼盒内容物',
    'booster': '礼盒',
}

# 物品来源中文翻译
SOURCE_MAP = {
    'quest': '任务获得',
    'dungeon': '地下城掉落',
    'shop': '商店购买',
    'upgrade': '升级获得',
    'craft': '制作获得',
    'event': '活动获得',
    'mail': '邮件获得',
    'trade': '交易获得',
    'auction': '拍卖行购买',
    'gift': '礼品获得',
    'gm': 'GM发放',
    'system': '系统发放',
    'pvp': 'PVP获得',
    'guild': '公会获得',
    'pet': '宠物获得',
    'avatar': '装扮获得',
    'title': '称号获得',
    'creature': '宠物获得',
    'material': '材料获得',
    'recipe': '设计图获得',
    'package': '礼包获得',
    'box': '宝箱获得',
    'lottery': '抽奖获得',
    'daily': '每日获得',
    'weekly': '每周获得',
    'monthly': '每月获得',
    'achievement': '成就获得',
    'collection': '收藏获得',
    'explore': '探索获得',
    'secret': '秘密获得',
    'raid': '团本获得',
    'epic': '史诗获得',
    'legend': '传说获得',
    'unique': '独特获得',
    'rare': '稀有获得',
    'advanced': '高级获得',
    'normal': '普通获得',
    'low': '低级获得',
    'booster_item': '礼盒内容物',
    'booster': '礼盒开启',
}

def translate_source(source=''):
    """将物品来源翻译为中文"""
    if not source:
        return '未知'
    s = str(source).strip().lower()
    if s in SOURCE_MAP:
        return SOURCE_MAP[s]
    # 尝试部分匹配
    for key, value in SOURCE_MAP.items():
        if key in s:
            return value
    return str(source)

def translate_item_type(kind='', equipment_type='', stackable_type='', category=''):
    """将物品类型翻译为中文"""
    # 优先使用equipment_type
    if equipment_type and equipment_type != 'None':
        et = str(equipment_type).strip().lower()
        for key, value in EQUIP_TYPE_MAP.items():
            if key.lower() == et:
                return value
        # 没有匹配的，去掉括号返回
        return str(equipment_type).strip('[]')
    
    # 其次使用stackable_type（消耗品类型）
    if stackable_type and stackable_type != 'None':
        st = str(stackable_type).strip().lower()
        for key, value in STACKABLE_TYPE_MAP.items():
            if key.lower() == st:
                return value
        # 没有匹配的，去掉括号返回
        return str(stackable_type).strip('[]')
    
    # 其次使用kind
    if kind:
        k = str(kind).strip().lower()
        for key, value in KIND_MAP.items():
            if key.lower() == k:
                return value
    
    # 最后使用category
    if category:
        return str(category)
    
    return '未知'

def translate_attach_type(attach_type=''):
    """将附加类型（交易属性等）翻译为中文"""
    if not attach_type:
        return ''
    at = str(attach_type).strip().lower()
    for key, value in ATTACH_TYPE_MAP.items():
        if key.lower() == at:
            return value
    return str(attach_type)

# ============== 配置管理 ==============
class GMConfig:
    """GM工具配置管理 - 适配launcher新配置结构（config/config.lau，launcher/gmtool独立字段）"""
    
    def __init__(self):
        self.gm_dir = self._find_gm_dir()
        # 根目录（module目录的父目录，即launcher目录）
        self.root_dir = os.path.dirname(self.gm_dir) if os.path.basename(self.gm_dir) == "module" else self.gm_dir
        # launcher配置文件（由登录器创建，launcher和gmtool共享）
        self.launcher_config_file = self._find_launcher_config_file()
        # gmtool用户配置文件（储存用户设置和预设，设置改动时创建）
        self.config_dir = os.path.join(self.gm_dir, "config")
        self.config_file = os.path.join(self.config_dir, "config.lau")
        self.config = self._load_config()
        self.log_file = os.path.join(self.gm_dir, "gm_operations.log")
    
    def _find_gm_dir(self):
        """查找GM工具所在目录（module目录）"""
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 如果当前目录是module目录，直接返回
        if os.path.basename(exe_dir) == "module":
            return exe_dir
        
        # 检查父目录是否有module目录
        parent = os.path.dirname(exe_dir)
        module_dir = os.path.join(parent, "module")
        if os.path.exists(module_dir):
            return module_dir
        
        # 向上查找3级
        for _ in range(3):
            if os.path.exists(os.path.join(parent, "config", "config.lau")):
                return os.path.join(parent, "module") if os.path.exists(os.path.join(parent, "module")) else parent
            if os.path.exists(os.path.join(parent, "module", "config", "config.lau")):
                return os.path.join(parent, "module")
            parent = os.path.dirname(parent)
        
        return exe_dir
    
    def _find_launcher_config_file(self):
        """查找launcher配置文件 - 优先使用config文件夹下的config.lau"""
        # 优先使用launcher目录下的config/config.lau
        config_in_folder = os.path.join(self.root_dir, "config", "config.lau")
        if os.path.exists(config_in_folder):
            return config_in_folder
        
        # 兼容旧格式：launcher目录下的config.lau
        config_in_root = os.path.join(self.root_dir, "config.lau")
        if os.path.exists(config_in_root):
            return config_in_root
        
        # 兼容旧格式：launcher.lau
        old_config = os.path.join(self.root_dir, "launcher.lau")
        if os.path.exists(old_config):
            return old_config
        
        # 默认返回config文件夹下的config.lau（即使不存在，保存时会创建）
        return config_in_folder
    
    def _load_config(self):
        """加载配置（先从launcher配置文件读取基础配置，再从gmtool用户配置读取用户设置和预设）"""
        default_config = {
            "server_path": "",
            "client_path": "",
            "db_mode": "mysql",
            "pvf_path": "",
            "presets": {}  # 预设配置（金币/点券默认方向等）
        }
        
        # 1. 先从launcher配置文件读取基础配置（由登录器创建，launcher和gmtool共享）
        if os.path.exists(self.launcher_config_file):
            try:
                with open(self.launcher_config_file, 'r', encoding='utf-8') as f:
                    launcher_config = json.load(f)
                
                # 检查是否是新格式（包含launcher或gmtool字段）
                if "launcher" in launcher_config or "gmtool" in launcher_config:
                    # 新格式：从launcher字段中读取基础配置
                    launcher_section = launcher_config.get("launcher", {})
                    
                    # 映射字段：launcher字段中的go_server_path/python_server_path映射到server_path
                    server_type = launcher_section.get("server_type", "go")
                    if server_type == "go":
                        default_config["server_path"] = launcher_section.get("go_server_path", "")
                    else:
                        default_config["server_path"] = launcher_section.get("python_server_path", "")
                    
                    default_config["client_path"] = launcher_section.get("client_path", "")
                    
                    # 从gmtool字段读取db_mode和pvf_path
                    gmtool_section = launcher_config.get("gmtool", {})
                    default_config["db_mode"] = gmtool_section.get("db_mode", "mysql")
                    default_config["pvf_path"] = gmtool_section.get("pvf_path", "")
                    default_config["last_character_id"] = gmtool_section.get("last_character_id", "")
                    
                    # 从gmtool字段读取预设
                    if "presets" in gmtool_section:
                        default_config["presets"] = gmtool_section["presets"]
                else:
                    # 旧格式：直接用配置文件的内容更新默认配置
                    for key in ["server_path", "client_path", "db_mode", "pvf_path", "presets", "last_character_id"]:
                        if key in launcher_config:
                            default_config[key] = launcher_config[key]
            except Exception as e:
                print(f"加载launcher配置失败: {e}")
        
        # 2. 再从gmtool用户配置文件读取用户设置和预设（设置改动时才创建）
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 用户配置优先，覆盖launcher配置中的对应字段
                    for key in ["server_path", "client_path", "db_mode", "pvf_path", "presets", "last_character_id"]:
                        if key in user_config:
                            default_config[key] = user_config[key]
            except Exception as e:
                print(f"加载用户配置失败: {e}")
        
        return default_config
    
    def save_config(self):
        """保存用户设置和预设到launcher配置文件的gmtool字段（与登录器共享配置）"""
        try:
            # 确保launcher配置文件目录存在
            launcher_config_dir = os.path.dirname(self.launcher_config_file)
            os.makedirs(launcher_config_dir, exist_ok=True)
            
            # 读取现有的launcher配置文件
            launcher_config = {}
            if os.path.exists(self.launcher_config_file):
                try:
                    with open(self.launcher_config_file, 'r', encoding='utf-8') as f:
                        launcher_config = json.load(f)
                except Exception as e:
                    print(f"读取launcher配置失败: {e}")
                    launcher_config = {}
            
            # 确保配置结构正确
            if "launcher" not in launcher_config:
                launcher_config["launcher"] = {}
            if "gmtool" not in launcher_config:
                launcher_config["gmtool"] = {}
            
            # 将gmtool的用户设置和预设保存到gmtool字段
            launcher_config["gmtool"]["server_path"] = self.config.get("server_path", "")
            launcher_config["gmtool"]["client_path"] = self.config.get("client_path", "")
            launcher_config["gmtool"]["db_mode"] = self.config.get("db_mode", "mysql")
            launcher_config["gmtool"]["pvf_path"] = self.config.get("pvf_path", "")
            launcher_config["gmtool"]["presets"] = self.config.get("presets", {})
            launcher_config["gmtool"]["settings"] = self.config.get("settings", {})
            launcher_config["gmtool"]["last_character_id"] = self.config.get("last_character_id", "")
            
            # 保存到launcher配置文件
            with open(self.launcher_config_file, 'w', encoding='utf-8') as f:
                json.dump(launcher_config, f, ensure_ascii=False, indent=4)
            
            # 同时删除旧的module/config/config.lau（如果存在）
            if os.path.exists(self.config_file):
                try:
                    os.remove(self.config_file)
                    print(f"已删除旧的用户配置文件: {self.config_file}")
                except Exception as e:
                    print(f"删除旧配置文件失败: {e}")
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get_preset(self, key, default=None):
        """获取预设配置"""
        presets = self.config.get("presets", {})
        return presets.get(key, default)
    
    def set_preset(self, key, value):
        """设置预设配置"""
        if "presets" not in self.config:
            self.config["presets"] = {}
        self.config["presets"][key] = value
        self.save_config()
    
    def get_server_path(self):
        return self.config.get("server_path", "")
    
    def get_client_path(self):
        return self.config.get("client_path", "")
    
    def get_pvf_path(self):
        """获取PVF文件路径，优先服务端，其次客户端"""
        # 如果配置中已设置pvf_path，直接返回
        pvf_path = self.config.get("pvf_path", "")
        if pvf_path and os.path.exists(pvf_path):
            return pvf_path
        
        # 优先使用服务端路径下的PVF
        server_path = self.get_server_path()
        if server_path:
            server_pvf = os.path.join(server_path, "runtime", "data", "dnf", "Script.pvf")
            if os.path.exists(server_pvf):
                return server_pvf
        
        # 其次使用客户端路径下的PVF
        client_path = self.get_client_path()
        if client_path:
            client_pvf = os.path.join(client_path, "Script.pvf")
            if os.path.exists(client_pvf):
                return client_pvf
        
        # 都不存在，返回空
        return ""
    
    def get_db_mode(self):
        return self.config.get("db_mode", "sqlite")
    
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
    
    def log_operation(self, operation, details=""):
        """记录操作日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {operation}"
        if details:
            log_entry += f" - {details}"
        log_entry += "\n"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"记录日志失败: {e}")

# ============== 数据库管理 ==============
class GMDatabase:
    """GM工具数据库管理"""
    
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
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        if self.mysql_conn:
            self.mysql_conn.close()
            self.mysql_conn = None
    
    def execute_query(self, query, params=None):
        """执行查询语句"""
        if self.db_mode == "mysql":
            return self._mysql_query(query, params)
        else:
            return self._sqlite_query(query, params)
    
    def _sqlite_query(self, query, params=None):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def _mysql_query(self, query, params=None):
        if not self.mysql_conn:
            return []
        # pymysql使用 %s 占位符，自动转换 ? 为 %s
        query = query.replace('?', '%s')
        # 连接时已设置 cursorclass=pymysql.cursors.DictCursor，直接使用默认cursor
        with self.mysql_conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query, params=None):
        """执行更新语句"""
        if self.db_mode == "mysql":
            return self._mysql_update(query, params)
        else:
            return self._sqlite_update(query, params)
    
    def _sqlite_update(self, query, params=None):
        if not self.conn:
            return False
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.conn.commit()
        return True
    
    def _mysql_update(self, query, params=None):
        if not self.mysql_conn:
            return False
        # pymysql使用 %s 占位符，自动转换 ? 为 %s
        query = query.replace('?', '%s')
        with self.mysql_conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
        self.mysql_conn.commit()
        return True
    
    def get_tables(self):
        """获取所有表名"""
        if self.db_mode == "mysql":
            result = self.execute_query("SHOW TABLES")
            return [list(row.values())[0] for row in result]
        else:
            result = self.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            return [row['name'] for row in result]

# ============== 通用对话框（圆角风格） ==============
class GMDialog(QDialog):
    """GM工具通用对话框（圆角风格）"""
    
    def __init__(self, title="", parent=None, show_back=False):
        super().__init__(parent)
        # 无边框 + 对话框（只在程序内最上层，不全局置顶）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        self.dragging = False
        self.drag_position = QPoint()
        self.show_back = show_back
        
        self.init_ui(title)
    
    def init_ui(self, title):
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet("""
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #4a4a4a;
        """)
        
        layout = QVBoxLayout(self.main_container)
        layout.setContentsMargins(12, 12, 12, 16)
        layout.setSpacing(12)
        
        # 一体化标题行（标题文字 + 关闭按钮）
        title_container = QWidget()
        title_container.setStyleSheet("background-color: transparent; border: none;")
        self.title_row = QHBoxLayout(title_container)
        self.title_row.setContentsMargins(0, 0, 0, 0)
        self.title_row.setSpacing(8)
        
        # 返回按钮（可选）
        if self.show_back:
            back_btn = QPushButton("←")
            back_btn.setObjectName("titleBtn")
            back_btn.setFixedSize(28, 24)
            back_btn.setCursor(Qt.PointingHandCursor)
            back_btn.clicked.connect(self.reject)
            self.title_row.addWidget(back_btn)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setStyleSheet("color: #e0e0e0; font-size: 16px; font-weight: bold; background-color: transparent; border: none;")
        self.title_row.addWidget(self.title_label)
        
        self.title_row.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(28, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        self.title_row.addWidget(close_btn)
        
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
        
        # 使整个窗口可拖动
        self.main_container.mousePressEvent = self.mousePressEvent
        self.main_container.mouseMoveEvent = self.mouseMoveEvent
        self.main_container.mouseReleaseEvent = self.mouseReleaseEvent
        self.main_container.mouseDoubleClickEvent = self.on_title_double_click
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_container)
    
    def on_title_double_click(self, event):
        self.showMinimized()
    
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
        btn = QPushButton(text)
        if btn_type == "danger":
            btn.setObjectName("dangerBtn")
        elif btn_type == "success":
            btn.setObjectName("successBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click)
        self.button_layout.addWidget(btn)
        return btn

# ============== 通用确认对话框（无边框，支持自定义按钮样式和位置） ==============
class GMConfirmDialog(GMDialog):
    """通用确认对话框 - 支持自定义按钮样式和位置"""
    
    def __init__(self, title="确认", message="", confirm_text="确认", cancel_text="取消",
                 confirm_style="normal", confirm_position="right", parent=None,
                 hide_title=False, dark_background=False):
        """
        Args:
            title: 对话框标题
            message: 提示消息
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
            confirm_style: 确认按钮样式 (normal/danger/success)
            confirm_position: 确认按钮位置 (right/left)
            hide_title: 是否隐藏标题栏文字
            dark_background: 是否使用更暗的背景
        """
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.confirm_style = confirm_style
        self.confirm_position = confirm_position
        self.hide_title = hide_title
        self.dark_background = dark_background
        self.result = False
        super().__init__(title, parent)
        # 设置紧凑宽度
        self.setMaximumWidth(420)
        self.setMinimumWidth(320)
        
        # 隐藏标题栏文字
        if hide_title and hasattr(self, 'title_label'):
            self.title_label.setVisible(False)
        
        # 更暗的背景
        if dark_background and hasattr(self, 'main_container'):
            self.main_container.setStyleSheet("""
                background-color: #1e1e1e;
                border-radius: 8px;
                border: 1px solid #3a3a3a;
            """)
            # 移除内容区域和按钮区域的容器背景色，让主容器背景透出来
            if hasattr(self, 'content_widget'):
                self.content_widget.setStyleSheet("background-color: transparent; border: none;")
            if hasattr(self, 'button_widget'):
                self.button_widget.setStyleSheet("background-color: transparent; border: none;")
        
        self.init_content()
    
    def init_content(self):
        """初始化内容 - 一体式深灰风格"""
        # 消息文字
        msg_label = QLabel(self.message)
        msg_label.setObjectName("dialogMessage")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setStyleSheet("""
            color: #e0e0e0;
            font-size: 14px;
            line-height: 1.6;
            background-color: transparent;
            padding: 12px 0;
        """)
        self.content_layout.addWidget(msg_label)
        self.content_layout.addSpacing(8)
        
        # 按钮区域
        has_cancel = bool(self.cancel_text and self.cancel_text.strip())
        
        def make_button(text):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.setMinimumWidth(120)
            # 统一按钮样式，深灰风格
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    padding: 8px 32px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #5a5a5a;
                }
            """)
            return btn
        
        # 按钮居中布局
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        self.button_layout.addStretch()
        
        if has_cancel:
            # 有两个按钮时，按confirm_position排列
            if self.confirm_position == "left":
                # 确认按钮在左，取消按钮在右
                confirm_btn = make_button(self.confirm_text)
                confirm_btn.clicked.connect(self.on_confirm)
                self.button_layout.addWidget(confirm_btn)
                
                self.button_layout.addSpacing(16)
                
                cancel_btn = make_button(self.cancel_text)
                cancel_btn.clicked.connect(self.on_cancel)
                self.button_layout.addWidget(cancel_btn)
            else:
                # 取消按钮在左，确认按钮在右
                cancel_btn = make_button(self.cancel_text)
                cancel_btn.clicked.connect(self.on_cancel)
                self.button_layout.addWidget(cancel_btn)
                
                self.button_layout.addSpacing(16)
                
                confirm_btn = make_button(self.confirm_text)
                confirm_btn.clicked.connect(self.on_confirm)
                self.button_layout.addWidget(confirm_btn)
        else:
            # 只有一个按钮时，居中显示
            confirm_btn = make_button(self.confirm_text)
            confirm_btn.clicked.connect(self.on_confirm)
            self.button_layout.addWidget(confirm_btn)
        
        self.button_layout.addStretch()
    
    def on_confirm(self):
        self.result = True
        self.accept()
    
    def on_cancel(self):
        self.result = False
        self.reject()
    
    @staticmethod
    def confirm(parent, title="确认", message="", confirm_text="确认", cancel_text="取消",
                confirm_style="normal", confirm_position="right",
                hide_title=False, dark_background=False):
        """静态方法：显示确认对话框
        如果只有一个确认按钮（cancel_text为空），则改为静默式，只在状态栏显示，不弹出对话框
        """
        # 如果只有一个确认按钮（无害提示弹窗），改为静默式
        if not cancel_text or not cancel_text.strip():
            # 静默式：只在状态栏显示，不弹出对话框
            if parent and hasattr(parent, 'status_label'):
                parent.status_label.setText(f"{title}: {message}")
            # 记录到操作日志
            if parent and hasattr(parent, 'config') and hasattr(parent.config, 'log_operation'):
                try:
                    parent.config.log_operation(title, message)
                except Exception:
                    pass
            return True
        
        # 有取消按钮时，显示确认对话框
        dialog = GMConfirmDialog(title, message, confirm_text, cancel_text,
                                  confirm_style, confirm_position, parent,
                                  hide_title=hide_title, dark_background=dark_background)
        dialog.exec_()
        return dialog.result

# ============== 货币调整对话框 ==============
class GMAdjustDialog(GMDialog):
    """货币调整对话框 - 调整金币或点券"""
    
    def __init__(self, adjust_type="gold", character_id=None, character_name="", 
                 account_id=None, db=None, parent=None, preset_direction=None):
        """
        Args:
            adjust_type: 调整类型 (gold/cera)
            character_id: 角色ID
            character_name: 角色名称
            account_id: 账号ID
            db: 数据库连接
            parent: 父窗口
            preset_direction: 预设方向 (add/reduce/None)，有预设时只显示确定/取消按钮
        """
        self.adjust_type = adjust_type
        self.character_id = character_id
        self.character_name = character_name
        self.account_id = account_id
        self.db = db
        self.current_value = 0
        self.result = False
        self.preset_direction = preset_direction  # 预设方向
        
        title = "调整金币" if adjust_type == "gold" else "调整点券"
        super().__init__(title, parent)
        # 框体宽度继续变窄
        self.setMinimumWidth(340)
        self.setMaximumWidth(380)
        self.init_content()
        self.load_current_value()
    
    def init_content(self):
        """初始化内容"""
        # 当前值显示 - 放在标题栏上，配色改为浅灰
        type_name = "金币" if self.adjust_type == "gold" else "点券"
        current_label = QLabel(f"当前{type_name}: 加载中...")
        current_label.setObjectName("dialogMessage")
        current_label.setAlignment(Qt.AlignCenter)
        current_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 12px;
            font-weight: normal;
            background-color: transparent;
            padding: 0 8px;
        """)
        self.current_label = current_label
        # 在标题标签和stretch之间插入当前值标签
        # 先找到stretch的位置（标题标签之后）
        # title_row: [返回按钮(可选)] [标题标签] [stretch] [关闭按钮]
        # 我们在标题标签之后插入当前值标签
        stretch_index = self.title_row.indexOf(self.title_label) + 1
        self.title_row.insertWidget(stretch_index, current_label)
        
        # 输入框（左对齐，与最左侧按钮对齐，宽度=三个按钮+间距=294）
        self.amount_input = QLineEdit()
        self.amount_input.setObjectName("formInput")
        self.amount_input.setPlaceholderText(f"输入{type_name}数量")
        self.amount_input.setMinimumHeight(32)
        self.amount_input.setFixedWidth(294)
        self.amount_input.setStyleSheet("""
            QLineEdit#formInput {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit#formInput:focus {
                border: 1px solid #4a90d9;
            }
        """)
        # 居中布局：前后都加stretch，前面加2像素spacer微调
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.addStretch()
        input_row.addSpacing(2)  # 输入框向右微调
        input_row.addWidget(self.amount_input)
        input_row.addStretch()
        self.content_layout.addLayout(input_row)
        self.content_layout.addSpacing(8)
        
        # 按钮区域 - 取消紧贴，恢复有间距的布局
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(12)
        
        # 统一按钮宽度和高度
        btn_width = 90
        btn_height = 34
        
        # 预设模式：有预设方向时只显示确定/取消按钮
        if self.preset_direction:
            self.button_layout.addStretch()
            
            # 确定按钮（按照预设方向执行）
            type_name = "金币" if self.adjust_type == "gold" else "点券"
            action_name = "增加" if self.preset_direction == "add" else "减少"
            if self.adjust_type == "cera":
                action_name = "充值" if self.preset_direction == "add" else "回收"
            
            confirm_btn = QPushButton(f"确定{action_name}")
            confirm_btn.setCursor(Qt.PointingHandCursor)
            confirm_btn.setFixedSize(btn_width + 20, btn_height)
            confirm_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d6cdf;
                    color: #ffffff;
                    border: 1px solid #2d6cdf;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1a56c4;
                    border-color: #1a56c4;
                }
                QPushButton:pressed {
                    background-color: #154a9e;
                }
            """)
            confirm_btn.clicked.connect(lambda: self.adjust_value(self.preset_direction))
            self.button_layout.addWidget(confirm_btn)
            
            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.setFixedSize(btn_width, btn_height)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #5a5a5a;
                }
            """)
            cancel_btn.clicked.connect(self.on_cancel)
            self.button_layout.addWidget(cancel_btn)
            
            self.button_layout.addStretch()
        elif self.adjust_type == "gold":
            # 金币调整：增加/减少（居中布局）
            self.button_layout.addStretch()
            
            add_btn = QPushButton("增加金币")
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setFixedSize(btn_width, btn_height)
            add_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d6cdf;
                    color: #ffffff;
                    border: 1px solid #2d6cdf;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1a56c4;
                    border-color: #1a56c4;
                }
                QPushButton:pressed {
                    background-color: #154a9e;
                }
            """)
            add_btn.clicked.connect(lambda: self.adjust_value("add"))
            self.button_layout.addWidget(add_btn)
            
            reduce_btn = QPushButton("减少金币")
            reduce_btn.setCursor(Qt.PointingHandCursor)
            reduce_btn.setFixedSize(btn_width, btn_height)
            reduce_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: #ffffff;
                    border: 1px solid #dc3545;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                    border-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
            reduce_btn.clicked.connect(lambda: self.adjust_value("reduce"))
            self.button_layout.addWidget(reduce_btn)
            
            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.setFixedSize(btn_width, btn_height)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #5a5a5a;
                }
            """)
            cancel_btn.clicked.connect(self.on_cancel)
            self.button_layout.addWidget(cancel_btn)
            
            self.button_layout.addStretch()
        else:
            # 点券调整：充值/回收（居中布局）
            self.button_layout.addStretch()
            
            recharge_btn = QPushButton("充值点券")
            recharge_btn.setCursor(Qt.PointingHandCursor)
            recharge_btn.setFixedSize(btn_width, btn_height)
            recharge_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d6cdf;
                    color: #ffffff;
                    border: 1px solid #2d6cdf;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1a56c4;
                    border-color: #1a56c4;
                }
                QPushButton:pressed {
                    background-color: #154a9e;
                }
            """)
            recharge_btn.clicked.connect(lambda: self.adjust_value("add"))
            self.button_layout.addWidget(recharge_btn)
            
            recycle_btn = QPushButton("回收点券")
            recycle_btn.setCursor(Qt.PointingHandCursor)
            recycle_btn.setFixedSize(btn_width, btn_height)
            recycle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: #ffffff;
                    border: 1px solid #dc3545;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                    border-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
            recycle_btn.clicked.connect(lambda: self.adjust_value("reduce"))
            self.button_layout.addWidget(recycle_btn)
            
            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.setFixedSize(btn_width, btn_height)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #5a5a5a;
                }
            """)
            cancel_btn.clicked.connect(self.on_cancel)
            self.button_layout.addWidget(cancel_btn)
            
            self.button_layout.addStretch()
    
    def load_current_value(self):
        """加载当前值"""
        try:
            if self.adjust_type == "gold":
                query = "SELECT gold FROM dnf_characters WHERE character_id = ?"
                result = self.db.execute_query(query, (self.character_id,))
                self.current_value = result[0]['gold'] if result else 0
                type_name = "金币"
            else:
                query = "SELECT entry_value FROM dnf_account_metadata WHERE account_id = ? AND entry_key = 'account_cera'"
                result = self.db.execute_query(query, (self.account_id,))
                self.current_value = int(result[0]['entry_value']) if result else 0
                type_name = "点券"
            
            self.current_label.setText(f"当前{type_name}: {self.current_value:,}")
        except Exception as e:
            self.current_label.setText(f"加载失败: {str(e)}")
    
    def adjust_value(self, mode):
        """调整值"""
        amount_text = self.amount_input.text().strip()
        if not amount_text:
            GMConfirmDialog.confirm(self, "提示", "请输入数量", "确定", "", "normal", "right")
            return
        
        try:
            amount = int(amount_text)
            if amount <= 0:
                GMConfirmDialog.confirm(self, "提示", "数量必须大于0", "确定", "", "normal", "right")
                return
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的数字", "确定", "", "normal", "right")
            return
        
        if mode == "reduce" and amount > self.current_value:
            GMConfirmDialog.confirm(self, "提示", "减少数量不能大于当前数量", "确定", "", "normal", "right")
            return
        
        try:
            if mode == "add":
                new_value = self.current_value + amount
                action = "增加"
            else:
                new_value = self.current_value - amount
                action = "减少"
            
            if self.adjust_type == "gold":
                query = "UPDATE dnf_characters SET gold = ? WHERE character_id = ?"
                self.db.execute_update(query, (new_value, self.character_id))
                type_name = "金币"
            else:
                query = """
                    INSERT INTO dnf_account_metadata (account_id, entry_key, entry_value)
                    VALUES (?, 'account_cera', ?)
                    ON DUPLICATE KEY UPDATE entry_value = ?
                """
                self.db.execute_update(query, (self.account_id, str(new_value), str(new_value)))
                type_name = "点券"
            
            self.current_value = new_value
            self.current_label.setText(f"当前{type_name}: {new_value:,}")
            self.amount_input.clear()
            self.result = True
            
            GMConfirmDialog.confirm(
                self,
                title="调整成功",
                message=f"{type_name}已成功{action}！\n\n角色: {self.character_name}\n{action}数量: {amount:,}\n当前{type_name}: {new_value:,}",
                confirm_text="确定",
                cancel_text="",
                confirm_style="success",
                confirm_position="right"
            )
            
        except Exception as e:
            GMConfirmDialog.confirm(self, "错误", f"调整失败: {str(e)}", "确定", "", "danger", "right")
    
    def on_cancel(self):
        """取消"""
        self.result = False
        self.close()

# ============== 装备管理对话框（强化增幅） ==============
class EquipmentManagerDialog(GMDialog):
    """装备管理对话框 - 查看和修改装备强化增幅"""
    
    AMPLIFY_TYPE_MAP = {
        0: "无增幅",
        1: "异次元体力",
        2: "异次元精神",
        3: "异次元力量",
        4: "异次元智力"
    }
    
    def __init__(self, character_id, character_name, db, parent=None):
        self.character_id = character_id
        self.character_name = character_name
        self.db = db
        self.equipments = []
        self.items_dict = {}  # item_id -> item_info
        self._load_items_json()
        super().__init__(f"装备管理 - {character_name}", parent)
        self.setMinimumWidth(800)
        self.setMinimumHeight(550)
        QTimer.singleShot(100, self.load_equipments)
    
    def _load_items_json(self):
        """加载物品信息用于显示物品中文名称（从PVF读取）"""
        try:
            # 从PVF加载
            pvf_items = load_items_from_pvf()
            if pvf_items:
                for item in pvf_items:
                    item_id = str(item.get('id', ''))
                    if item_id:
                        self.items_dict[item_id] = item
                print(f"已从PVF加载 {len(self.items_dict)} 个物品信息")
            else:
                print("PVF加载失败，物品名称将使用默认值")
        except Exception as e:
            print(f"加载物品信息失败: {e}")
    
    def _get_item_name(self, item_id):
        """根据物品ID获取中文名称"""
        item_info = self.items_dict.get(str(item_id), {})
        name = item_info.get('name', '')
        if name:
            return name
        return f"未知物品({item_id})"
    
    def _is_equipment(self, item_id):
        """判断是否为装备（严格过滤装扮、称号、宠物等），并过滤低等级低稀有度装备"""
        item_info = self.items_dict.get(str(item_id), {})
        equipment_type = item_info.get('equipment_type', '')
        category = item_info.get('category', '')
        name = item_info.get('name', '')
        path = item_info.get('path', '')
        
        # 严格定义真正的装备类型（排除所有装扮、称号、宠物等）
        valid_equip_types = [
            '[weapon]',      # 武器
            '[coat]',         # 上衣
            '[pants]',        # 下装
            '[shoulder]',     # 头肩
            '[waist]',        # 腰带
            '[shoes]',        # 鞋子
            '[ring]',         # 戒指
            '[amulet]',       # 项链
            '[wrist]',        # 手镯
            '[support]',      # 辅助装备
            '[magic stone]',  # 魔法石
            '[earring]'       # 耳环
        ]
        
        # 必须是有效的装备类型
        if equipment_type not in valid_equip_types:
            return False
        
        # 过滤掉明显的装扮类（通过路径判断）
        if 'avatar' in path.lower() or 'avatar' in equipment_type.lower():
            return False
        
        # 过滤称号、宠物、光环等
        if 'title' in path.lower() or 'creature' in path.lower() or 'aurora' in path.lower():
            return False
        
        # 过滤等级<55级、稀有度<稀有的装备
        return self._filter_by_level_and_rarity(item_id, item_info)
    
    def _filter_by_level_and_rarity(self, item_id, item_info):
        """根据等级和稀有度过滤装备，只保留>=55级、>=稀有度的装备"""
        name = item_info.get('name', '')
        path = item_info.get('path', '')
        equipment_type = item_info.get('equipment_type', '')
        
        # 高稀有度关键词（直接保留）
        high_rarity_keywords = [
            '传承', '圣物', '史诗', '传说', '神器', '勇者', '异界',
            '荒古', '圣耀', '苍穹', '夜雨', '太极', '星之海', '神之意象',
            '刺骨', '爆裂', '血舞', '炎月', '冰霜', '雷鸣', '瞬杀',
            '流光', '屠戮', '无影', '崩山', '嗜魂', '暴走'
        ]
        
        for keyword in high_rarity_keywords:
            if keyword in name:
                return True
        
        # 通过item_id范围判断等级（放宽范围，确保60级装备显示）
        try:
            id_int = int(item_id)
            
            # 根据装备类型判断等级阈值
            # 武器：27000+，55级以上通常id >= 27500
            # 布甲/皮甲上衣：10000-15000，55级以上通常id >= 12000
            # 轻甲/重甲/板甲：20000-27000，55级以上通常id >= 22000
            # 首饰：30000-40000，55级以上通常id >= 33000
            # 特殊装备：40000-50000，55级以上通常id >= 43000
            # 100000+通常是高级装备
            
            if equipment_type == '[weapon]':
                if id_int >= 27500:
                    return True
            elif equipment_type in ['[coat]', '[pants]', '[shoulder]', '[waist]', '[shoes]']:
                # 防具
                if (10000 <= id_int < 20000 and id_int >= 12000) or \
                   (20000 <= id_int < 27000 and id_int >= 22000) or \
                   id_int >= 100000:
                    return True
            elif equipment_type in ['[ring]', '[amulet]', '[wrist]']:
                # 首饰
                if id_int >= 33000:
                    return True
            elif equipment_type in ['[support]', '[magic stone]', '[earring]']:
                # 特殊装备
                if id_int >= 43000:
                    return True
            elif id_int >= 100000:
                # 高级装备
                return True
            
            # 名称中包含等级信息的（如"55级"、"60级"等）
            import re
            level_match = re.search(r'(\d+)级', name)
            if level_match:
                level = int(level_match.group(1))
                if level >= 55:
                    return True
            
            # 路径中包含等级信息的
            path_level_match = re.search(r'_l(\d+)', path)
            if path_level_match:
                level = int(path_level_match.group(1))
                if level >= 55:
                    return True
            
            # 过滤掉明显的低等级装备（名称中包含"破损的"、"生锈的"、"破旧的"等）
            low_level_keywords = ['破损的', '生锈的', '破旧的', '腐烂的', '劣质的', '粗糙的']
            for keyword in low_level_keywords:
                if keyword in name:
                    return False
            
            # 默认过滤掉（不确定的低等级低稀有度装备）
            return False
            
        except Exception:
            # 解析失败时，通过名称关键词判断
            for keyword in high_rarity_keywords:
                if keyword in name:
                    return True
            return False
    
    def init_ui(self, title):
        super().init_ui(title)
        
        # 装备表格
        self.equip_table = QTableWidget()
        self.equip_table.setColumnCount(7)
        self.equip_table.setHorizontalHeaderLabels(["槽位", "物品ID", "物品名称", "强化等级", "增幅类型", "增幅数值", "操作"])
        self.equip_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.equip_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # 物品名称列拉伸
        self.equip_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.equip_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.equip_table.setAlternatingRowColors(True)
        # 减少行高
        self.equip_table.verticalHeader().setDefaultSectionSize(38)
        self.equip_table.verticalHeader().setMinimumSectionSize(38)
        self.content_layout.addWidget(self.equip_table)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_equipments)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        self.content_layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.content_layout.addWidget(self.status_label)
    
    def load_equipments(self):
        """加载角色装备列表"""
        try:
            # 查询装备条目
            query = """
                SELECT e.entry_key, e.slot_index, e.item_id, e.bind_flag
                FROM dnf_equipment_entries e
                WHERE e.character_id = %s
                ORDER BY e.slot_index
            """
            equipments = self.db.execute_query(query, (self.character_id,))
            
            self.equipments = []
            self.equip_table.setRowCount(0)
            
            for equip in equipments:
                entry_key = equip['entry_key']
                slot_index = equip['slot_index']
                item_id = equip['item_id']
                
                # 过滤非装备物品（时装、宠物等）
                if not self._is_equipment(item_id):
                    continue
                
                # 查询装备的extra信息（强化增幅）
                extra_query = """
                    SELECT extra_key, extra_value
                    FROM dnf_equipment_entry_extra
                    WHERE character_id = %s AND entry_key = %s
                      AND extra_key IN ('reinforce', 'upgrade_level', 'amplify_type', 'amplify_value', 'amplification_type', 'amplification_value')
                """
                extras = self.db.execute_query(extra_query, (self.character_id, entry_key))
                
                extra_dict = {e['extra_key']: e['extra_value'] for e in extras}
                
                reinforce = int(extra_dict.get('reinforce', 0))
                upgrade_level = int(extra_dict.get('upgrade_level', 0))
                amplify_type = int(extra_dict.get('amplify_type', extra_dict.get('amplification_type', 0)))
                amplify_value = int(extra_dict.get('amplify_value', extra_dict.get('amplification_value', 0)))
                
                # 获取物品中文名称
                item_name = self._get_item_name(item_id)
                
                equip_info = {
                    'entry_key': entry_key,
                    'slot_index': slot_index,
                    'item_id': item_id,
                    'item_name': item_name,
                    'reinforce': reinforce,
                    'upgrade_level': upgrade_level,
                    'amplify_type': amplify_type,
                    'amplify_value': amplify_value
                }
                self.equipments.append(equip_info)
                
                # 添加到表格
                row = self.equip_table.rowCount()
                self.equip_table.insertRow(row)
                
                self.equip_table.setItem(row, 0, QTableWidgetItem(str(slot_index)))
                self.equip_table.setItem(row, 1, QTableWidgetItem(str(item_id)))
                self.equip_table.setItem(row, 2, QTableWidgetItem(item_name))
                self.equip_table.setItem(row, 3, QTableWidgetItem(f"+{reinforce}"))
                
                amplify_type_name = self.AMPLIFY_TYPE_MAP.get(amplify_type, f"未知({amplify_type})")
                self.equip_table.setItem(row, 4, QTableWidgetItem(amplify_type_name))
                self.equip_table.setItem(row, 5, QTableWidgetItem(f"+{amplify_value}" if amplify_value > 0 else "0"))
                
                # 操作按钮（链接式）
                modify_btn = QPushButton("修改")
                modify_btn.setProperty("linkButton", True)
                modify_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #4a90d9;
                        border: none;
                        padding: 4px 8px;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        color: #6ab0f9;
                        text-decoration: underline;
                    }
                    QPushButton:pressed {
                        color: #2a70b9;
                    }
                """)
                modify_btn.setCursor(Qt.PointingHandCursor)
                modify_btn.clicked.connect(lambda checked, idx=row: self.modify_equipment(idx))
                self.equip_table.setCellWidget(row, 6, modify_btn)
            
            self.status_label.setText(f"已加载 {len(self.equipments)} 件装备")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def modify_equipment(self, row):
        """修改装备强化增幅"""
        if row >= len(self.equipments):
            return
        
        equip = self.equipments[row]
        
        # 创建修改对话框
        dialog = GMDialog(f"修改装备 - 槽位{equip['slot_index']}", self)
        dialog.setMinimumWidth(350)
        
        # 强化等级
        reinforce_label = QLabel("强化等级:")
        reinforce_label.setObjectName("formLabel")
        dialog.content_layout.addWidget(reinforce_label)
        
        reinforce_input = QLineEdit(str(equip['reinforce']))
        reinforce_input.setObjectName("formInput")
        dialog.content_layout.addWidget(reinforce_input)
        
        # 增幅类型
        amplify_type_label = QLabel("增幅类型:")
        amplify_type_label.setObjectName("formLabel")
        dialog.content_layout.addWidget(amplify_type_label)
        
        amplify_type_combo = QComboBox()
        for type_id, type_name in self.AMPLIFY_TYPE_MAP.items():
            amplify_type_combo.addItem(f"{type_id} - {type_name}", type_id)
        amplify_type_combo.setCurrentIndex(equip['amplify_type'] if equip['amplify_type'] <= 4 else 0)
        dialog.content_layout.addWidget(amplify_type_combo)
        
        # 增幅数值
        amplify_value_label = QLabel("增幅数值:")
        amplify_value_label.setObjectName("formLabel")
        dialog.content_layout.addWidget(amplify_value_label)
        
        amplify_value_input = QLineEdit(str(equip['amplify_value']))
        amplify_value_input.setObjectName("formInput")
        dialog.content_layout.addWidget(amplify_value_input)
        
        dialog.content_layout.addStretch()
        
        # 按钮
        def on_save():
            try:
                new_reinforce = int(reinforce_input.text())
                new_amplify_type = amplify_type_combo.currentData()
                new_amplify_value = int(amplify_value_input.text())
                
                if new_reinforce < 0 or new_reinforce > 31:
                    GMConfirmDialog.confirm(dialog, "提示", "强化等级范围: 0-31", "确定", "", "normal", "right")
                    return
                
                if new_amplify_value < 0 or new_amplify_value > 31:
                    GMConfirmDialog.confirm(dialog, "提示", "增幅数值范围: 0-31", "确定", "", "normal", "right")
                    return
                
                self.save_equipment_modification(equip['entry_key'], new_reinforce, new_amplify_type, new_amplify_value)
                dialog.accept()
                self.load_equipments()
                
            except ValueError:
                GMConfirmDialog.confirm(dialog, "提示", "请输入有效的数字", "确定", "", "normal", "right")
        
        save_btn = dialog.add_button("保存", on_save, "success")
        cancel_btn = dialog.add_button("取消", dialog.reject)
        
        dialog.exec_()
    
    def save_equipment_modification(self, entry_key, reinforce, amplify_type, amplify_value):
        """保存装备修改到数据库"""
        try:
            # 更新或插入reinforce
            self._upsert_extra(entry_key, 'reinforce', str(reinforce))
            # 更新或插入upgrade_level（与reinforce同步）
            self._upsert_extra(entry_key, 'upgrade_level', str(reinforce))
            
            # 更新或插入增幅
            if amplify_type > 0:
                self._upsert_extra(entry_key, 'amplify_type', str(amplify_type))
                self._upsert_extra(entry_key, 'amplification_type', str(amplify_type))
                self._upsert_extra(entry_key, 'amplify_value', str(amplify_value))
                self._upsert_extra(entry_key, 'amplification_value', str(amplify_value))
            else:
                # 移除增幅
                self._delete_extra(entry_key, 'amplify_type')
                self._delete_extra(entry_key, 'amplification_type')
                self._delete_extra(entry_key, 'amplify_value')
                self._delete_extra(entry_key, 'amplification_value')
            
            self.status_label.setText(f"装备修改成功: 强化+{reinforce}, 增幅+{amplify_value}")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"保存失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"保存失败: {str(e)}", "确定", "", "danger", "right")
    
    def _upsert_extra(self, entry_key, extra_key, extra_value):
        """更新或插入装备extra字段"""
        # 先检查是否存在
        query = """
            SELECT COUNT(*) as cnt FROM dnf_equipment_entry_extra
            WHERE character_id = %s AND entry_key = %s AND extra_key = %s
        """
        result = self.db.execute_query(query, (self.character_id, entry_key, extra_key))
        
        if result and result[0]['cnt'] > 0:
            # 更新
            update_query = """
                UPDATE dnf_equipment_entry_extra
                SET extra_value = %s
                WHERE character_id = %s AND entry_key = %s AND extra_key = %s
            """
            self.db.execute_update(update_query, (extra_value, self.character_id, entry_key, extra_key))
        else:
            # 插入
            insert_query = """
                INSERT INTO dnf_equipment_entry_extra (character_id, entry_key, extra_key, extra_value)
                VALUES (%s, %s, %s, %s)
            """
            self.db.execute_update(insert_query, (self.character_id, entry_key, extra_key, extra_value))
    
    def _delete_extra(self, entry_key, extra_key):
        """删除装备extra字段"""
        delete_query = """
            DELETE FROM dnf_equipment_entry_extra
            WHERE character_id = %s AND entry_key = %s AND extra_key = %s
        """
        self.db.execute_update(delete_query, (self.character_id, entry_key, extra_key))

# ============== 角色管理模块 ==============
class CharacterManagerWidget(QWidget):
    """角色管理模块"""
    
    def __init__(self, db, config, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.current_characters = []
        self.init_ui()
        QTimer.singleShot(100, self.load_characters)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("角色管理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索角色名...")
        self.search_input.returnPressed.connect(self.load_characters)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.load_characters)
        search_layout.addWidget(search_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_characters)
        search_layout.addWidget(refresh_btn)
        
        layout.addLayout(search_layout)
        
        # 角色表格
        self.char_table = QTableWidget()
        self.char_table.setColumnCount(8)
        self.char_table.setHorizontalHeaderLabels(["角色ID", "角色名", "账号", "等级", "职业", "转职阶段", "经验值", "最后登录"])
        self.char_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.char_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.char_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.char_table.setAlternatingRowColors(True)
        # 隐藏角色ID列
        self.char_table.setColumnHidden(0, True)
        layout.addWidget(self.char_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.modify_level_btn = QPushButton("调整等级")
        self.modify_level_btn.clicked.connect(self.modify_level)
        btn_layout.addWidget(self.modify_level_btn)
        
        self.modify_gold_btn = QPushButton("开启黑钻")
        self.modify_gold_btn.clicked.connect(self.open_black_dragon)
        btn_layout.addWidget(self.modify_gold_btn)
        
        self.equip_manager_btn = QPushButton("装备管理")
        self.equip_manager_btn.clicked.connect(self.open_equipment_manager)
        self.equip_manager_btn.setEnabled(False)  # 装备管理功能保持禁用状态
        btn_layout.addWidget(self.equip_manager_btn)
        
        self.delete_btn = QPushButton("删除角色")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self.delete_character)
        btn_layout.addWidget(self.delete_btn)
        
        self.cleanup_btn = QPushButton("清理已删除数据")
        self.cleanup_btn.setObjectName("warningBtn")
        self.cleanup_btn.clicked.connect(self.cleanup_deleted_characters)
        btn_layout.addWidget(self.cleanup_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
    
    def _get_current_account(self):
        """获取当前登录账号 - 从launcher配置文件读取last_account"""
        try:
            # 从config对象获取launcher配置文件路径
            launcher_config_file = getattr(self.config, 'launcher_config_file', None)
            if not launcher_config_file:
                # 尝试从root_dir构建路径
                root_dir = getattr(self.config, 'root_dir', None)
                if root_dir:
                    launcher_config_file = os.path.join(root_dir, "config", "config.lau")
            
            if launcher_config_file and os.path.exists(launcher_config_file):
                with open(launcher_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 新格式：从launcher字段中读取last_account
                if "launcher" in config_data:
                    return config_data["launcher"].get("last_account", "")
                # 旧格式：直接读取last_account
                else:
                    return config_data.get("last_account", "")
        except Exception as e:
            print(f"获取当前登录账号失败: {e}")
        
        return ""
    
    def load_characters(self):
        """加载角色列表 - 只显示当前登录账号的角色"""
        try:
            keyword = self.search_input.text().strip()
            
            # 角色表是 dnf_characters
            char_table = 'dnf_characters'
            
            # 获取当前登录账号（从launcher配置文件读取last_account）
            current_account = self._get_current_account()
            
            # 根据账号名查询账号ID（从dnf_login_accounts表查询）
            account_id = None
            if current_account:
                try:
                    account_query = "SELECT account_id FROM dnf_login_accounts WHERE username = ? LIMIT 1"
                    account_result = self.db.execute_query(account_query, (current_account,))
                    if account_result and len(account_result) > 0:
                        account_id = account_result[0].get('account_id')
                except Exception as e:
                    print(f"查询账号ID失败: {e}")
            
            # 构建查询条件
            conditions = ["delete_flag = 0"]
            params = []
            
            # 如果有关键词，添加搜索条件
            if keyword:
                conditions.append("name LIKE ?")
                params.append(f"%{keyword}%")
            
            # 如果有当前账号ID，只查询该账号的角色
            if account_id is not None:
                conditions.append("account_id = ?")
                params.append(account_id)
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {char_table} WHERE {where_clause} LIMIT 100"
            characters = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)
            
            # 职业/转职/觉醒完整映射表（参考.chr文件）
            # 结构: job -> {base: 基础职业名, chr: .chr路径, transfers: {grow_index: {name: 转职名, awaken1: 一次觉醒, awaken2: 二次觉醒}}}
            job_class_map = {
                '0': {
                    'base': '鬼剑士', 'chr': 'Swordman/Swordman.chr',
                    'transfers': {
                        1: {'name': '剑魂', 'awaken1': '剑圣', 'awaken2': '剑神'},
                        2: {'name': '鬼泣', 'awaken1': '弑魂', 'awaken2': '黑暗君主'},
                        3: {'name': '狂战士', 'awaken1': '狱血魔神', 'awaken2': '帝血弑天'},
                        4: {'name': '阿修罗', 'awaken1': '大暗黑天', 'awaken2': '天帝'},
                    }
                },
                '1': {
                    'base': '格斗家', 'chr': 'Fighter/Fighter.chr',
                    'transfers': {
                        1: {'name': '气功师', 'awaken1': '百花缭乱', 'awaken2': '念帝'},
                        2: {'name': '散打', 'awaken1': '武神', 'awaken2': '极武圣'},
                        3: {'name': '街霸', 'awaken1': '毒王', 'awaken2': '毒神绝'},
                        4: {'name': '柔道家', 'awaken1': '暴风眼', 'awaken2': '风暴女皇'},
                    }
                },
                '2': {
                    'base': '神枪手', 'chr': 'Gunner/Gunner.chr',
                    'transfers': {
                        1: {'name': '漫游枪手', 'awaken1': '枪神', 'awaken2': '掠天之翼'},
                        2: {'name': '枪炮师', 'awaken1': '狂暴者', 'awaken2': '毁灭者'},
                        3: {'name': '机械师', 'awaken1': '机械战神', 'awaken2': '机械元首'},
                        4: {'name': '弹药专家', 'awaken1': '大将军', 'awaken2': '战场统治者'},
                    }
                },
                '3': {
                    'base': '魔法师', 'chr': 'Mage/Mage.chr',
                    'transfers': {
                        1: {'name': '元素师', 'awaken1': '大魔导师', 'awaken2': '元素圣灵'},
                        2: {'name': '召唤师', 'awaken1': '月之女皇', 'awaken2': '月蚀'},
                        3: {'name': '战斗法师', 'awaken1': '贝亚娜斗神', 'awaken2': '伊斯塔战灵'},
                        4: {'name': '魔道学者', 'awaken1': '魔术师', 'awaken2': '古灵精怪'},
                    }
                },
                '4': {
                    'base': '圣职者', 'chr': 'Priest/Priest.chr',
                    'transfers': {
                        1: {'name': '圣骑士', 'awaken1': '天启者', 'awaken2': '神思者'},
                        2: {'name': '蓝拳圣使', 'awaken1': '神之手', 'awaken2': '正义仲裁者'},
                        3: {'name': '驱魔师', 'awaken1': '龙斗士', 'awaken2': '真龙星君'},
                        4: {'name': '复仇者', 'awaken1': '末日审判者', 'awaken2': '永生者'},
                    }
                },
                '5': {
                    'base': '神枪手(女)', 'chr': 'Gunner/ATGunner.chr',
                    'transfers': {
                        1: {'name': '漫游枪手', 'awaken1': '沾血蔷薇', 'awaken2': '绯红玫瑰'},
                        2: {'name': '枪炮师', 'awaken1': '重炮掌控者', 'awaken2': '风暴骑兵'},
                        3: {'name': '机械师', 'awaken1': '机械之心', 'awaken2': '机械之灵'},
                        4: {'name': '弹药专家', 'awaken1': '战争女神', 'awaken2': '芙蕾雅'},
                    }
                },
                '6': {
                    'base': '暗夜使者', 'chr': 'Thief/Thief.chr',
                    'transfers': {
                        1: {'name': '刺客', 'awaken1': '银月', 'awaken2': '月影星劫'},
                        2: {'name': '死灵术士', 'awaken1': '灵魂收割者', 'awaken2': '亡魂主宰'},
                        3: {'name': '忍者', 'awaken1': '毕方之炎', 'awaken2': '不知火'},
                        4: {'name': '影舞者', 'awaken1': '梦魇', 'awaken2': '幽冥'},
                    }
                },
                '7': {
                    'base': '格斗家(男)', 'chr': 'Fighter/ATFighter.chr',
                    'transfers': {
                        1: {'name': '气功师', 'awaken1': '狂虎帝', 'awaken2': '念皇'},
                        2: {'name': '散打', 'awaken1': '武极', 'awaken2': '极武皇'},
                        3: {'name': '街霸', 'awaken1': '千手罗汉', 'awaken2': '暗街之王'},
                        4: {'name': '柔道家', 'awaken1': '风林火山', 'awaken2': '宗师'},
                    }
                },
                '8': {
                    'base': '魔法师(男)', 'chr': 'Mage/ATMage.chr',
                    'transfers': {
                        1: {'name': '元素爆破师', 'awaken1': '魔皇', 'awaken2': '湮灭之瞳'},
                        2: {'name': '冰结师', 'awaken1': '冰冻之心', 'awaken2': '刹那永恒'},
                        3: {'name': '血法师', 'awaken1': '血狱伯爵', 'awaken2': '血狱君主'},
                        4: {'name': '逐风者', 'awaken1': '御风者', 'awaken2': '风神'},
                        5: {'name': '次元行者', 'awaken1': '虚空行者', 'awaken2': '混沌行者'},
                    }
                },
                '9': {
                    'base': '黑暗武士', 'chr': 'Swordman/DSSwordman.chr',
                    'transfers': {}
                },
                '10': {
                    'base': '缔造者', 'chr': 'Mage/CreatorMage.chr',
                    'transfers': {}
                },
                '11': {
                    'base': '鬼剑士(女)', 'chr': 'Swordman/ATSwordman.chr',
                    'transfers': {
                        1: {'name': '驭剑士', 'awaken1': '剑宗', 'awaken2': '剑皇'},
                        2: {'name': '暗殿骑士', 'awaken1': '暗帝', 'awaken2': '裁决女神'},
                        3: {'name': '契魔者', 'awaken1': '剑魔', 'awaken2': '弑神者'},
                        4: {'name': '流浪武士', 'awaken1': '剑豪', 'awaken2': '剑帝'},
                    }
                },
                '12': {
                    'base': '守护者', 'chr': 'Knight/Knight.chr',
                    'transfers': {
                        1: {'name': '精灵骑士', 'awaken1': '星辰之光', 'awaken2': '大地女神'},
                        2: {'name': '混沌魔灵', 'awaken1': '黑魔后', 'awaken2': '黑曜神'},
                        3: {'name': '帕拉丁', 'awaken1': '曙光', 'awaken2': '破晓女神'},
                        4: {'name': '龙骑士', 'awaken1': '龙皇', 'awaken2': '龙神'},
                    }
                },
                '13': {
                    'base': '魔枪士', 'chr': 'DemonicLancer/DemonicLancer.chr',
                    'transfers': {
                        1: {'name': '征战者', 'awaken1': '战魂', 'awaken2': '不灭战神'},
                        2: {'name': '决战者', 'awaken1': '无双之魂', 'awaken2': '圣武枪魂'},
                        3: {'name': '狩猎者', 'awaken1': '征服之魂', 'awaken2': '屠戮之魂'},
                        4: {'name': '暗枪士', 'awaken1': '狂怒恶鬼', 'awaken2': '幽影夜神'},
                    }
                },
                '14': {
                    'base': '圣职者(女)', 'chr': 'Priest/ATPriest.chr',
                    'transfers': {
                        1: {'name': '圣骑士', 'awaken1': '福音传道者', 'awaken2': '炽天使'},
                        2: {'name': '异端审判者', 'awaken1': '神焰处刑官', 'awaken2': '炎狱裁决者'},
                        3: {'name': '巫女', 'awaken1': '神女', 'awaken2': '神龙天女'},
                        4: {'name': '诱魔者', 'awaken1': '断罪者', 'awaken2': '救世主'},
                    }
                },
                '15': {
                    'base': '枪剑士', 'chr': 'GunBlader/GunBlader.chr',
                    'transfers': {
                        1: {'name': '暗刃', 'awaken1': '统御者', 'awaken2': '铁血统帅'},
                        2: {'name': '特工', 'awaken1': '绝命谍影', 'awaken2': '弑心镇魂者'},
                        3: {'name': '战线佣兵', 'awaken1': '战场王牌', 'awaken2': '巅峰狂徒'},
                        4: {'name': '源能专家', 'awaken1': '源力掌控者', 'awaken2': '未来开拓者'},
                    }
                },
            }
            
            # 觉醒技能ID映射表（从.chr文件的[awakening skill]标签提取）
            # 结构: job -> [growtype列表], 每个growtype包含 awaken1（一次觉醒技能ID）和 awaken2（二次觉醒技能ID）
            awaken_skill_map = {
                '0': [  # 鬼剑士
                    {'growtype': 0, 'awaken1': [86, 91], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [89, 87], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [90, 85], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [92, 88], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '1': [  # 格斗家
                    {'growtype': 0, 'awaken1': [72, 67], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [70, 71], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [65, 64], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [66, 63], 'awaken2': []},
                ],
                '2': [  # 神枪手
                    {'growtype': 0, 'awaken1': [66, 64], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [65, 54], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [68, 67], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [69, 70], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '3': [  # 魔法师
                    {'growtype': 0, 'awaken1': [73, 74], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [75, 82], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [84, 83], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [110, 109], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '4': [  # 圣职者
                    {'growtype': 0, 'awaken1': [86, 84], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [87, 90], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [89, 93], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [122, 135, 120, 119], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '5': [  # 神枪手(女)
                    {'growtype': 0, 'awaken1': [94, 233], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [93, 97], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [95, 96], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [99, 98], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '6': [  # 暗夜使者
                    {'growtype': 0, 'awaken1': [56, 57], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [58, 59], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [97, 98], 'awaken2': [73]},
                    {'growtype': 3, 'awaken1': [117, 114], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '7': [  # 格斗家(男)
                    {'growtype': 0, 'awaken1': [114, 67], 'awaken2': [242]},
                    {'growtype': 1, 'awaken1': [65, 41], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [116, 105], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [115, 63], 'awaken2': []},
                ],
                '8': [  # 魔法师(男)
                    {'growtype': 0, 'awaken1': [51, 49], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [50, 48], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [126, 127], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [82, 83], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [107, 108], 'awaken2': []},
                ],
                '9': [  # 黑暗武士
                    {'growtype': 0, 'awaken1': [], 'awaken2': []},
                ],
                '10': [  # 缔造者
                    {'growtype': 0, 'awaken1': [], 'awaken2': []},
                ],
                '11': [  # 鬼剑士(女)
                    {'growtype': 0, 'awaken1': [52, 54], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [75, 74], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [42, 19], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [72, 73], 'awaken2': []},
                    {'growtype': 4, 'awaken1': [], 'awaken2': []},
                ],
                '12': [  # 守护者
                    {'growtype': 0, 'awaken1': [43, 51], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [87, 76], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [120, 121], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [144, 143], 'awaken2': []},
                ],
                '13': [  # 魔枪士
                    {'growtype': 0, 'awaken1': [52, 55], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [24, 25], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [68, 86], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [102, 103], 'awaken2': []},
                ],
                '14': [  # 圣职者(女)
                    {'growtype': 0, 'awaken1': [33, 34], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [50, 51], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [64, 65], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [83, 77], 'awaken2': []},
                ],
                '15': [  # 枪剑士
                    {'growtype': 0, 'awaken1': [71, 72], 'awaken2': []},
                    {'growtype': 1, 'awaken1': [49, 12], 'awaken2': []},
                    {'growtype': 2, 'awaken1': [34, 33], 'awaken2': []},
                    {'growtype': 3, 'awaken1': [94, 93], 'awaken2': []},
                ],
            }
            
            # 查询所有角色的技能数据（用于判断觉醒状态）
            character_skills = {}
            try:
                skill_query = "SELECT character_id, skill_id FROM dnf_skill_states WHERE skill_level > 0"
                skill_results = self.db.execute_query(skill_query)
                for sr in skill_results:
                    cid = sr.get('character_id', '')
                    sid = sr.get('skill_id', 0)
                    if cid not in character_skills:
                        character_skills[cid] = set()
                    character_skills[cid].add(sid)
            except Exception as e:
                print(f"查询角色技能失败: {e}")
            
            self.current_characters = characters
            self.char_table.setRowCount(len(characters))
            
            for row, char in enumerate(characters):
                # 角色ID
                char_id = char.get('character_id', char.get('id', ''))
                self.char_table.setItem(row, 0, QTableWidgetItem(str(char_id)))
                
                # 角色名
                char_name = char.get('name', '')
                self.char_table.setItem(row, 1, QTableWidgetItem(str(char_name)))
                
                # 账号ID
                account_id = char.get('account_id', '')
                self.char_table.setItem(row, 2, QTableWidgetItem(str(account_id)))
                
                # 等级
                level = char.get('level', 0)
                self.char_table.setItem(row, 3, QTableWidgetItem(str(level)))
                
                # 职业（调用辅助函数解析职业信息）
                job_name, transfer_stage = self._parse_character_job_info(
                    char, character_skills, job_class_map, awaken_skill_map
                )
                self.char_table.setItem(row, 4, QTableWidgetItem(job_name))
                
                # 转职阶段列
                self.char_table.setItem(row, 5, QTableWidgetItem(transfer_stage))
                
                # 经验
                exp = char.get('exp', 0)
                self.char_table.setItem(row, 6, QTableWidgetItem(str(exp)))
                
                # 最后登录（用 updated_at 代替）
                last_login = char.get('updated_at', '')
                self.char_table.setItem(row, 7, QTableWidgetItem(str(last_login)))
            
            self.status_label.setText(f"共加载 {len(characters)} 个角色")
            self.status_label.setObjectName("statusLabelSuccess")
            self.config.log_operation("加载角色列表", f"共{len(characters)}个角色")
            
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def _parse_character_job_info(self, char, character_skills, job_class_map, awaken_skill_map):
        """
        解析角色职业信息（从load_characters提取）
        返回: (job_name, transfer_stage)
        """
        job = str(char.get('job', ''))
        grow_type = int(char.get('grow_type', 0))
        char_id = char.get('character_id', char.get('id', ''))
        char_skill_set = character_skills.get(char_id, set())
        
        # 获取该职业该转职的觉醒技能ID
        awaken1_skills = []
        awaken2_skills = []
        if job in awaken_skill_map and grow_type > 0:
            job_awaken_list = awaken_skill_map[job]
            job_int = int(job)
            grow_index = grow_type - job_int * 8
            if grow_index < 1 or grow_index > len(job_awaken_list):
                grow_index = grow_type
            awaken_idx = grow_index - 1
            if 0 <= awaken_idx < len(job_awaken_list):
                awaken1_skills = job_awaken_list[awaken_idx].get('awaken1', [])
                awaken2_skills = job_awaken_list[awaken_idx].get('awaken2', [])
        
        # 判断觉醒状态
        has_awaken2 = any(sid in char_skill_set for sid in awaken2_skills) if awaken2_skills else False
        has_awaken1 = any(sid in char_skill_set for sid in awaken1_skills) if awaken1_skills else False
        
        if has_awaken2:
            awaken_level = 2
        elif has_awaken1:
            awaken_level = 1
        elif grow_type > 0:
            awaken_level = 0
        else:
            awaken_level = -1
        
        # 根据职业映射表获取职业名称和转职阶段
        if job in job_class_map:
            job_info = job_class_map[job]
            base_name = job_info['base']
            transfers = job_info['transfers']
            
            if grow_type == 0:
                job_name = base_name
                transfer_stage = "未转职"
            else:
                job_int = int(job)
                grow_index = grow_type - job_int * 8
                if grow_index not in transfers and grow_type in transfers:
                    grow_index = grow_type
                
                if grow_index in transfers:
                    transfer_info = transfers[grow_index]
                    transfer_name = transfer_info['name']
                    awaken1_name = transfer_info['awaken1']
                    awaken2_name = transfer_info['awaken2']
                    
                    if awaken_level >= 2:
                        job_name = awaken2_name
                        transfer_stage = "二次觉醒"
                    elif awaken_level >= 1:
                        job_name = awaken1_name
                        transfer_stage = "已觉醒"
                    else:
                        job_name = transfer_name
                        transfer_stage = "已转职"
                else:
                    job_name = f'{base_name}(未知转职)'
                    transfer_stage = "未知转职"
        else:
            job_name = f'未知职业(job={job}, grow={grow_type})'
            transfer_stage = "未知"
        
        return job_name, transfer_stage
    
    def get_selected_character(self):
        """获取选中的角色"""
        current_row = self.char_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_characters):
            GMConfirmDialog.confirm(self, "提示", "请先选择一个角色", "确定", "", "normal", "right")
            return None
        return self.current_characters[current_row]
    
    def open_equipment_manager(self):
        """打开装备管理对话框"""
        char = self.get_selected_character()
        if not char:
            GMConfirmDialog.confirm(self, "提示", "请先选择一个角色", "确定", "", "normal", "right")
            return
        
        character_id = char.get('character_id', char.get('id', ''))
        char_name = char.get('name', char.get('char_name', ''))
        
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "无法获取角色ID", "确定", "", "normal", "right")
            return
        
        dialog = EquipmentManagerDialog(str(character_id), char_name, self.db, self)
        dialog.exec_()
    
    def modify_level(self):
        """调整等级"""
        char = self.get_selected_character()
        if not char:
            return
        
        char_name = char.get('char_name', char.get('name', ''))
        current_level = char.get('level', 0)
        
        dialog = GMDialog("调整等级", self)
        form_layout = QFormLayout()
        
        char_label = QLabel(f"角色: {char_name}")
        form_layout.addRow(char_label)
        
        current_label = QLabel(f"当前等级: {current_level}")
        form_layout.addRow(current_label)
        
        level_input = QLineEdit()
        level_input.setPlaceholderText("输入新的等级 (1-90)")
        level_input.setText(str(current_level))
        form_layout.addRow("新等级:", level_input)
        
        dialog.content_layout.addLayout(form_layout)
        
        def on_ok():
            try:
                new_level = int(level_input.text())
                if new_level < 1 or new_level > 90:
                    GMConfirmDialog.confirm(dialog, "提示", "等级范围应为1-90", "确定", "", "normal", "right")
                    return
                
                # 更新等级（dnf_characters 表，character_id 字段）
                character_id = char.get('character_id', char.get('id', ''))
                query = "UPDATE dnf_characters SET level = ? WHERE character_id = ?"
                self.db.execute_update(query, (new_level, character_id))
                
                self.config.log_operation("调整等级", f"角色:{char_name}, 从{current_level}调整为{new_level}")
                GMConfirmDialog.confirm(dialog, "成功", f"等级已调整为: {new_level}", "确定", "", "success", "right")
                dialog.accept()
                self.load_characters()
                
            except ValueError:
                GMConfirmDialog.confirm(dialog, "提示", "请输入有效的数字", "确定", "", "normal", "right")
            except Exception as e:
                GMConfirmDialog.confirm(dialog, "错误", f"调整失败: {str(e)}", "确定", "", "danger", "right")
        
        dialog.add_button("取消", dialog.reject)
        dialog.add_button("确认", on_ok, "success")
        dialog.exec_()
    
    def modify_gold(self):
        """调整金币"""
        char = self.get_selected_character()
        if not char:
            return
        
        char_name = char.get('name', char.get('char_name', ''))
        current_gold = char.get('gold', 0)
        
        dialog = GMDialog("调整金币", self)
        form_layout = QFormLayout()
        
        char_label = QLabel(f"角色: {char_name}")
        form_layout.addRow(char_label)
        
        current_label = QLabel(f"当前金币: {current_gold}")
        form_layout.addRow(current_label)
        
        gold_input = QLineEdit()
        gold_input.setPlaceholderText("输入新的金币数量")
        gold_input.setText(str(current_gold))
        form_layout.addRow("新金币数量:", gold_input)
        
        dialog.content_layout.addLayout(form_layout)
        
        def on_ok():
            try:
                new_gold = int(gold_input.text())
                if new_gold < 0:
                    GMConfirmDialog.confirm(dialog, "提示", "金币数量不能为负数", "确定", "", "normal", "right")
                    return
                
                # 更新金币（dnf_characters 表，character_id 字段）
                character_id = char.get('character_id', char.get('id', ''))
                query = "UPDATE dnf_characters SET gold = ? WHERE character_id = ?"
                self.db.execute_update(query, (new_gold, character_id))
                
                self.config.log_operation("调整金币", f"角色:{char_name}, 从{current_gold}调整为{new_gold}")
                GMConfirmDialog.confirm(dialog, "成功", f"金币已调整为: {new_gold}", "确定", "", "success", "right")
                dialog.accept()
                self.load_characters()
                
            except ValueError:
                GMConfirmDialog.confirm(dialog, "提示", "请输入有效的数字", "确定", "", "normal", "right")
            except Exception as e:
                GMConfirmDialog.confirm(dialog, "错误", f"调整失败: {str(e)}", "确定", "", "danger", "right")
        
        dialog.add_button("取消", dialog.reject)
        dialog.add_button("确认", on_ok, "success")
        dialog.exec_()
    
    def open_black_dragon(self):
        """开启黑钻（默认30天）"""
        char = self.get_selected_character()
        if not char:
            return
        
        char_name = char.get('name', char.get('char_name', ''))
        account_id = char.get('account_id', '')
        
        if not account_id:
            GMConfirmDialog.confirm(self, "错误", "无法获取账号ID", "确定", "", "danger", "right")
            return
        
        # 查询当前黑钻到期时间
        try:
            query = "SELECT entry_value FROM dnf_account_metadata WHERE account_id = ? AND entry_key = 'premium_expire_1000'"
            result = self.db.execute_query(query, (account_id,))
            current_expire = int(result[0]['entry_value']) if result else 0
        except Exception:
            current_expire = 0
        
        import time
        from datetime import datetime, timedelta
        
        now = int(time.time())
        days = 30
        new_expire = now + days * 24 * 3600
        
        # 如果当前已到期，从现在开始算；如果未到期，在现有基础上延长
        if current_expire > now:
            new_expire = current_expire + days * 24 * 3600
        
        current_expire_str = datetime.fromtimestamp(current_expire).strftime('%Y-%m-%d %H:%M:%S') if current_expire > 0 else "未开通"
        new_expire_str = datetime.fromtimestamp(new_expire).strftime('%Y-%m-%d %H:%M:%S')
        
        dialog = GMDialog("开启黑钻", self)
        form_layout = QFormLayout()
        
        char_label = QLabel(f"角色: {char_name}")
        form_layout.addRow(char_label)
        
        account_label = QLabel(f"账号ID: {account_id}")
        form_layout.addRow(account_label)
        
        current_label = QLabel(f"当前黑钻到期: {current_expire_str}")
        form_layout.addRow(current_label)
        
        days_label = QLabel(f"充值天数: {days}天")
        form_layout.addRow(days_label)
        
        new_label = QLabel(f"新到期时间: {new_expire_str}")
        form_layout.addRow(new_label)
        
        tip_label = QLabel("提示：黑钻权益将在角色下次登录时生效")
        tip_label.setStyleSheet("color: #888; font-size: 11px;")
        form_layout.addRow(tip_label)
        
        dialog.content_layout.addLayout(form_layout)
        
        def on_ok():
            try:
                # 更新黑钻到期时间（premium_expire_1000字段）
                query = """
                    INSERT INTO dnf_account_metadata (account_id, entry_key, entry_value)
                    VALUES (?, ?, ?)
                    ON DUPLICATE KEY UPDATE entry_value = ?
                """
                self.db.execute_update(query, (account_id, 'premium_expire_1000', str(new_expire), str(new_expire)))
                
                self.config.log_operation("开启黑钻", f"角色:{char_name}, 账号:{account_id}, 到期时间:{new_expire_str}")
                GMConfirmDialog.confirm(dialog, "成功", f"黑钻已开启！\n到期时间: {new_expire_str}\n\n请重新登录游戏查看黑钻效果。", "确定", "", "success", "right")
                dialog.accept()
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                GMConfirmDialog.confirm(dialog, "错误", f"开启失败: {str(e)}\n\n详细信息:\n{error_detail}", "确定", "", "danger", "right")
        
        dialog.add_button("取消", dialog.reject)
        dialog.add_button("确认开启", on_ok, "success")
        dialog.exec_()
    
    def delete_character(self):
        """删除角色"""
        char = self.get_selected_character()
        if not char:
            return
        
        char_name = char.get('char_name', char.get('name', ''))
        
        reply = GMConfirmDialog.confirm(self, "确认删除", 
                                    f"确定要删除角色 {char_name} 吗？\n此操作不可恢复！",
                                    "确定", "取消", "danger", "left")
        if not reply:
            return
        
        try:
            # 软删除角色（设置 delete_flag = 1）
            character_id = char.get('character_id', char.get('id', ''))
            query = "UPDATE dnf_characters SET delete_flag = 1 WHERE character_id = ?"
            self.db.execute_update(query, (character_id,))
            
            # 自动清理该角色的相关数据
            self._cleanup_character_data(character_id)
            
            self.config.log_operation("删除角色", f"角色:{char_name}, ID:{character_id}")
            GMConfirmDialog.confirm(self, "成功", "角色已删除，相关数据已自动清理", "确定", "", "success", "right")
            self.load_characters()
            
        except Exception as e:
            GMConfirmDialog.confirm(self, "错误", f"删除失败: {str(e)}", "确定", "", "danger", "right")
    
    def cleanup_deleted_characters(self):
        """手动清理所有已删除角色的残留数据"""
        try:
            # 查询所有已删除的角色
            query = "SELECT character_id, name FROM dnf_characters WHERE delete_flag = 1"
            deleted_chars = self.db.execute_query(query)
            
            if not deleted_chars:
                self.status_label.setText("没有已删除的角色需要清理")
                self.status_label.setObjectName("statusLabelSuccess")
                return
            
            # 确认清理
            char_names = [c.get('name', '') for c in deleted_chars]
            reply = GMConfirmDialog.confirm(self, "确认清理", 
                                        f"将清理以下已删除角色的所有残留数据：\n{', '.join(char_names)}\n此操作不可恢复！",
                                        "确定清理", "取消", "danger", "left")
            if not reply:
                return
            
            # 逐个清理关联数据
            total_cleaned = 0
            for char in deleted_chars:
                char_id = char.get('character_id')
                char_name = char.get('name', '')
                cleaned = self._cleanup_character_data(char_id)
                total_cleaned += cleaned
                self.status_label.setText(f"已清理角色 {char_name} 的 {cleaned} 条数据")
            
            # 硬删除 dnf_characters 表中的记录
            for char in deleted_chars:
                char_id = char.get('character_id')
                delete_query = "DELETE FROM dnf_characters WHERE character_id = ?"
                self.db.execute_update(delete_query, (char_id,))
            
            self.config.log_operation("清理已删除角色数据", f"共硬删除 {len(deleted_chars)} 个角色，清理 {total_cleaned} 条关联数据")
            GMConfirmDialog.confirm(self, "成功", f"已硬删除 {len(deleted_chars)} 个角色，清理 {total_cleaned} 条关联数据", "确定", "", "success", "right")
            self.load_characters()
            
        except Exception as e:
            GMConfirmDialog.confirm(self, "错误", f"清理失败: {str(e)}", "确定", "", "danger", "right")
    
    def _cleanup_character_data(self, character_id):
        """清理指定角色的所有相关数据，返回清理的记录数"""
        if not character_id:
            return 0
        
        # 需要清理的表列表（表名, 字段名）
        tables_to_clean = [
            ('dnf_inventories', 'character_id'),
            ('dnf_inventory_items', 'character_id'),
            ('dnf_inventory_item_extra', 'character_id'),
            ('dnf_character_stats', 'character_id'),
            ('dnf_character_locations', 'character_id'),
            ('dnf_character_rosters', 'character_id'),
            ('dnf_character_roster_equipment', 'character_id'),
            ('dnf_character_roster_lists', 'character_id'),
            ('dnf_dungeon_permissions', 'character_id'),
            ('dnf_hell_party_permissions', 'character_id'),
            ('dnf_equipments', 'character_id'),
            ('dnf_equipment_entries', 'character_id'),
            ('dnf_equipment_entry_extra', 'character_id'),
            ('dnf_skill_states', 'character_id'),
            ('dnf_skill_layouts', 'character_id'),
            ('dnf_skill_cooldowns', 'character_id'),
            ('dnf_skill_commands', 'character_id'),
            ('dnf_skill_tree_points', 'character_id'),
            ('dnf_skill_tree_states', 'character_id'),
            ('dnf_skills', 'character_id'),
            ('dnf_quest_states', 'character_id'),
            ('dnf_quest_state_extra', 'character_id'),
            ('dnf_quests', 'character_id'),
            ('dnf_mailboxes', 'character_id'),
            ('dnf_mail_metadata', 'character_id'),
            ('dnf_mail_attachments', 'character_id'),
            ('dnf_mail_attachment_extra', 'character_id'),
            ('dnf_pets', 'character_id'),
            ('dnf_pet_entries', 'character_id'),
            ('dnf_pet_entry_extra', 'character_id'),
            ('dnf_pet_artifacts', 'character_id'),
            ('dnf_pet_artifact_extra', 'character_id'),
            ('dnf_pet_clear_tokens', 'character_id'),
        ]
        
        total_cleaned = 0
        
        for table_name, field_name in tables_to_clean:
            try:
                # 先查询数量
                count_query = f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {field_name} = ?"
                result = self.db.execute_query(count_query, (character_id,))
                if result and len(result) > 0:
                    cnt = result[0].get('cnt', 0)
                    if cnt > 0:
                        # 执行删除
                        delete_query = f"DELETE FROM {table_name} WHERE {field_name} = ?"
                        self.db.execute_update(delete_query, (character_id,))
                        total_cleaned += cnt
            except Exception:
                # 表不存在或其他错误，跳过
                pass
        
        # 清理邮件（发件人和收件人）
        try:
            # 发件人
            count_query = "SELECT COUNT(*) as cnt FROM dnf_mails WHERE sender_character_id = ?"
            result = self.db.execute_query(count_query, (character_id,))
            if result and len(result) > 0:
                cnt = result[0].get('cnt', 0)
                if cnt > 0:
                    delete_query = "DELETE FROM dnf_mails WHERE sender_character_id = ?"
                    self.db.execute_update(delete_query, (character_id,))
                    total_cleaned += cnt
            
            # 收件人
            count_query = "SELECT COUNT(*) as cnt FROM dnf_mails WHERE recipient_character_id = ?"
            result = self.db.execute_query(count_query, (character_id,))
            if result and len(result) > 0:
                cnt = result[0].get('cnt', 0)
                if cnt > 0:
                    delete_query = "DELETE FROM dnf_mails WHERE recipient_character_id = ?"
                    self.db.execute_update(delete_query, (character_id,))
                    total_cleaned += cnt
        except Exception:
            pass
        
        return total_cleaned

# ============== 物品管理模块 ==============
class ItemManagerWidget(QWidget):
    """物品管理模块（通过邮件附件发放物品）"""
    
    def __init__(self, db, config, preloaded_items=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.characters = []
        self.items = preloaded_items if preloaded_items else []
        self.selected_item = None
        self.selected_is_boostable_equipment = False
        self.current_amplify_value = 10  # 联动的异次元数值，默认等于强化等级
        self.init_ui()
        if preloaded_items:
            # 使用预加载的物品数据
            self.status_label.setText(f"已加载 {len(self.items)} 个物品（PVF预加载）")
        else:
            # 没有预加载数据，自己加载
            self.load_items()
        QTimer.singleShot(100, self.load_characters)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("道具发放")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 提示信息（放在标题下方）
        self.tip_label = QLabel("提示：物品通过游戏内邮件发放，角色上线后即可在邮箱中领取。")
        self.tip_label.setObjectName("tipLabel")
        self.tip_label.setWordWrap(True)
        self.tip_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.tip_label)
        
        # 发放表单
        form_widget = QWidget()
        form_widget.setObjectName("formCard")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)
        
        # 选择角色
        char_label = QLabel("选择角色")
        char_label.setObjectName("formLabel")
        form_layout.addWidget(char_label)
        
        self.char_combo = QComboBox()
        self.char_combo.setObjectName("formInput")
        self.char_combo.setMinimumHeight(36)
        self.char_combo.setPlaceholderText("加载角色列表中...")
        form_layout.addWidget(self.char_combo)
        
        # 物品搜索
        item_search_label = QLabel("搜索物品")
        item_search_label.setObjectName("formLabel")
        form_layout.addWidget(item_search_label)
        
        self.item_search_input = QLineEdit()
        self.item_search_input.setObjectName("formInput")
        self.item_search_input.setPlaceholderText("输入物品ID或名称关键词，例如 490701780 或 印章")
        self.item_search_input.setMinimumHeight(36)
        self.item_search_input.textChanged.connect(self.search_items)
        form_layout.addWidget(self.item_search_input)
        
        # 搜索结果列表
        self.item_list_widget = QListWidget()
        self.item_list_widget.setObjectName("formInput")
        self.item_list_widget.setMaximumHeight(150)
        self.item_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #2d6cdf;
                color: white;
            }
        """)
        self.item_list_widget.itemClicked.connect(self.on_item_selected)
        # 设置选择模式为NoSelection，避免选择状态影响后续点击
        self.item_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        form_layout.addWidget(self.item_list_widget)
        
        # 选中物品信息（移回搜索结果列表下方）
        self.selected_item_label = QLabel("未选择物品")
        self.selected_item_label.setObjectName("tipLabel")
        self.selected_item_label.setWordWrap(True)
        self.selected_item_label.setStyleSheet("color: #aaa; font-size: 12px; padding: 8px; background-color: #222; border-radius: 6px;")
        form_layout.addWidget(self.selected_item_label)
        
        # 隐藏原来的物品ID和名称输入框（保留用于发放逻辑）
        self.item_id_input = QLineEdit()
        self.item_id_input.setVisible(False)
        self.item_name_input = QLineEdit()
        self.item_name_input.setVisible(False)
        
        # 强化增幅开关（默认关闭）- 单独一行
        self.boost_enabled_checkbox = QCheckBox("强化")
        self.boost_enabled_checkbox.setObjectName("formLabel")
        self.boost_enabled_checkbox.setChecked(False)
        self.boost_enabled_checkbox.setCursor(Qt.PointingHandCursor)
        self.boost_enabled_checkbox.setStyleSheet("background-color: transparent;")
        self.boost_enabled_checkbox.stateChanged.connect(self.toggle_boost_settings)
        form_layout.addWidget(self.boost_enabled_checkbox)
        
        # 物品调整区域：四个组件等宽等高等距分布，标签在上方左对齐，底部对齐
        item_adjust_layout = QHBoxLayout()
        item_adjust_layout.setSpacing(12)
        item_adjust_layout.setAlignment(Qt.AlignBottom)
        
        # 统一的组件宽度和高度
        component_width = 140
        component_height = 36
        
        # 1. 物品数量输入框（标签在上方左对齐）
        quantity_widget = QWidget()
        quantity_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        quantity_widget.setAutoFillBackground(False)
        quantity_widget.setStyleSheet("background-color: transparent;")
        quantity_layout = QVBoxLayout(quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(4)
        quantity_label = QLabel("数量")
        quantity_label.setObjectName("formLabel")
        quantity_label.setAlignment(Qt.AlignLeft)
        quantity_label.setStyleSheet("background-color: transparent;")
        self.quantity_input = QLineEdit()
        self.quantity_input.setObjectName("formInput")
        self.quantity_input.setPlaceholderText("数量")
        self.quantity_input.setText("1")
        self.quantity_input.setFixedSize(component_width, component_height)
        quantity_layout.addWidget(quantity_label)
        quantity_layout.addWidget(self.quantity_input)
        item_adjust_layout.addWidget(quantity_widget)
        
        # 2. 异次元能力设置菜单（标签在上方左对齐，点击强化开关后显示）
        self.amplify_type_widget = QWidget()
        self.amplify_type_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.amplify_type_widget.setAutoFillBackground(False)
        self.amplify_type_widget.setStyleSheet("background-color: transparent;")
        amplify_type_layout = QVBoxLayout(self.amplify_type_widget)
        amplify_type_layout.setContentsMargins(0, 0, 0, 0)
        amplify_type_layout.setSpacing(4)
        amplify_type_label = QLabel("异次元")
        amplify_type_label.setObjectName("formLabel")
        amplify_type_label.setAlignment(Qt.AlignLeft)
        amplify_type_label.setStyleSheet("background-color: transparent;")
        self.amplify_type_combo = QComboBox()
        self.amplify_type_combo.setObjectName("formInput")
        self.amplify_type_combo.setFixedSize(component_width, component_height)
        self.amplify_type_combo.addItem("无", 0)
        self.amplify_type_combo.addItem("力量", 3)
        self.amplify_type_combo.addItem("智力", 4)
        self.amplify_type_combo.addItem("体力", 1)
        self.amplify_type_combo.addItem("精神", 2)
        self.amplify_type_combo.setCurrentIndex(0)  # 默认无
        # 联动：选择异次元类型时，异次元数值自动等于强化等级
        self.amplify_type_combo.currentIndexChanged.connect(self.sync_amplify_with_reinforce)
        amplify_type_layout.addWidget(amplify_type_label)
        amplify_type_layout.addWidget(self.amplify_type_combo)
        self.amplify_type_widget.setVisible(False)  # 默认隐藏
        item_adjust_layout.addWidget(self.amplify_type_widget)
        
        # 3. 异次元数值输入框（标签在上方左对齐，点击强化开关后显示）
        self.amplify_value_widget = QWidget()
        self.amplify_value_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.amplify_value_widget.setAutoFillBackground(False)
        self.amplify_value_widget.setStyleSheet("background-color: transparent;")
        amplify_value_layout = QVBoxLayout(self.amplify_value_widget)
        amplify_value_layout.setContentsMargins(0, 0, 0, 0)
        amplify_value_layout.setSpacing(4)
        amplify_value_label = QLabel("数值")
        amplify_value_label.setObjectName("formLabel")
        amplify_value_label.setAlignment(Qt.AlignLeft)
        amplify_value_label.setStyleSheet("background-color: transparent;")
        self.reinforce_input = QLineEdit()
        self.reinforce_input.setObjectName("formInput")
        self.reinforce_input.setPlaceholderText("0")
        self.reinforce_input.setText("0")
        self.reinforce_input.setFixedSize(component_width, component_height)
        # 联动：强化等级修改时，异次元数值自动同步
        self.reinforce_input.textChanged.connect(self.sync_amplify_with_reinforce)
        amplify_value_layout.addWidget(amplify_value_label)
        amplify_value_layout.addWidget(self.reinforce_input)
        self.amplify_value_widget.setVisible(False)  # 默认隐藏
        item_adjust_layout.addWidget(self.amplify_value_widget)
        
        # 4. 发送按钮（放在QWidget中确保底对齐，固定宽度）
        give_btn_widget = QWidget()
        give_btn_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        give_btn_widget.setAutoFillBackground(False)
        give_btn_widget.setStyleSheet("background-color: transparent;")
        give_btn_layout = QVBoxLayout(give_btn_widget)
        give_btn_layout.setContentsMargins(0, 0, 0, 0)
        give_btn_layout.setSpacing(4)
        # 添加一个空标签占位，确保和其他组件的标签高度一致
        give_btn_placeholder = QLabel("")
        give_btn_placeholder.setObjectName("formLabel")
        give_btn_placeholder.setStyleSheet("background-color: transparent;")
        give_btn_layout.addWidget(give_btn_placeholder)
        self.give_btn = QPushButton("发送")
        self.give_btn.setObjectName("primaryBtn")
        self.give_btn.setFixedSize(component_width, component_height)
        self.give_btn.setCursor(Qt.PointingHandCursor)
        self.give_btn.setStyleSheet("""
            QPushButton#primaryBtn {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #3a3a3a;
                border-color: #5a5a5a;
            }
            QPushButton#primaryBtn:pressed {
                background-color: #4a4a4a;
            }
        """)
        self.give_btn.clicked.connect(self.give_item)
        give_btn_layout.addWidget(self.give_btn)
        item_adjust_layout.addWidget(give_btn_widget)
        
        # 5. 调整金币按钮（放在QWidget中确保底对齐，固定宽度）
        adjust_gold_btn_widget = QWidget()
        adjust_gold_btn_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        adjust_gold_btn_widget.setAutoFillBackground(False)
        adjust_gold_btn_widget.setStyleSheet("background-color: transparent;")
        adjust_gold_btn_layout = QVBoxLayout(adjust_gold_btn_widget)
        adjust_gold_btn_layout.setContentsMargins(0, 0, 0, 0)
        adjust_gold_btn_layout.setSpacing(4)
        # 添加一个空标签占位，确保和其他组件的标签高度一致
        adjust_gold_btn_placeholder = QLabel("")
        adjust_gold_btn_placeholder.setObjectName("formLabel")
        adjust_gold_btn_placeholder.setStyleSheet("background-color: transparent;")
        adjust_gold_btn_layout.addWidget(adjust_gold_btn_placeholder)
        self.adjust_gold_btn = QPushButton("调整金币")
        self.adjust_gold_btn.setObjectName("primaryBtn")
        self.adjust_gold_btn.setFixedSize(component_width, component_height)
        self.adjust_gold_btn.setCursor(Qt.PointingHandCursor)
        self.adjust_gold_btn.setStyleSheet("""
            QPushButton#primaryBtn {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #3a3a3a;
                border-color: #5a5a5a;
            }
            QPushButton#primaryBtn:pressed {
                background-color: #4a4a4a;
            }
        """)
        self.adjust_gold_btn.clicked.connect(self.show_adjust_gold_dialog)
        adjust_gold_btn_layout.addWidget(self.adjust_gold_btn)
        item_adjust_layout.addWidget(adjust_gold_btn_widget)
        
        # 6. 调整点券按钮（放在QWidget中确保底对齐，固定宽度）
        adjust_cera_btn_widget = QWidget()
        adjust_cera_btn_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        adjust_cera_btn_widget.setAutoFillBackground(False)
        adjust_cera_btn_widget.setStyleSheet("background-color: transparent;")
        adjust_cera_btn_layout = QVBoxLayout(adjust_cera_btn_widget)
        adjust_cera_btn_layout.setContentsMargins(0, 0, 0, 0)
        adjust_cera_btn_layout.setSpacing(4)
        # 添加一个空标签占位，确保和其他组件的标签高度一致
        adjust_cera_btn_placeholder = QLabel("")
        adjust_cera_btn_placeholder.setObjectName("formLabel")
        adjust_cera_btn_placeholder.setStyleSheet("background-color: transparent;")
        adjust_cera_btn_layout.addWidget(adjust_cera_btn_placeholder)
        self.adjust_cera_btn = QPushButton("调整点券")
        self.adjust_cera_btn.setObjectName("primaryBtn")
        self.adjust_cera_btn.setFixedSize(component_width, component_height)
        self.adjust_cera_btn.setCursor(Qt.PointingHandCursor)
        self.adjust_cera_btn.setStyleSheet("""
            QPushButton#primaryBtn {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #3a3a3a;
                border-color: #5a5a5a;
            }
            QPushButton#primaryBtn:pressed {
                background-color: #4a4a4a;
            }
        """)
        self.adjust_cera_btn.clicked.connect(self.show_adjust_cera_dialog)
        adjust_cera_btn_layout.addWidget(self.adjust_cera_btn)
        item_adjust_layout.addWidget(adjust_cera_btn_widget)
        
        form_layout.addLayout(item_adjust_layout)
        
        layout.addWidget(form_widget)
        
        layout.addStretch()
        
        # 状态标签 + 预设按钮（右下角）
        status_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        
        # 预设按钮（调整大小和字号）
        self.preset_btn = QPushButton("预设")
        self.preset_btn.setObjectName("secondaryBtn")
        self.preset_btn.setFixedSize(70, 26)
        self.preset_btn.setCursor(Qt.PointingHandCursor)
        self.preset_btn.setStyleSheet("""
            QPushButton#secondaryBtn {
                background-color: #2a2a2a;
                color: #999999;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 12px;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #3a3a3a;
                border-color: #4a4a4a;
                color: #cccccc;
            }
        """)
        self.preset_btn.clicked.connect(self.show_preset_dialog)
        status_row.addWidget(self.preset_btn)
        layout.addLayout(status_row)
    
    def load_characters(self):
        """加载角色列表到下拉框 - 只显示当前登录账号的角色，默认选择上次操作的角色"""
        try:
            # 获取当前登录账号ID
            account_id = self._get_current_account_id()
            
            # 构建查询条件
            conditions = ["delete_flag = 0"]
            params = []
            
            if account_id:
                conditions.append("account_id = ?")
                params.append(account_id)
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT character_id, account_id, name, job, grow_type, level FROM dnf_characters WHERE {where_clause} ORDER BY level DESC"
            characters = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)
            
            self.characters = characters
            self.char_combo.clear()
            
            if not characters:
                self.char_combo.addItem("暂无角色", None)
                self.status_label.setText("暂无可用角色")
                return
            
            for char in characters:
                char_id = char.get('character_id', '')
                name = char.get('name', '')
                level = char.get('level', 0)
                display_text = f"{name} (Lv.{level}) - ID: {char_id}"
                self.char_combo.addItem(display_text, char_id)
            
            # 默认选择上次操作的角色，如果不存在则选择第一个
            last_character_id = self.config.config.get("last_character_id", "")
            selected_index = 0
            
            if last_character_id:
                for i, char in enumerate(characters):
                    if str(char.get('character_id', '')) == str(last_character_id):
                        selected_index = i
                        break
            
            self.char_combo.setCurrentIndex(selected_index)
            
            # 连接角色选择改变信号（只连接一次）
            try:
                self.char_combo.currentIndexChanged.disconnect(self.on_character_changed)
            except Exception:
                pass
            self.char_combo.currentIndexChanged.connect(self.on_character_changed)
            
            self.status_label.setText(f"已加载 {len(characters)} 个角色，默认选择: {self.char_combo.currentText()}")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.char_combo.addItem("加载失败", None)
            self.status_label.setText(f"角色加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def on_character_changed(self, index):
        """角色选择改变时，记录当前选择的角色ID到配置文件"""
        if index >= 0:
            char_id = self.char_combo.itemData(index)
            if char_id:
                self.config.config["last_character_id"] = str(char_id)
                # 保存到配置文件
                try:
                    self.config.save_config()
                except Exception:
                    pass
    
    def _get_current_account_id(self):
        """获取当前登录账号ID"""
        try:
            # 从launcher配置文件读取last_account
            launcher_config_file = getattr(self.config, 'launcher_config_file', None)
            if not launcher_config_file:
                root_dir = getattr(self.config, 'root_dir', None)
                if root_dir:
                    launcher_config_file = os.path.join(root_dir, "config", "config.lau")
            
            if launcher_config_file and os.path.exists(launcher_config_file):
                with open(launcher_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if "launcher" in config_data:
                    last_account = config_data["launcher"].get("last_account", "")
                else:
                    last_account = config_data.get("last_account", "")
                
                if last_account:
                    # 根据账号名查询账号ID
                    account_query = "SELECT account_id FROM dnf_login_accounts WHERE username = ? LIMIT 1"
                    account_result = self.db.execute_query(account_query, (last_account,))
                    if account_result and len(account_result) > 0:
                        return account_result[0].get('account_id')
        except Exception as e:
            print(f"获取当前账号ID失败: {e}")
        
        return None
    
    def show_preset_dialog(self):
        """显示预设设置对话框"""
        dialog = GMDialog("预设设置", self)
        dialog.setMinimumWidth(360)
        dialog.setMaximumWidth(400)
        # 内容区域用原来下拉的配色（#1a1a1a），下拉框用窗体配色（#2a2a2a）
        dialog.setStyleSheet("""
            QWidget#dialogContent {
                background-color: #1a1a1a;
            }
            QLabel {
                background-color: #1a1a1a;
            }
        """)
        
        layout = dialog.content_layout
        
        # 金币默认方向
        gold_label = QLabel("金币默认方向：")
        gold_label.setStyleSheet("color: #cccccc; font-size: 13px; background-color: transparent;")
        layout.addWidget(gold_label)
        
        gold_combo = QComboBox()
        gold_combo.addItem("增加", "add")
        gold_combo.addItem("减少", "reduce")
        current_gold = self.config.get_preset("gold_direction", "add")
        gold_combo.setCurrentIndex(0 if current_gold == "add" else 1)
        gold_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #2d6cdf;
            }
        """)
        layout.addWidget(gold_combo)
        layout.addSpacing(8)
        
        # 点券默认方向
        cera_label = QLabel("点券默认方向：")
        cera_label.setStyleSheet("color: #cccccc; font-size: 13px; background-color: transparent;")
        layout.addWidget(cera_label)
        
        cera_combo = QComboBox()
        cera_combo.addItem("充值", "add")
        cera_combo.addItem("回收", "reduce")
        current_cera = self.config.get_preset("cera_direction", "add")
        cera_combo.setCurrentIndex(0 if current_cera == "add" else 1)
        cera_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #2d6cdf;
            }
        """)
        layout.addWidget(cera_combo)
        layout.addSpacing(16)
        
        # 按钮（向左微调，左边用固定间距代替stretch）
        btn_layout = dialog.button_layout
        btn_layout.addSpacing(10)  # 继续向左微调
        
        save_btn = QPushButton("保存")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedSize(90, 34)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d6cdf;
                color: #ffffff;
                border: 1px solid #2d6cdf;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a56c4;
            }
        """)
        save_btn.clicked.connect(lambda: self.save_presets(gold_combo.currentData(), cera_combo.currentData(), dialog))
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedSize(90, 34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        
        dialog.exec_()
    
    def save_presets(self, gold_direction, cera_direction, dialog):
        """保存预设"""
        self.config.set_preset("gold_direction", gold_direction)
        self.config.set_preset("cera_direction", cera_direction)
        self.status_label.setText("预设已保存")
        dialog.accept()
    
    def load_items(self):
        """加载物品列表（优先从PVF文件读取，失败则回退到items.json）"""
        try:
            import json
            import os
            import sys
            
            # 优先从PVF加载
            pvf_items = load_items_from_pvf()
            if pvf_items:
                self.items = pvf_items
                self.status_label.setText(f"已加载 {len(self.items)} 个物品（PVF）")
                return
            
            # PVF加载失败，回退到items.json
            print("PVF加载失败，回退到items.json")
            
            # 获取exe所在目录
            if getattr(sys, 'frozen', False):
                # PyInstaller打包后
                exe_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 优先从exe同目录读取，然后是其他路径
            possible_paths = [
                os.path.join(exe_dir, 'items.json'),
                os.path.join(os.getcwd(), 'items.json'),
                'items.json',
            ]
            
            items_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    items_path = path
                    break
            
            if items_path:
                with open(items_path, 'r', encoding='utf-8-sig') as f:
                    self.items = json.load(f)
                self.status_label.setText(f"已加载 {len(self.items)} 个物品（外置）")
            else:
                self.items = []
                self.status_label.setText("物品列表加载失败：PVF和items.json均不可用")
        except Exception as e:
            self.items = []
            self.status_label.setText(f"物品列表加载失败: {str(e)}")
    
    def search_items(self, keyword):
        """搜索物品"""
        self.item_list_widget.clear()
        if not keyword.strip():
            return
        
        keyword = keyword.strip().lower()
        results = []
        
        for item in self.items:
            item_id = str(item.get('id', ''))
            item_name = (item.get('name') or '').lower()
            item_path = (item.get('path') or '').lower()
            item_type = (item.get('stackable_type') or item.get('equipment_type') or '').lower()
            
            # 匹配ID或名称或路径或类型
            if keyword in item_id or keyword in item_name or keyword in item_path or keyword in item_type:
                results.append(item)
                if len(results) >= 50:  # 最多显示50个结果
                    break
        
        for item in results:
            item_id = item.get('id', '')
            item_name = item.get('name') or '未知物品'
            item_path = item.get('path') or ''
            item_category = item.get('category') or ''
            item_kind = item.get('kind') or ''
            # 直接使用加载时已经翻译好的类型
            item_type_translated = item.get('type') or ''
            
            # 显示格式：[类型] 物品名称（隐藏ID，但仍支持ID搜索）
            type_info = f"[{item_type_translated}] " if item_type_translated else ""
            display_text = f"{type_info}{item_name}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item)
            # 设置工具提示显示完整信息（包含ID）
            list_item.setToolTip(f"ID: {item_id}\n名称: {item_name}\n类型: {item_type_translated}\n路径: {item_path}")
            self.item_list_widget.addItem(list_item)
    
    def on_item_selected(self, item):
        """选择物品后的处理"""
        item_data = item.data(Qt.UserRole)
        if item_data:
            self.selected_item = item_data
            item_id = item_data.get('id', '')
            item_name = item_data.get('name') or '未知物品'
            item_path = item_data.get('path') or ''
            item_category = item_data.get('category') or ''
            item_kind = item_data.get('kind') or ''
            item_type = item_data.get('stackable_type') or item_data.get('equipment_type') or ''
            item_type_translated = item_data.get('type') or ''
            item_destination = item_data.get('destination') or ''
            item_stack_limit = item_data.get('stack_limit') or 0
            
            # 填充隐藏的输入框（用于发放逻辑）
            self.item_id_input.setText(str(item_id))
            self.item_name_input.setText(item_name)
            
            # 判断是否是可强化增幅的装备（不包括时装、宠物装备、称号）
            is_boostable_equipment = self._is_boostable_equipment(item_type, item_category, item_path)
            self.selected_is_boostable_equipment = is_boostable_equipment
            
            # 强化增幅设置区域已调整为始终显示，不再需要控制显示/隐藏
            
            # 显示选中物品详细信息
            info_text = f"已选择: {item_name}\n"
            info_text += f"ID: {item_id}\n"
            info_text += f"分类: {item_category} ({item_kind})\n"
            if item_type_translated:
                info_text += f"类型: {item_type_translated}\n"
            if is_boostable_equipment:
                info_text += f"状态: 可强化增幅装备\n"
            if item_destination:
                info_text += f"存放位置: {item_destination}\n"
            if item_stack_limit and item_stack_limit > 0:
                info_text += f"堆叠上限: {item_stack_limit}\n"
            info_text += f"路径: {item_path}"
            
            self.selected_item_label.setText(info_text)
            self.selected_item_label.setStyleSheet("color: #4ade80; font-size: 12px; padding: 8px; background-color: #1a2e1a; border-radius: 6px; border: 1px solid #2d5a2d;")
            
            # 将焦点返回到搜索框，方便继续搜索
            self.item_search_input.setFocus()
            # 选中搜索框中的所有文本，方便直接输入新关键词
            self.item_search_input.selectAll()
    
    def _is_boostable_equipment(self, item_type, item_category, item_path):
        """判断是否是可强化增幅的装备（不包括时装、宠物装备、称号）"""
        if not item_type:
            return False
        
        item_type_lower = item_type.lower()
        item_category_lower = (item_category or '').lower()
        item_path_lower = (item_path or '').lower()
        
        # 可强化增幅的装备类型
        boostable_types = [
            '[weapon]',      # 武器
            '[coat]',        # 上衣
            '[pants]',       # 下装
            '[shoes]',       # 鞋子
            '[shoulder]',    # 头肩
            '[waist]',       # 腰带
            '[ring]',        # 戒指
            '[amulet]',      # 项链
            '[wrist]',       # 手镯
            '[support]',     # 辅助装备
            '[magic stone]', # 魔法石
            '[earring]',     # 耳环
        ]
        
        # 检查是否是可强化增幅的装备类型
        is_boostable = False
        for boost_type in boostable_types:
            if item_type_lower == boost_type.lower():
                is_boostable = True
                break
        
        if not is_boostable:
            return False
        
        # 排除时装（avatar）
        if 'avatar' in item_type_lower or 'avatar' in item_category_lower or 'avatar' in item_path_lower:
            return False
        
        # 排除称号（title）
        if 'title' in item_type_lower or 'title' in item_category_lower or 'title' in item_path_lower:
            return False
        
        # 排除宠物装备（creature/pet）
        if 'creature' in item_type_lower or 'creature' in item_category_lower or 'creature' in item_path_lower:
            return False
        if 'pet' in item_type_lower or 'pet' in item_category_lower or 'pet' in item_path_lower:
            return False
        
        return True
    
    def construct_raw_entry(self, item_id, quality_seed, durability=0, reinforce=0, amplify_type=0, amplify_value=0):
        """构造邮件附件的raw_entry二进制数据（119字节，参考原版GM工具）"""
        import struct
        import random
        
        # 生成quality_seed随机种子（如果未提供）
        if quality_seed is None:
            quality_seed = random.randint(1, 2**31 - 1)
        
        # 构造119字节的raw_entry
        raw_entry = bytearray(119)
        
        # 0-1字节: 状态标志（邮件中是0900）
        raw_entry[0] = 0x09
        raw_entry[1] = 0x00
        
        # 2-5字节: 物品ID（小端序）
        item_id_bytes = struct.pack('<I', item_id)
        raw_entry[2:6] = item_id_bytes
        
        # 6-9字节: quality_seed随机种子（小端序）
        seed_bytes = struct.pack('<I', quality_seed)
        raw_entry[6:10] = seed_bytes
        
        # 10字节: 强化等级（reinforce/upgrade_level）
        raw_entry[10] = reinforce & 0xFF
        
        # 11字节: 耐久度（默认48）
        raw_entry[11] = durability
        
        # 12-18字节: 0
        
        # 19字节: 增幅类型（amplify_type）
        raw_entry[19] = amplify_type & 0xFF
        
        # 20字节: 增幅数值（amplify_value）
        raw_entry[20] = amplify_value & 0xFF
        
        # 21-118字节: 都是0（已经初始化为0）
        
        return bytes(raw_entry), quality_seed
    
    def get_item_info_from_json(self, item_id):
        """从items.json中获取物品信息（PVF路径、装备类型等）"""
        try:
            import json
            import os
            json_path = os.path.join(os.path.dirname(__file__), 'items.json')
            if not os.path.exists(json_path):
                # 尝试从运行目录查找
                json_path = 'items.json'
            
            with open(json_path, 'r', encoding='utf-8-sig') as f:
                items = json.load(f)
            
            for item in items:
                if item.get('id') == item_id:
                    return item
            return None
        except Exception as e:
            print(f"获取物品信息失败: {e}")
            return None
    
    def generate_mail_id(self):
        """生成唯一的邮件ID（数字自增，与游戏内格式一致）"""
        try:
            result = self.db.execute_query(
                "SELECT MAX(CAST(mail_id AS UNSIGNED)) as max_id FROM dnf_mails WHERE mail_id REGEXP '^[0-9]+$'"
            )
            if result and result[0].get('max_id'):
                return str(int(result[0]['max_id']) + 1)
            return '1'
        except Exception:
            return '1'
    
    def toggle_boost_settings(self):
        """切换强化增幅设置区域的显示/隐藏"""
        is_checked = self.boost_enabled_checkbox.isChecked()
        # 直接显示/隐藏异次元能力设置菜单和异次元数值输入框
        self.amplify_type_widget.setVisible(is_checked)
        self.amplify_value_widget.setVisible(is_checked)
    
    def sync_amplify_with_reinforce(self):
        """联动：异次元数值自动等于强化等级（当选择了异次元类型时）"""
        try:
            amplify_type_idx = self.amplify_type_combo.currentIndex()
            if amplify_type_idx > 0:  # 选择了异次元类型（非"无"）
                reinforce_text = self.reinforce_input.text().strip()
                if reinforce_text:
                    reinforce_val = int(reinforce_text)
                    # 异次元数值自动等于强化等级，存储在内部变量中
                    self.current_amplify_value = reinforce_val
                else:
                    self.current_amplify_value = 0
            else:
                self.current_amplify_value = 0
        except Exception:
            self.current_amplify_value = 0
    
    def give_item(self):
        """发放物品（通过邮件附件）"""
        # 获取选中的角色
        char_index = self.char_combo.currentIndex()
        if char_index < 0:
            GMConfirmDialog.confirm(self, "提示", "请选择角色", "确定", "", "normal", "right")
            return
        
        character_id = self.char_combo.itemData(char_index)
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "请选择有效的角色", "确定", "", "normal", "right")
            return
        
        # 获取角色名称
        char_name = ""
        for char in self.characters:
            if char.get('character_id') == character_id:
                char_name = char.get('name', '')
                break
        
        # 获取物品ID
        item_id_text = self.item_id_input.text().strip()
        if not item_id_text:
            GMConfirmDialog.confirm(self, "提示", "请先搜索并选择物品", "确定", "", "normal", "right")
            return
        
        try:
            item_id = int(item_id_text)
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "物品ID必须是数字", "确定", "", "normal", "right")
            return
        
        # 获取物品名称
        item_name = self.item_name_input.text().strip()
        if not item_name:
            item_name = f"物品_{item_id}"
        
        # 获取数量
        try:
            quantity = int(self.quantity_input.text())
            if quantity < 1:
                GMConfirmDialog.confirm(self, "提示", "数量至少为1", "确定", "", "normal", "right")
                return
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的数量", "确定", "", "normal", "right")
            return
        
        # 发送物品时无需确认，直接执行
        try:
            # 生成邮件ID
            mail_id = self.generate_mail_id()
            
            # 1. 插入邮件主表
            mail_query = """
                INSERT INTO dnf_mails 
                (character_id, mail_id, sender_character_id, sender_name, 
                 recipient_character_id, recipient_name, title, body, gold, 
                 read_flag, claimed_flag, deleted_flag, created_at)
                VALUES (?, ?, '0', '系统', ?, ?, 'GM 道具发放', ?, 0, 0, 0, 0, NOW())
            """
            body = f"系统发放：{item_name}（{item_id}）"
            self.db.execute_update(mail_query, (character_id, mail_id, character_id, char_name, body))
            
            # 2. 插入邮件附件
            # 参考原版GM工具：bind_flag=0，raw_entry为119字节二进制数据
            import random
            quality_seed = random.randint(1, 2**31 - 1)
            
            # 获取物品信息（判断是否是装备，获取PVF路径和装备类型）
            item_info = self.get_item_info_from_json(item_id)
            is_equipment = False
            pvf_path = ""
            equipment_type = ""
            if item_info:
                is_equipment = item_info.get('kind') == 'equipment'
                pvf_path = item_info.get('path', '')
                equipment_type = item_info.get('equipment_type', '') or ''
            
            # 构造raw_entry二进制数据（119字节，包含强化等级和增幅信息）
            # 只有在强化增幅开关打开时才带强化增幅等级
            reinforce = 0
            amplify_type_idx = 0
            amplify_value = 0
            
            boost_enabled = hasattr(self, 'boost_enabled_checkbox') and self.boost_enabled_checkbox.isChecked()
            if boost_enabled:
                try:
                    reinforce_text = self.reinforce_input.text().strip()
                    if reinforce_text:
                        reinforce = int(reinforce_text)
                    
                    # 使用currentData()获取选项值，而不是currentIndex()
                    amplify_type_idx = self.amplify_type_combo.currentData()
                    if amplify_type_idx is None:
                        amplify_type_idx = 0
                    
                    # 增幅数值等于强化等级
                    amplify_value = reinforce
                except Exception:
                    pass
                
                # 如果没有设置强化等级或异次元类型，则视为普通装备
                if reinforce == 0 or amplify_type_idx == 0:
                    reinforce = 0
                    amplify_type_idx = 0
                    amplify_value = 0
            
            raw_entry, quality_seed = self.construct_raw_entry(
                item_id, quality_seed, durability=0, 
                reinforce=reinforce, amplify_type=amplify_type_idx, amplify_value=amplify_value
            )
            
            attachment_query = """
                INSERT INTO dnf_mail_attachments 
                (character_id, mail_id, attachment_index, item_id, item_count, bind_flag, expire_at, raw_entry)
                VALUES (?, ?, 0, ?, ?, 0, NULL, ?)
            """
            self.db.execute_update(attachment_query, (character_id, mail_id, item_id, quantity, raw_entry))
            
            # 2.1 如果是装备，插入邮件附件extra表（调用辅助函数）
            if is_equipment:
                self._create_equipment_extra_data(
                    character_id, mail_id, reinforce, amplify_type_idx, 
                    amplify_value, quality_seed, pvf_path, equipment_type
                )
            
            # 3. 插入邮件元数据（参考原版GM工具，4条记录，包括unlimited和completion_key）
            metadata_query = """
                INSERT INTO dnf_mail_metadata (character_id, mail_id, metadata_key, metadata_value)
                VALUES (?, ?, 'source', 'gm_admin_system_mail'),
                       (?, ?, 'system_mail', 'true'),
                       (?, ?, 'unlimited', 'true'),
                       (?, ?, 'completion_key', '')
            """
            self.db.execute_update(metadata_query, (character_id, mail_id, character_id, mail_id, character_id, mail_id, character_id, mail_id))
            
            # 4. 更新邮箱更新时间
            mailbox_query = """
                INSERT INTO dnf_mailboxes (character_id, updated_at)
                VALUES (?, NOW())
                ON DUPLICATE KEY UPDATE updated_at = NOW()
            """
            self.db.execute_update(mailbox_query, (character_id,))
            
            # 记录操作日志
            log_msg = f"角色:{char_name}(ID:{character_id}), 物品:{item_name}(ID:{item_id}), 数量:{quantity}, 邮件ID:{mail_id}"
            boost_enabled = hasattr(self, 'boost_enabled_checkbox') and self.boost_enabled_checkbox.isChecked()
            if getattr(self, 'selected_is_boostable_equipment', False) and boost_enabled:
                log_msg += f", 强化:+{self.reinforce_input.text()}"
            self.config.log_operation("发放物品", log_msg)
            
            self.status_label.setText(f"发放成功！物品已通过邮件发送给 [{char_name}]")
            self.status_label.setObjectName("statusLabelSuccess")
            
            # 发放成功提示（使用自定义无边框对话框）
            success_msg = f"物品已成功发放！\n\n角色: {char_name}\n物品: {item_name}\n数量: {quantity}\n\n请登录游戏在邮箱中领取。"
            GMConfirmDialog.confirm(
                self,
                title="发放成功",
                message=success_msg,
                confirm_text="确定",
                cancel_text="",
                confirm_style="success",
                confirm_position="right"
            )
            
            # 重置UI，清空选择的物品，方便继续发放其他物品
            self.reset_item_selection()
            
        except Exception as e:
            self.status_label.setText(f"发放失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"发放失败: {str(e)}", "确定", "", "danger", "right")
    
    def _create_equipment_extra_data(self, character_id, mail_id, reinforce, amplify_type_idx, amplify_value, quality_seed, pvf_path, equipment_type):
        """
        创建装备邮件附件的extra数据（27条记录）
        从give_item函数中提取，减少函数长度
        """
        try:
            extra_query = """
                INSERT INTO dnf_mail_attachment_extra 
                (character_id, mail_id, attachment_index, extra_key, extra_value)
                VALUES (?, ?, 0, ?, ?)
            """
            
            # 基础装备字段（15条）
            extra_fields = [
                ('upgrade_level', str(reinforce)),
                ('source', 'gm_admin_system_mail'),
                ('reinforce', str(reinforce)),
                ('quality_seed', str(quality_seed)),
                ('pvf_path', pvf_path),
                ('packed_flag_byte', str(reinforce)),
                ('max_durability', '0'),
                ('mailbox_pvf_path', pvf_path),
                ('mailbox_pvf_kind', 'equipment'),
                ('mailbox_equipment_type', equipment_type),
                ('last_grant_source', 'gm_admin_system_mail'),
                ('item_kind', 'equipment'),
                ('ext_data0', str(reinforce)),
                ('equipment_type', equipment_type),
                ('durability', '0'),
            ]
            
            for key, value in extra_fields:
                self.db.execute_update(extra_query, (character_id, mail_id, key, value))
            
            # 如果选择了异次元类型（非"无"），插入增幅相关数据（12条）
            if amplify_type_idx > 0:
                amplify_fields = [
                    ('amplify_type', str(amplify_type_idx)),
                    ('amplify_value', str(amplify_value)),
                    ('amplification_type', str(amplify_type_idx)),
                    ('amplification_value', str(amplify_value)),
                    ('value_d', str(amplify_value)),
                    ('value_c', str(amplify_type_idx)),
                    ('value_13', str(amplify_type_idx)),
                    ('marker16', str(amplify_value)),
                    ('marker_16', str(amplify_value)),
                    ('byte_13', str(amplify_type_idx)),
                ]
                for key, value in amplify_fields:
                    self.db.execute_update(extra_query, (character_id, mail_id, key, value))
                    
        except Exception as e:
            print(f"插入邮件附件extra表失败: {e}")
    
    def reset_item_selection(self):
        """重置物品选择UI，清空选择的物品"""
        # 清空隐藏的输入框
        self.item_id_input.clear()
        self.item_name_input.clear()
        self.quantity_input.setText("1")
        
        # 清空搜索结果列表
        self.item_list_widget.clear()
        
        # 重置选中物品信息
        self.selected_item = None
        self.selected_is_boostable_equipment = False
        self.selected_item_label.setText("未选择物品")
        self.selected_item_label.setStyleSheet("color: #aaa; font-size: 12px; padding: 8px; background-color: #222; border-radius: 6px;")
        
        # 隐藏强化增幅设置区域
        # 强化增幅设置区域已调整为始终显示，不再需要隐藏
        
        # 重置强化增幅开关（默认关闭）
        if hasattr(self, 'boost_enabled_checkbox'):
            self.boost_enabled_checkbox.setChecked(False)
        
        # 重置强化增幅输入框
        if hasattr(self, 'reinforce_input'):
            self.reinforce_input.setText("10")
        if hasattr(self, 'amplify_type_combo'):
            self.amplify_type_combo.setCurrentIndex(1)
        # 重置联动的异次元数值
        self.current_amplify_value = 10
    
    def show_adjust_gold_dialog(self):
        """显示调整金币对话框"""
        # 获取选中的角色
        char_index = self.char_combo.currentIndex()
        if char_index < 0:
            GMConfirmDialog.confirm(self, "提示", "请选择角色", "确定", "", "normal", "right")
            return
        
        character_id = self.char_combo.itemData(char_index)
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "请选择有效的角色", "确定", "", "normal", "right")
            return
        
        # 获取角色名称
        char_name = ""
        for char in self.characters:
            if char.get('character_id') == character_id:
                char_name = char.get('name', char.get('char_name', ''))
                break
        
        # 显示调整金币对话框（读取预设方向）
        preset_direction = self.config.get_preset("gold_direction", None)
        dialog = GMAdjustDialog(
            adjust_type="gold",
            character_id=character_id,
            character_name=char_name,
            db=self.db,
            parent=self,
            preset_direction=preset_direction
        )
        dialog.exec_()
    
    def show_adjust_cera_dialog(self):
        """显示调整点券对话框"""
        # 获取选中的角色
        char_index = self.char_combo.currentIndex()
        if char_index < 0:
            GMConfirmDialog.confirm(self, "提示", "请选择角色", "确定", "", "normal", "right")
            return
        
        character_id = self.char_combo.itemData(char_index)
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "请选择有效的角色", "确定", "", "normal", "right")
            return
        
        # 获取角色名称和账号ID
        char_name = ""
        account_id = ""
        for char in self.characters:
            if char.get('character_id') == character_id:
                char_name = char.get('name', char.get('char_name', ''))
                account_id = char.get('account_id', '')
                break
        
        if not account_id:
            GMConfirmDialog.confirm(self, "错误", "无法获取账号ID", "确定", "", "danger", "right")
            return
        
        # 显示调整点券对话框（读取预设方向）
        preset_direction = self.config.get_preset("cera_direction", None)
        dialog = GMAdjustDialog(
            adjust_type="cera",
            character_id=character_id,
            character_name=char_name,
            account_id=account_id,
            db=self.db,
            parent=self,
            preset_direction=preset_direction
        )
        dialog.exec_()
    
    def adjust_gold(self):
        """调整角色金币"""
        # 获取选中的角色
        char_index = self.char_combo.currentIndex()
        if char_index < 0:
            GMConfirmDialog.confirm(self, "提示", "请选择角色", "确定", "", "normal", "right")
            return
        
        character_id = self.char_combo.itemData(char_index)
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "请选择有效的角色", "确定", "", "normal", "right")
            return
        
        # 获取角色名称
        char_name = ""
        for char in self.characters:
            if char.get('character_id') == character_id:
                char_name = char.get('name', char.get('char_name', ''))
                break
        
        # 获取输入的金币数量
        gold_text = self.gold_input.text().strip()
        if not gold_text:
            GMConfirmDialog.confirm(self, "提示", "请输入金币数量", "确定", "", "normal", "right")
            return
        
        try:
            new_gold = int(gold_text)
            if new_gold < 0:
                GMConfirmDialog.confirm(self, "提示", "金币数量不能为负数", "确定", "", "normal", "right")
                return
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的数字", "确定", "", "normal", "right")
            return
        
        try:
            # 查询当前金币
            query = "SELECT gold FROM dnf_characters WHERE character_id = ?"
            result = self.db.execute_query(query, (character_id,))
            current_gold = result[0]['gold'] if result else 0
            
            # 更新金币
            query = "UPDATE dnf_characters SET gold = ? WHERE character_id = ?"
            self.db.execute_update(query, (new_gold, character_id))
            
            self.config.log_operation("调整金币", f"角色:{char_name}(ID:{character_id}), 从{current_gold}调整为{new_gold}")
            self.status_label.setText(f"金币已调整！角色: {char_name}, 金币: {new_gold}")
            self.status_label.setObjectName("statusLabelSuccess")
            
            GMConfirmDialog.confirm(
                self,
                title="调整成功",
                message=f"金币已成功调整！\n\n角色: {char_name}\n当前金币: {current_gold}\n新金币: {new_gold}",
                confirm_text="确定",
                cancel_text="",
                confirm_style="success",
                confirm_position="right"
            )
            
            self.gold_input.clear()
            
        except Exception as e:
            self.status_label.setText(f"调整失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"调整失败: {str(e)}", "确定", "", "danger", "right")
    
    def adjust_cera(self):
        """调整账号点券"""
        # 获取选中的角色
        char_index = self.char_combo.currentIndex()
        if char_index < 0:
            GMConfirmDialog.confirm(self, "提示", "请选择角色", "确定", "", "normal", "right")
            return
        
        character_id = self.char_combo.itemData(char_index)
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "请选择有效的角色", "确定", "", "normal", "right")
            return
        
        # 获取角色名称和账号ID
        char_name = ""
        account_id = ""
        for char in self.characters:
            if char.get('character_id') == character_id:
                char_name = char.get('name', char.get('char_name', ''))
                account_id = char.get('account_id', '')
                break
        
        if not account_id:
            GMConfirmDialog.confirm(self, "错误", "无法获取账号ID", "确定", "", "danger", "right")
            return
        
        # 获取输入的点券数量
        cera_text = self.cera_input.text().strip()
        if not cera_text:
            GMConfirmDialog.confirm(self, "提示", "请输入点券数量", "确定", "", "normal", "right")
            return
        
        try:
            new_cera = int(cera_text)
            if new_cera < 0:
                GMConfirmDialog.confirm(self, "提示", "点券数量不能为负数", "确定", "", "normal", "right")
                return
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的数字", "确定", "", "normal", "right")
            return
        
        try:
            # 查询当前点券
            query = "SELECT entry_value FROM dnf_account_metadata WHERE account_id = ? AND entry_key = 'account_cera'"
            result = self.db.execute_query(query, (account_id,))
            current_cera = int(result[0]['entry_value']) if result else 0
            
            # 更新点券
            query = """
                INSERT INTO dnf_account_metadata (account_id, entry_key, entry_value)
                VALUES (?, 'account_cera', ?)
                ON DUPLICATE KEY UPDATE entry_value = ?
            """
            self.db.execute_update(query, (account_id, str(new_cera), str(new_cera)))
            
            self.config.log_operation("调整点券", f"角色:{char_name}(ID:{character_id}), 账号:{account_id}, 从{current_cera}调整为{new_cera}")
            self.status_label.setText(f"点券已调整！角色: {char_name}, 点券: {new_cera}")
            self.status_label.setObjectName("statusLabelSuccess")
            
            GMConfirmDialog.confirm(
                self,
                title="调整成功",
                message=f"点券已成功调整！\n\n角色: {char_name}\n账号: {account_id}\n当前点券: {current_cera}\n新点券: {new_cera}",
                confirm_text="确定",
                cancel_text="",
                confirm_style="success",
                confirm_position="right"
            )
            
            self.cera_input.clear()
            
        except Exception as e:
            self.status_label.setText(f"调整失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"调整失败: {str(e)}", "确定", "", "danger", "right")
    
    def construct_simple_raw_entry(self, item_id, durability=0):
        """构造简单的raw_entry（119字节，只包含基础信息）"""
        import struct
        raw = bytearray(119)  # 119字节全0
        
        # 偏移2-5: 物品ID（4字节小端）
        struct.pack_into('<I', raw, 2, int(item_id))
        
        # 偏移11: 耐久度
        raw[11] = durability
        
        return bytes(raw)
    
    def give_item_to_inventory_with_boost(self):
        """发放带强化增幅的装备到背包（方案A：raw_entry简单构造，强化增幅写入extra表）"""
        # 获取选中的角色
        char_index = self.char_combo.currentIndex()
        if char_index < 0:
            GMConfirmDialog.confirm(self, "提示", "请选择角色", "确定", "", "normal", "right")
            return
        
        character_id = self.char_combo.itemData(char_index)
        if not character_id:
            GMConfirmDialog.confirm(self, "提示", "请选择有效的角色", "确定", "", "normal", "right")
            return
        
        # 获取角色名称
        char_name = ""
        for char in self.characters:
            if char.get('character_id') == character_id:
                char_name = char.get('name', '')
                break
        
        # 获取物品ID
        item_id_text = self.item_id_input.text().strip()
        if not item_id_text:
            GMConfirmDialog.confirm(self, "提示", "请先搜索并选择物品", "确定", "", "normal", "right")
            return
        
        try:
            item_id = int(item_id_text)
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "物品ID必须是数字", "确定", "", "normal", "right")
            return
        
        # 获取物品名称和路径
        item_name = self.item_name_input.text().strip()
        if not item_name:
            item_name = f"物品_{item_id}"
        
        item_path = ""
        item_type = ""
        if self.selected_item:
            item_path = self.selected_item.get('path', '')
            item_type = self.selected_item.get('equipment_type', '')
        
        # 获取强化增幅参数
        try:
            reinforce = int(self.reinforce_input.text())
            if reinforce < 0 or reinforce > 31:
                GMConfirmDialog.confirm(self, "提示", "强化等级范围: 0-31", "确定", "", "normal", "right")
                return
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的强化等级", "确定", "", "normal", "right")
            return
        
        amplify_type = self.amplify_type_combo.currentData()
        if amplify_type is None:
            amplify_type = 0
        
        try:
            amplify_value = int(self.amplify_value_input.text())
            if amplify_value < 0 or amplify_value > 31:
                GMConfirmDialog.confirm(self, "提示", "增幅数值范围: 0-31", "确定", "", "normal", "right")
                return
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的增幅数值", "确定", "", "normal", "right")
            return
        
        # 确认发放（使用自定义无边框对话框）
        # 多行显示，仅角色名加粗，移除调试信息（HTML模式下用<br>换行）
        amplify_type_name = self.amplify_type_combo.currentText()
        message = (f'确定要给角色 [<b>{char_name}</b>] 发放以下装备吗？<br><br>'
                   f'物品: {item_name}<br>'
                   f'ID: {item_id}<br>'
                   f'强化等级: +{reinforce}<br>'
                   f'增幅类型: {amplify_type_name}<br>'
                   f'增幅数值: +{amplify_value}')
        
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认发放",
            message=message,
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="normal",
            confirm_position="right"
        )
        
        if not confirmed:
            return
        
        try:
            import time
            import random
            
            # 生成唯一的entry_key
            timestamp = int(time.time() * 1000)
            random_num = random.randint(1000, 9999)
            entry_key = f"gm_{timestamp}_{random_num}"
            
            # 构造简单的raw_entry
            raw_entry = self.construct_simple_raw_entry(item_id, durability=0)
            
            # 1. 插入背包物品表
            inventory_query = """
                INSERT INTO dnf_inventory_items 
                (character_id, collection_name, entry_key, item_id, item_count, bind_flag, expire_at, raw_entry)
                VALUES (%s, 'inventory', %s, %s, 1, 1, NULL, %s)
            """
            self.db.execute_update(inventory_query, (character_id, entry_key, item_id, raw_entry))
            
            # 2. 插入背包物品extra表（强化增幅信息）
            extra_fields = [
                ('reinforce', str(reinforce)),
                ('upgrade_level', str(reinforce)),
                ('durability', '0'),
                ('max_durability', '0'),
                ('equipment_type', item_type if item_type else '[weapon]'),
                ('item_kind', 'equipment'),
                ('pvf_path', item_path if item_path else ''),
                ('seal_removed_by_first_equip', '1'),
                ('trade_locked_by_first_equip', '1'),
            ]
            
            # 如果有增幅，添加增幅字段
            if amplify_type > 0:
                extra_fields.append(('amplify_type', str(amplify_type)))
                extra_fields.append(('amplify_value', str(amplify_value)))
                extra_fields.append(('amplification_type', str(amplify_type)))
                extra_fields.append(('amplification_value', str(amplify_value)))
            
            for extra_key, extra_value in extra_fields:
                extra_query = """
                    INSERT INTO dnf_inventory_item_extra
                    (character_id, collection_name, entry_key, extra_key, extra_value)
                    VALUES (%s, 'inventory', %s, %s, %s)
                """
                self.db.execute_update(extra_query, (character_id, entry_key, extra_key, extra_value))
            
            # 记录操作日志
            self.config.log_operation("发放带强化增幅装备(方案A)", 
                f"角色:{char_name}(ID:{character_id}), 物品:{item_name}(ID:{item_id}), "
                f"强化:+{reinforce}, 增幅:{amplify_type_name}+{amplify_value}, entry_key:{entry_key}")
            
            self.status_label.setText(f"发放成功！装备已放入 [{char_name}] 的背包")
            self.status_label.setObjectName("statusLabelSuccess")
            
            # 发放成功提示（使用自定义无边框对话框）
            success_msg = (f"装备已成功发放到背包！\n\n"
                           f"角色: {char_name}\n"
                           f"物品: {item_name}\n"
                           f"强化: +{reinforce}\n"
                           f"增幅: {amplify_type_name} +{amplify_value}\n\n"
                           f"请登录游戏查看背包中的装备。\n"
                           f"如果强化增幅不生效，说明需要同时修改raw_entry（方案B）。")
            GMConfirmDialog.confirm(
                self,
                title="发放成功",
                message=success_msg,
                confirm_text="确定",
                cancel_text="",
                confirm_style="success",
                confirm_position="right"
            )
            
        except Exception as e:
            self.status_label.setText(f"发放失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"发放失败: {str(e)}", "确定", "", "danger", "right")

# ============== 背包管理模块 ==============
class InventoryManagerWidget(QWidget):
    """背包管理模块 - 查看和管理角色背包物品"""
    
    def __init__(self, db, config, preloaded_items=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.characters = []
        self.current_character_id = None
        self.items_data = {}  # item_id -> item info
        self._is_first_show = True
        self.init_ui()
        QTimer.singleShot(100, self.load_characters)
        
        if preloaded_items:
            # 使用预加载的物品数据，转换为字典格式
            for item in preloaded_items:
                item_id = str(item.get('id', ''))
                if item_id:
                    self.items_data[item_id] = item
            self.status_label.setText(f"已加载 {len(self.items_data)} 个物品信息（PVF预加载）")
        else:
            # 没有预加载数据，尝试从config目录的缓存文件读取
            self.load_items_from_cache()
    
    def load_items_from_cache(self):
        """从全局缓存加载物品数据（纯内存，不依赖JSON文件）"""
        try:
            items_dict = get_items_data_dict()
            if items_dict:
                self.items_data = items_dict
                self.status_label.setText(f"已加载 {len(self.items_data)} 个物品信息（内存缓存）")
                # 如果已经选择了角色，自动刷新背包列表
                if self.current_character_id:
                    QTimer.singleShot(100, self.load_inventory)
            else:
                self.status_label.setText("等待PVF物品数据加载...")
        except Exception as e:
            print(f"加载物品缓存失败: {e}")
            self.status_label.setText("等待PVF物品数据加载...")
    
    def showEvent(self, event):
        """widget显示时自动刷新列表"""
        super().showEvent(event)
        # 显示时尝试从全局缓存加载物品数据（如果还没有的话）
        if not self.items_data:
            self.load_items_from_cache()
        if not self._is_first_show:
            # 非首次显示时，只刷新角色列表，不自动刷新背包物品（PVF加载模式下取消自动刷新）
            QTimer.singleShot(50, self.load_characters)
        self._is_first_show = False
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("背包管理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 角色选择
        char_layout = QHBoxLayout()
        char_label = QLabel("选择角色:")
        char_label.setFixedWidth(80)
        self.char_combo = QComboBox()
        self.char_combo.setMinimumWidth(200)
        self.char_combo.currentIndexChanged.connect(self.on_character_changed)
        char_layout.addWidget(char_label)
        char_layout.addWidget(self.char_combo)
        char_layout.addStretch()
        layout.addLayout(char_layout)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_inventory)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_items)
        toolbar_layout.addWidget(self.select_all_btn)
        
        self.invert_select_btn = QPushButton("反选")
        self.invert_select_btn.clicked.connect(self.invert_select_items)
        toolbar_layout.addWidget(self.invert_select_btn)
        
        self.delete_btn = QPushButton("删除选中物品")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self.delete_selected_items)
        toolbar_layout.addWidget(self.delete_btn)
        
        toolbar_layout.addStretch()
        
        # 搜索
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索物品ID或名称...")
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(self.filter_items)
        toolbar_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.filter_items)
        toolbar_layout.addWidget(search_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 物品表格
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(8)
        self.inventory_table.setHorizontalHeaderLabels(["选择", "槽位", "物品ID", "物品名称", "类型", "数量", "来源", "操作"])
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.inventory_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # ID列减小宽度，名称列增加宽度
        self.inventory_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.inventory_table.setColumnWidth(2, 90)
        self.inventory_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.inventory_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.inventory_table.setSortingEnabled(True)
        # 隐藏槽位列
        self.inventory_table.setColumnHidden(1, True)
        layout.addWidget(self.inventory_table)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        
        self.all_items = []
    
    def load_items_json(self):
        """加载items.json物品数据"""
        try:
            # 获取exe所在目录（打包后正确路径）
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 如果当前目录是module，items.json在同级目录；否则在module子目录
            if os.path.basename(exe_dir) == "module":
                possible_paths = [
                    os.path.join(exe_dir, "items.json"),
                ]
            else:
                possible_paths = [
                    os.path.join(exe_dir, "module", "items.json"),
                    os.path.join(os.path.dirname(exe_dir), "module", "items.json"),
                    os.path.join(os.getcwd(), "items.json"),
                    "items.json",
                ]
            
            items_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    items_file = path
                    break
            
            if not items_file and hasattr(sys, '_MEIPASS'):
                items_file = os.path.join(sys._MEIPASS, "items.json")
            
            if items_file and os.path.exists(items_file):
                with open(items_file, 'r', encoding='utf-8-sig') as f:
                    items_list = json.load(f)
                
                for item in items_list:
                    item_id = item.get('id')
                    if item_id:
                        self.items_data[item_id] = item
            else:
                self.status_label.setText("未找到items.json，物品名称将显示为ID")
                
        except Exception as e:
            self.status_label.setText(f"加载物品数据失败: {str(e)}")
    
    def load_characters(self):
        """加载角色列表 - 只显示当前登录账号的角色"""
        try:
            # 获取当前登录账号ID
            account_id = self._get_current_account_id()
            
            # 构建查询条件
            conditions = ["1=1"]
            params = []
            
            if account_id:
                conditions.append("account_id = ?")
                params.append(account_id)
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT character_id, name, job, level FROM dnf_characters WHERE {where_clause} ORDER BY character_id"
            results = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)
            self.characters = results if results else []
            
            self.char_combo.clear()
            for char in self.characters:
                char_name = char.get('name', f"角色{char.get('character_id')}")
                char_level = char.get('level', 0)
                self.char_combo.addItem(f"{char_name} (Lv.{char_level})", char.get('character_id'))
            
            if self.characters:
                self.current_character_id = self.characters[0].get('character_id')
                self.load_inventory()
            
        except Exception as e:
            self.status_label.setText(f"加载角色失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def _get_current_account_id(self):
        """获取当前登录账号ID"""
        try:
            launcher_config_file = getattr(self.config, 'launcher_config_file', None)
            if not launcher_config_file:
                root_dir = getattr(self.config, 'root_dir', None)
                if root_dir:
                    launcher_config_file = os.path.join(root_dir, "config", "config.lau")
            
            if launcher_config_file and os.path.exists(launcher_config_file):
                with open(launcher_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if "launcher" in config_data:
                    last_account = config_data["launcher"].get("last_account", "")
                else:
                    last_account = config_data.get("last_account", "")
                
                if last_account:
                    account_query = "SELECT account_id FROM dnf_login_accounts WHERE username = ? LIMIT 1"
                    account_result = self.db.execute_query(account_query, (last_account,))
                    if account_result and len(account_result) > 0:
                        return account_result[0].get('account_id')
        except Exception as e:
            print(f"获取当前账号ID失败: {e}")
        
        return None
    
    def on_character_changed(self, index):
        """角色选择改变"""
        if index >= 0:
            self.current_character_id = self.char_combo.itemData(index)
            self.load_inventory()
    
    def load_inventory(self):
        """加载背包物品"""
        if not self.current_character_id:
            return
        
        try:
            self.status_label.setText("正在加载背包物品...")
            self.status_label.setObjectName("statusLabel")
            
            # 查询背包物品（slots集合）
            query = """
                SELECT entry_key, item_id, item_count, bind_flag, collection_name
                FROM dnf_inventory_items 
                WHERE character_id = %s AND collection_name = 'slots'
                ORDER BY entry_key
            """
            items = self.db.execute_query(query, (self.current_character_id,))
            self.all_items = items if items else []
            
            # 查询物品名称（从extra表）
            self.item_names = {}
            for item in self.all_items:
                entry_key = item.get('entry_key')
                extra_query = """
                    SELECT extra_key, extra_value 
                    FROM dnf_inventory_item_extra 
                    WHERE character_id = %s AND collection_name = 'slots' AND entry_key = %s
                    AND extra_key IN ('item_name', 'equipment_type', 'item_kind', 'source', 'pvf_path')
                """
                extras = self.db.execute_query(extra_query, (self.current_character_id, entry_key))
                if extras:
                    for ext in extras:
                        key = ext.get('extra_key')
                        value = ext.get('extra_value')
                        if key == 'item_name':
                            self.item_names[entry_key] = value
            
            self.display_items(self.all_items)
            self.status_label.setText(f"共加载 {len(self.all_items)} 个物品")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def display_items(self, items):
        """显示物品列表"""
        self.inventory_table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            entry_key = item.get('entry_key', '')
            item_id = item.get('item_id', 0)
            item_count = item.get('item_count', 0)
            
            # 优先从PVF预加载数据获取中文名称和类型（已经翻译好）
            item_info = self.items_data.get(str(item_id), {})
            item_name = item_info.get('name', '') if item_info else ''
            if not item_name:
                # PVF数据中没有，从数据库extra表获取
                item_name = self.item_names.get(entry_key, '')
            if not item_name:
                item_name = f'ID:{item_id}'
            
            # 从PVF预加载数据获取物品类型（已经翻译好）
            item_type = item_info.get('type', '') if item_info else ''
            if not item_type:
                # 如果没有预加载数据，则手动翻译
                kind = item_info.get('kind', '') if item_info else ''
                equipment_type = item_info.get('equipment_type', '') if item_info else ''
                stackable_type = item_info.get('stackable_type', '') if item_info else ''
                category = item_info.get('category', '') if item_info else ''
                item_type = translate_item_type(kind=kind, equipment_type=equipment_type, stackable_type=stackable_type, category=category)
            
            # 查询来源
            source = ''
            try:
                extra_query = """
                    SELECT extra_key, extra_value 
                    FROM dnf_inventory_item_extra 
                    WHERE character_id = %s AND collection_name = 'slots' AND entry_key = %s
                    AND extra_key = 'source'
                """
                extras = self.db.execute_query(extra_query, (self.current_character_id, entry_key))
                if extras:
                    for ext in extras:
                        if ext.get('extra_key') == 'source':
                            source = ext.get('extra_value', '')
            except Exception:
                pass
            
            # 复选框 - 选择列不显示选中高亮
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background-color: transparent;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            # 设置选择列的Item，固定背景色，避免选中高亮
            select_item = QTableWidgetItem()
            select_item.setBackground(QColor("#1a1a1a"))
            select_item.setFlags(Qt.NoItemFlags)
            self.inventory_table.setItem(row, 0, select_item)
            self.inventory_table.setCellWidget(row, 0, checkbox_widget)
            
            self.inventory_table.setItem(row, 1, QTableWidgetItem(str(entry_key)))
            self.inventory_table.setItem(row, 2, QTableWidgetItem(str(item_id)))
            self.inventory_table.setItem(row, 3, QTableWidgetItem(item_name if item_name else f'ID:{item_id}'))
            self.inventory_table.setItem(row, 4, QTableWidgetItem(item_type if item_type else '未知'))
            self.inventory_table.setItem(row, 5, QTableWidgetItem(str(item_count)))
            self.inventory_table.setItem(row, 6, QTableWidgetItem(translate_source(source) if source else '未知'))
            
            # 删除按钮（链接式）
            delete_btn = QPushButton("删除")
            delete_btn.setProperty("linkButton", True)
            delete_btn.setStyleSheet("")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, ek=entry_key, iid=item_id, iname=item_name: self.delete_item(ek, iid, iname))
            self.inventory_table.setCellWidget(row, 7, delete_btn)
    
    def select_all_items(self):
        """全选物品"""
        for row in range(self.inventory_table.rowCount()):
            checkbox_widget = self.inventory_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def invert_select_items(self):
        """反选物品"""
        for row in range(self.inventory_table.rowCount()):
            checkbox_widget = self.inventory_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(not checkbox.isChecked())
    
    def filter_items(self):
        """搜索过滤物品"""
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            self.display_items(self.all_items)
            return
        
        filtered = []
        for item in self.all_items:
            entry_key = str(item.get('entry_key', ''))
            item_id = str(item.get('item_id', ''))
            item_name = self.item_names.get(entry_key, '').lower()
            if keyword in entry_key or keyword in item_id or keyword in item_name:
                filtered.append(item)
        
        self.display_items(filtered)
        self.status_label.setText(f"搜索结果: {len(filtered)} 个物品")
    
    def delete_item(self, entry_key, item_id=None, item_name=None):
        """删除单个物品"""
        # 获取物品名称（如果没有传入）
        if not item_name:
            item_name = self.item_names.get(entry_key, '')
        if not item_id:
            # 从all_items中查找
            for item in self.all_items:
                if str(item.get('entry_key')) == str(entry_key):
                    item_id = item.get('item_id')
                    break
        
        display_name = item_name if item_name else f'ID:{item_id}'
        message = f"确实要删除 {item_id} {display_name} 吗？该操作不可逆！"
        
        # 使用自定义确认对话框（红色确认按钮在左侧，取消按钮在右侧）
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认删除",
            message=message,
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="danger",
            confirm_position="left"
        )
        
        if not confirmed:
            return
        
        try:
            # 删除物品extra
            extra_query = """
                DELETE FROM dnf_inventory_item_extra 
                WHERE character_id = %s AND collection_name = 'slots' AND entry_key = %s
            """
            self.db.execute_update(extra_query, (self.current_character_id, entry_key))
            
            # 删除物品
            item_query = """
                DELETE FROM dnf_inventory_items 
                WHERE character_id = %s AND collection_name = 'slots' AND entry_key = %s
            """
            self.db.execute_update(item_query, (self.current_character_id, entry_key))
            
            self.config.log_operation("删除背包物品", f"角色ID:{self.current_character_id}, 槽位:{entry_key}")
            self.status_label.setText(f"已删除槽位 {entry_key} 的物品")
            self.status_label.setObjectName("statusLabelSuccess")
            self.load_inventory()
            
        except Exception as e:
            self.status_label.setText(f"删除失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"删除失败: {str(e)}", "确定", "", "danger", "right")
    
    def delete_selected_items(self):
        """批量删除选中物品"""
        selected_items = []
        for row in range(self.inventory_table.rowCount()):
            checkbox_widget = self.inventory_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    entry_key = self.inventory_table.item(row, 1).text()
                    selected_items.append(entry_key)
        
        if not selected_items:
            self.status_label.setText("请先选择要删除的物品")
            self.status_label.setObjectName("statusLabelError")
            return
        
        message = f"确实要删除选中的 {len(selected_items)} 个物品吗？该操作不可逆！"
        
        # 使用自定义确认对话框（红色确认按钮在左侧，取消按钮在右侧）
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认批量删除",
            message=message,
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="danger",
            confirm_position="left"
        )
        
        if not confirmed:
            return
        
        try:
            for entry_key in selected_items:
                # 删除物品extra
                extra_query = """
                    DELETE FROM dnf_inventory_item_extra 
                    WHERE character_id = %s AND collection_name = 'slots' AND entry_key = %s
                """
                self.db.execute_update(extra_query, (self.current_character_id, entry_key))
                
                # 删除物品
                item_query = """
                    DELETE FROM dnf_inventory_items 
                    WHERE character_id = %s AND collection_name = 'slots' AND entry_key = %s
                """
                self.db.execute_update(item_query, (self.current_character_id, entry_key))
            
            self.config.log_operation("批量删除背包物品", f"角色ID:{self.current_character_id}, 数量:{len(selected_items)}")
            self.status_label.setText(f"已删除 {len(selected_items)} 个物品")
            self.status_label.setObjectName("statusLabelSuccess")
            self.load_inventory()
            
        except Exception as e:
            self.status_label.setText(f"删除失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"删除失败: {str(e)}", "确定", "", "danger", "right")

# ============== 邮件系统模块 ==============
class MailSystemWidget(QWidget):
    """邮件系统模块 - 查看、发送和删除邮件"""
    
    def __init__(self, db, config, parent=None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.characters = []
        self.current_character_id = None
        self.all_mails = []
        self.init_ui()
        QTimer.singleShot(100, self.load_characters)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("邮件系统")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 角色选择
        char_layout = QHBoxLayout()
        char_label = QLabel("选择角色:")
        char_label.setFixedWidth(80)
        self.char_combo = QComboBox()
        self.char_combo.setMinimumWidth(200)
        self.char_combo.currentIndexChanged.connect(self.on_character_changed)
        char_layout.addWidget(char_label)
        char_layout.addWidget(self.char_combo)
        char_layout.addStretch()
        layout.addLayout(char_layout)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_mails)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_mails)
        toolbar_layout.addWidget(self.select_all_btn)
        
        self.invert_select_btn = QPushButton("反选")
        self.invert_select_btn.clicked.connect(self.invert_select_mails)
        toolbar_layout.addWidget(self.invert_select_btn)
        
        self.delete_btn = QPushButton("删除选中邮件")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self.delete_selected_mails)
        toolbar_layout.addWidget(self.delete_btn)
        
        toolbar_layout.addStretch()
        
        # 搜索
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索邮件标题或内容...")
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(self.filter_mails)
        toolbar_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.filter_mails)
        toolbar_layout.addWidget(search_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 邮件列表
        self.mail_table = QTableWidget()
        self.mail_table.setColumnCount(7)
        self.mail_table.setHorizontalHeaderLabels(["选择", "邮件ID", "发件人", "标题", "内容", "金币", "状态"])
        self.mail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.mail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        # 发件人列减小宽度，内容列增加宽度
        self.mail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.mail_table.setColumnWidth(2, 80)
        self.mail_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.mail_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.mail_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.mail_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mail_table.setAlternatingRowColors(True)
        self.mail_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mail_table.setSortingEnabled(True)
        layout.addWidget(self.mail_table)
        
        # 发送邮件区域（已隐藏 - 只保留删除邮件功能）
        self.send_mail_container = QWidget()
        send_container_layout = QVBoxLayout(self.send_mail_container)
        send_container_layout.setContentsMargins(0, 0, 0, 0)
        send_container_layout.setSpacing(10)
        
        send_title = QLabel("发送邮件")
        send_title.setObjectName("sectionTitle")
        send_container_layout.addWidget(send_title)
        
        # 收件人
        form_layout = QFormLayout()
        
        self.receiver_input = QLineEdit()
        self.receiver_input.setPlaceholderText("输入角色ID")
        form_layout.addRow("收件人ID:", self.receiver_input)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("输入邮件标题")
        form_layout.addRow("邮件标题:", self.subject_input)
        
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("输入邮件内容")
        self.content_input.setFixedHeight(80)
        form_layout.addRow("邮件内容:", self.content_input)
        
        # 附件
        attachment_layout = QHBoxLayout()
        
        self.item_id_input = QLineEdit()
        self.item_id_input.setPlaceholderText("物品ID")
        self.item_id_input.setFixedWidth(120)
        attachment_layout.addWidget(self.item_id_input)
        
        self.item_quantity_input = QLineEdit()
        self.item_quantity_input.setPlaceholderText("数量")
        self.item_quantity_input.setFixedWidth(80)
        self.item_quantity_input.setText("1")
        attachment_layout.addWidget(self.item_quantity_input)
        
        self.gold_input = QLineEdit()
        self.gold_input.setPlaceholderText("金币")
        self.gold_input.setFixedWidth(100)
        self.gold_input.setText("0")
        attachment_layout.addWidget(self.gold_input)
        
        attachment_layout.addStretch()
        form_layout.addRow("附件:", attachment_layout)
        
        send_container_layout.addLayout(form_layout)
        
        # 发送按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.send_btn = QPushButton("发送邮件")
        self.send_btn.setObjectName("successBtn")
        self.send_btn.setFixedWidth(120)
        self.send_btn.clicked.connect(self.send_mail)
        btn_layout.addWidget(self.send_btn)
        
        send_container_layout.addLayout(btn_layout)
        
        # 隐藏发送邮件区域
        self.send_mail_container.setVisible(False)
        layout.addWidget(self.send_mail_container)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
    
    def load_characters(self):
        """加载角色列表 - 只显示当前登录账号的角色"""
        try:
            # 获取当前登录账号ID
            account_id = self._get_current_account_id()
            
            # 构建查询条件
            conditions = ["1=1"]
            params = []
            
            if account_id:
                conditions.append("account_id = ?")
                params.append(account_id)
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT character_id, name, job, level FROM dnf_characters WHERE {where_clause} ORDER BY character_id"
            results = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)
            self.characters = results if results else []
            
            self.char_combo.clear()
            for char in self.characters:
                char_name = char.get('name', f"角色{char.get('character_id')}")
                char_level = char.get('level', 0)
                self.char_combo.addItem(f"{char_name} (Lv.{char_level})", char.get('character_id'))
            
            if self.characters:
                self.current_character_id = self.characters[0].get('character_id')
                self.load_mails()
            
        except Exception as e:
            self.status_label.setText(f"加载角色失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def _get_current_account_id(self):
        """获取当前登录账号ID"""
        try:
            launcher_config_file = getattr(self.config, 'launcher_config_file', None)
            if not launcher_config_file:
                root_dir = getattr(self.config, 'root_dir', None)
                if root_dir:
                    launcher_config_file = os.path.join(root_dir, "config", "config.lau")
            
            if launcher_config_file and os.path.exists(launcher_config_file):
                with open(launcher_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if "launcher" in config_data:
                    last_account = config_data["launcher"].get("last_account", "")
                else:
                    last_account = config_data.get("last_account", "")
                
                if last_account:
                    account_query = "SELECT account_id FROM dnf_login_accounts WHERE username = ? LIMIT 1"
                    account_result = self.db.execute_query(account_query, (last_account,))
                    if account_result and len(account_result) > 0:
                        return account_result[0].get('account_id')
        except Exception as e:
            print(f"获取当前账号ID失败: {e}")
        
        return None
    
    def on_character_changed(self, index):
        """角色选择改变"""
        if index >= 0:
            self.current_character_id = self.char_combo.itemData(index)
            self.load_mails()
    
    def load_mails(self):
        """加载邮件列表"""
        if not self.current_character_id:
            return
        
        try:
            self.status_label.setText("正在加载邮件...")
            self.status_label.setObjectName("statusLabel")
            
            # 查询邮件
            query = """
                SELECT mail_id, sender_name, title, body, gold, read_flag, claimed_flag, created_at
                FROM dnf_mails 
                WHERE character_id = %s
                ORDER BY created_at DESC
            """
            mails = self.db.execute_query(query, (self.current_character_id,))
            self.all_mails = mails if mails else []
            
            self.display_mails(self.all_mails)
            self.status_label.setText(f"共加载 {len(self.all_mails)} 封邮件")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def display_mails(self, mails):
        """显示邮件列表"""
        self.mail_table.setRowCount(len(mails))
        
        for row, mail in enumerate(mails):
            mail_id = mail.get('mail_id', '')
            sender_name = mail.get('sender_name', '')
            title = mail.get('title', '')
            body = mail.get('body', '')
            gold = mail.get('gold', 0)
            read_flag = mail.get('read_flag', 0)
            claimed_flag = mail.get('claimed_flag', 0)
            
            # 状态
            status = []
            if read_flag:
                status.append("已读")
            else:
                status.append("未读")
            if claimed_flag:
                status.append("已领取")
            status_text = "/".join(status)
            
            # 复选框 - 选择列不显示选中高亮
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background-color: transparent;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            # 设置选择列的Item，固定背景色，避免选中高亮
            select_item = QTableWidgetItem()
            select_item.setBackground(QColor("#1a1a1a"))
            select_item.setFlags(Qt.NoItemFlags)
            self.mail_table.setItem(row, 0, select_item)
            self.mail_table.setCellWidget(row, 0, checkbox_widget)
            
            self.mail_table.setItem(row, 1, QTableWidgetItem(str(mail_id)))
            self.mail_table.setItem(row, 2, QTableWidgetItem(str(sender_name)))
            self.mail_table.setItem(row, 3, QTableWidgetItem(str(title)))
            # 内容截断显示
            body_text = str(body)[:50] + "..." if len(str(body)) > 50 else str(body)
            self.mail_table.setItem(row, 4, QTableWidgetItem(body_text))
            self.mail_table.setItem(row, 5, QTableWidgetItem(str(gold)))
            self.mail_table.setItem(row, 6, QTableWidgetItem(status_text))
    
    def select_all_mails(self):
        """全选邮件"""
        for row in range(self.mail_table.rowCount()):
            checkbox_widget = self.mail_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def invert_select_mails(self):
        """反选邮件"""
        for row in range(self.mail_table.rowCount()):
            checkbox_widget = self.mail_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(not checkbox.isChecked())
    
    def filter_mails(self):
        """搜索过滤邮件"""
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            self.display_mails(self.all_mails)
            return
        
        filtered = []
        for mail in self.all_mails:
            title = str(mail.get('title', '')).lower()
            body = str(mail.get('body', '')).lower()
            sender = str(mail.get('sender_name', '')).lower()
            if keyword in title or keyword in body or keyword in sender:
                filtered.append(mail)
        
        self.display_mails(filtered)
        self.status_label.setText(f"搜索结果: {len(filtered)} 封邮件")
    
    def delete_mail(self, mail_id):
        """删除单封邮件"""
        message = f"确定要删除邮件 {mail_id} 吗？\n此操作不可恢复！"
        
        # 使用自定义确认对话框（普通样式：确认按钮在右侧，蓝色）
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认删除",
            message=message,
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="normal",
            confirm_position="right"
        )
        
        if not confirmed:
            return
        
        try:
            # 删除邮件附件
            attachment_query = """
                DELETE FROM dnf_mail_attachments 
                WHERE character_id = %s AND mail_id = %s
            """
            self.db.execute_update(attachment_query, (self.current_character_id, mail_id))
            
            # 删除邮件附件extra
            attachment_extra_query = """
                DELETE FROM dnf_mail_attachment_extra 
                WHERE character_id = %s AND mail_id = %s
            """
            self.db.execute_update(attachment_extra_query, (self.current_character_id, mail_id))
            
            # 删除邮件元数据
            metadata_query = """
                DELETE FROM dnf_mail_metadata 
                WHERE character_id = %s AND mail_id = %s
            """
            self.db.execute_update(metadata_query, (self.current_character_id, mail_id))
            
            # 删除邮件
            mail_query = """
                DELETE FROM dnf_mails 
                WHERE character_id = %s AND mail_id = %s
            """
            self.db.execute_update(mail_query, (self.current_character_id, mail_id))
            
            self.config.log_operation("删除邮件", f"角色ID:{self.current_character_id}, 邮件ID:{mail_id}")
            self.status_label.setText(f"已删除邮件 {mail_id}")
            self.status_label.setObjectName("statusLabelSuccess")
            self.load_mails()
            
        except Exception as e:
            self.status_label.setText(f"删除失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"删除失败: {str(e)}", "确定", "", "danger", "right")
    
    def delete_selected_mails(self):
        """批量删除选中邮件"""
        selected_mails = []
        for row in range(self.mail_table.rowCount()):
            checkbox_widget = self.mail_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    mail_id = self.mail_table.item(row, 1).text()
                    selected_mails.append(mail_id)
        
        if not selected_mails:
            self.status_label.setText("请先选择要删除的邮件")
            self.status_label.setObjectName("statusLabelError")
            return
        
        message = f"确定要删除选中的 {len(selected_mails)} 封邮件吗？\n此操作不可恢复！"
        
        # 使用自定义确认对话框（普通样式：确认按钮在右侧，蓝色）
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认批量删除",
            message=message,
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="normal",
            confirm_position="right"
        )
        
        if not confirmed:
            return
        
        try:
            for mail_id in selected_mails:
                # 删除邮件附件
                attachment_query = """
                    DELETE FROM dnf_mail_attachments 
                    WHERE character_id = %s AND mail_id = %s
                """
                self.db.execute_update(attachment_query, (self.current_character_id, mail_id))
                
                # 删除邮件
                mail_query = """
                    DELETE FROM dnf_mails 
                    WHERE character_id = %s AND mail_id = %s
                """
                self.db.execute_update(mail_query, (self.current_character_id, mail_id))
            
            self.config.log_operation("批量删除邮件", f"角色ID:{self.current_character_id}, 数量:{len(selected_mails)}")
            self.status_label.setText(f"已删除 {len(selected_mails)} 封邮件")
            self.status_label.setObjectName("statusLabelSuccess")
            self.load_mails()
            
        except Exception as e:
            self.status_label.setText(f"删除失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"删除失败: {str(e)}", "确定", "", "danger", "right")
    
    def send_mail(self):
        """发送邮件"""
        receiver = self.receiver_input.text().strip()
        subject = self.subject_input.text().strip()
        content = self.content_input.toPlainText().strip()
        
        if not receiver:
            GMConfirmDialog.confirm(self, "提示", "请输入收件人角色ID", "确定", "", "normal", "right")
            return
        
        if not subject:
            GMConfirmDialog.confirm(self, "提示", "请输入邮件标题", "确定", "", "normal", "right")
            return
        
        try:
            item_id = self.item_id_input.text().strip()
            item_quantity = int(self.item_quantity_input.text()) if self.item_quantity_input.text() else 0
            gold = int(self.gold_input.text()) if self.gold_input.text() else 0
            
            import time
            import random
            mail_id = f"gm_{int(time.time()*1000)}_{random.randint(1000,9999)}"
            
            # 插入邮件
            mail_query = """
                INSERT INTO dnf_mails 
                (character_id, mail_id, sender_character_id, sender_name, 
                 recipient_character_id, recipient_name, title, body, gold, 
                 read_flag, claimed_flag, deleted_flag, created_at)
                VALUES (%s, %s, '0', '系统', %s, '', %s, %s, %s, 0, 0, 0, NOW())
            """
            self.db.execute_update(mail_query, (receiver, mail_id, receiver, subject, content, gold))
            
            # 如果有物品附件，插入附件
            if item_id and item_quantity > 0:
                attachment_query = """
                    INSERT INTO dnf_mail_attachments 
                    (character_id, mail_id, attachment_index, item_id, item_count, bind_flag, expire_at, raw_entry)
                    VALUES (%s, %s, 0, %s, %s, 1, NULL, NULL)
                """
                self.db.execute_update(attachment_query, (receiver, mail_id, int(item_id), item_quantity))
            
            # 更新邮箱更新时间
            mailbox_query = """
                INSERT INTO dnf_mailboxes (character_id, updated_at)
                VALUES (%s, NOW())
                ON DUPLICATE KEY UPDATE updated_at = NOW()
            """
            self.db.execute_update(mailbox_query, (receiver,))
            
            self.config.log_operation("发送邮件", f"收件人ID:{receiver}, 标题:{subject}, 邮件ID:{mail_id}")
            
            self.status_label.setText("邮件已发送")
            self.status_label.setObjectName("statusLabelSuccess")
            
            GMConfirmDialog.confirm(self, "成功", f"邮件已发送！\n邮件ID: {mail_id}", "确定", "", "success", "right")
            
            # 清空输入
            self.receiver_input.clear()
            self.subject_input.clear()
            self.content_input.clear()
            self.item_id_input.clear()
            self.gold_input.setText("0")
            
            # 刷新邮件列表
            if self.current_character_id:
                self.load_mails()
            
        except ValueError:
            GMConfirmDialog.confirm(self, "提示", "请输入有效的数字", "确定", "", "normal", "right")
        except Exception as e:
            self.status_label.setText(f"发送失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            GMConfirmDialog.confirm(self, "错误", f"发送失败: {str(e)}", "确定", "", "danger", "right")

# ============== 日志记录模块 ==============
class LogViewerWidget(QWidget):
    """日志查看模块"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
        QTimer.singleShot(100, self.load_logs)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("操作日志")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日志...")
        self.search_input.returnPressed.connect(self.load_logs)
        toolbar_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.load_logs)
        toolbar_layout.addWidget(search_btn)
        
        export_btn = QPushButton("导出日志")
        export_btn.clicked.connect(self.export_logs)
        toolbar_layout.addWidget(export_btn)
        
        clear_btn = QPushButton("清空日志")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self.clear_logs)
        toolbar_layout.addWidget(clear_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_logs)
        toolbar_layout.addWidget(refresh_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # 日志表格
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["时间", "操作", "详情"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.log_table.setAlternatingRowColors(True)
        layout.addWidget(self.log_table)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
    
    def load_logs(self):
        """加载日志（只显示各模块内的操作，不显示程序级别的操作）"""
        # 程序级别的操作关键词（需要过滤掉）
        system_operations = [
            "GM工具启动",
            "数据库连接成功",
            "数据库重连成功",
            "重连数据库",
            "数据库连接失败",
            "数据库重连失败",
        ]
        
        try:
            keyword = self.search_input.text().strip()
            
            if not os.path.exists(self.config.log_file):
                self.log_table.setRowCount(0)
                self.status_label.setText("暂无日志记录")
                self.status_label.setObjectName("statusLabel")
                return
            
            with open(self.config.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 过滤掉程序级别的操作
            filtered_lines = []
            for line in lines:
                is_system_op = False
                for sys_op in system_operations:
                    if sys_op in line:
                        is_system_op = True
                        break
                if not is_system_op:
                    filtered_lines.append(line)
            lines = filtered_lines
            
            # 过滤关键词
            if keyword:
                lines = [line for line in lines if keyword.lower() in line.lower()]
            
            # 倒序显示（最新的在前面）
            lines.reverse()
            
            # 只显示最近500条
            lines = lines[:500]
            
            self.log_table.setRowCount(len(lines))
            
            for row, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 解析日志格式：[时间] 操作 - 详情
                if line.startswith('[') and ']' in line:
                    timestamp = line[1:line.index(']')]
                    rest = line[line.index(']')+1:].strip()
                    
                    if ' - ' in rest:
                        operation, details = rest.split(' - ', 1)
                    else:
                        operation = rest
                        details = ""
                    
                    self.log_table.setItem(row, 0, QTableWidgetItem(timestamp))
                    self.log_table.setItem(row, 1, QTableWidgetItem(operation))
                    self.log_table.setItem(row, 2, QTableWidgetItem(details))
                else:
                    self.log_table.setItem(row, 0, QTableWidgetItem(""))
                    self.log_table.setItem(row, 1, QTableWidgetItem(line))
                    self.log_table.setItem(row, 2, QTableWidgetItem(""))
            
            self.status_label.setText(f"共 {len(lines)} 条日志")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def export_logs(self):
        """导出日志"""
        if not os.path.exists(self.config.log_file):
            GMConfirmDialog.confirm(self, "提示", "暂无日志记录", "确定", "", "normal", "right")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出日志", "gm_operations.log", "日志文件 (*.log);;文本文件 (*.txt)")
        if not file_path:
            return
        
        try:
            with open(self.config.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            GMConfirmDialog.confirm(self, "成功", f"日志已导出到: {file_path}", "确定", "", "success", "right")
            self.config.log_operation("导出日志", f"导出到:{file_path}")
            
        except Exception as e:
            GMConfirmDialog.confirm(self, "错误", f"导出失败: {str(e)}", "确定", "", "danger", "right")
    
    def clear_logs(self):
        """清空日志"""
        reply = GMConfirmDialog.confirm(self, "确认清空", 
                                    "确定要清空所有操作日志吗？此操作不可恢复！",
                                    "确定", "取消", "danger", "left")
        if not reply:
            return
        
        try:
            if os.path.exists(self.config.log_file):
                with open(self.config.log_file, 'w', encoding='utf-8') as f:
                    f.write("")
            
            self.load_logs()
            GMConfirmDialog.confirm(self, "成功", "日志已清空", "确定", "", "success", "right")
            
        except Exception as e:
            GMConfirmDialog.confirm(self, "错误", f"清空失败: {str(e)}", "确定", "", "danger", "right")

# ============== 存档管理模块 ==============
class ArchiveManagerWidget(QWidget):
    """存档管理 - 数据库备份、恢复、多版本管理"""
    
    def __init__(self, db, config):
        super().__init__()
        self.db = db
        self.config = config
        self.backup_dir = os.path.join(self.config.root_dir, "backup")
        self.backups = []
        self.init_ui()
        self.load_backups()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("存档管理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 操作按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.backup_btn = QPushButton("创建备份")
        self.backup_btn.setCursor(Qt.PointingHandCursor)
        self.backup_btn.clicked.connect(self.create_backup)
        btn_layout.addWidget(self.backup_btn)
        
        self.restore_btn = QPushButton("恢复选中")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.clicked.connect(self.restore_backup)
        btn_layout.addWidget(self.restore_btn)
        
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self.delete_backup)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 备份列表
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(["选择", "备份时间", "备注", "大小"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.backup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.backup_table)
        
        # 备注输入区域
        note_layout = QHBoxLayout()
        note_label = QLabel("备注：")
        note_label.setObjectName("formLabel")
        note_layout.addWidget(note_label)
        
        self.note_input = QLineEdit()
        self.note_input.setObjectName("formInput")
        self.note_input.setPlaceholderText("选中备份后可修改备注")
        note_layout.addWidget(self.note_input)
        
        self.save_note_btn = QPushButton("保存备注")
        self.save_note_btn.setCursor(Qt.PointingHandCursor)
        self.save_note_btn.clicked.connect(self.save_note)
        note_layout.addWidget(self.save_note_btn)
        
        layout.addLayout(note_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
    
    def get_db_path(self):
        """获取数据库文件路径"""
        server_path = self.config.get_server_path()
        db_mode = self.config.get("db_mode", "mysql")
        
        if db_mode == "mysql":
            # MySQL数据目录
            return os.path.join(server_path, "runtime", "mysql", "data")
        else:
            # SQLite数据库文件
            return os.path.join(server_path, "runtime", "data", "dnf_local.db")
    
    def load_backups(self):
        """加载备份列表"""
        self.backups = []
        self.backup_table.setRowCount(0)
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)
            return
        
        # 读取备份元数据
        meta_file = os.path.join(self.backup_dir, "backups.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    self.backups = json.load(f)
            except Exception:
                self.backups = []
        
        # 按时间倒序
        self.backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 显示到表格
        for i, backup in enumerate(self.backups):
            self.backup_table.insertRow(i)
            
            # 选择复选框
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background-color: transparent;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox()
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            self.backup_table.setCellWidget(i, 0, checkbox_widget)
            
            # 备份时间
            time_item = QTableWidgetItem(backup.get("timestamp", ""))
            self.backup_table.setItem(i, 1, time_item)
            
            # 备注
            note_item = QTableWidgetItem(backup.get("note", ""))
            self.backup_table.setItem(i, 2, note_item)
            
            # 大小
            size_item = QTableWidgetItem(backup.get("size", ""))
            self.backup_table.setItem(i, 3, size_item)
    
    def save_backups_meta(self):
        """保存备份元数据"""
        meta_file = os.path.join(self.backup_dir, "backups.json")
        try:
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(self.backups, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            self.status_label.setText(f"保存备份元数据失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
            return False
    
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
                except Exception:
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
    
    def create_backup(self):
        """创建备份"""
        try:
            self.status_label.setText("正在创建备份...")
            self.status_label.setObjectName("statusLabel")
            
            db_path = self.get_db_path()
            if not os.path.exists(db_path):
                self.status_label.setText(f"数据库路径不存在: {db_path}")
                self.status_label.setObjectName("statusLabelError")
                return
            
            # 生成备份目录名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # 复制数据库文件
            if os.path.isdir(db_path):
                shutil.copytree(db_path, backup_path)
            else:
                shutil.copy2(db_path, backup_path)
            
            # 计算大小
            size = self.get_dir_size(backup_path)
            size_str = self.format_size(size)
            
            # 添加备份记录
            backup_info = {
                "name": backup_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "",
                "size": size_str,
                "path": backup_path
            }
            self.backups.insert(0, backup_info)
            self.save_backups_meta()
            
            # 刷新列表
            self.load_backups()
            
            self.status_label.setText(f"备份创建成功: {backup_name} ({size_str})")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"备份失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def get_selected_backup(self):
        """获取选中的备份"""
        for i in range(self.backup_table.rowCount()):
            checkbox_widget = self.backup_table.cellWidget(i, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    return self.backups[i]
        return None
    
    def restore_backup(self):
        """恢复备份"""
        backup = self.get_selected_backup()
        if not backup:
            self.status_label.setText("请先选择要恢复的备份")
            self.status_label.setObjectName("statusLabelError")
            return
        
        # 确认对话框
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认恢复",
            message=f"确定要恢复备份 [{backup.get('timestamp', '')}] 吗？\n当前数据将被覆盖，该操作不可逆！",
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="danger",
            confirm_position="left"
        )
        
        if not confirmed:
            return
        
        try:
            self.status_label.setText("正在恢复备份...")
            self.status_label.setObjectName("statusLabel")
            
            db_path = self.get_db_path()
            backup_path = backup.get("path", "")
            
            if not os.path.exists(backup_path):
                self.status_label.setText(f"备份文件不存在: {backup_path}")
                self.status_label.setObjectName("statusLabelError")
                return
            
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
            
            self.status_label.setText(f"备份恢复成功: {backup.get('timestamp', '')}")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"恢复失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def delete_backup(self):
        """删除备份"""
        backup = self.get_selected_backup()
        if not backup:
            self.status_label.setText("请先选择要删除的备份")
            self.status_label.setObjectName("statusLabelError")
            return
        
        # 确认对话框
        confirmed = GMConfirmDialog.confirm(
            self,
            title="确认删除",
            message=f"确定要删除备份 [{backup.get('timestamp', '')}] 吗？该操作不可逆！",
            confirm_text="确认",
            cancel_text="取消",
            confirm_style="danger",
            confirm_position="left"
        )
        
        if not confirmed:
            return
        
        try:
            backup_path = backup.get("path", "")
            if os.path.exists(backup_path):
                if os.path.isdir(backup_path):
                    shutil.rmtree(backup_path)
                else:
                    os.remove(backup_path)
            
            # 从列表中移除
            self.backups = [b for b in self.backups if b.get("name") != backup.get("name")]
            self.save_backups_meta()
            
            # 刷新列表
            self.load_backups()
            
            self.status_label.setText(f"备份删除成功: {backup.get('timestamp', '')}")
            self.status_label.setObjectName("statusLabelSuccess")
            
        except Exception as e:
            self.status_label.setText(f"删除失败: {str(e)}")
            self.status_label.setObjectName("statusLabelError")
    
    def save_note(self):
        """保存备注"""
        backup = self.get_selected_backup()
        if not backup:
            self.status_label.setText("请先选择要修改备注的备份")
            self.status_label.setObjectName("statusLabelError")
            return
        
        note = self.note_input.text().strip()
        backup["note"] = note
        self.save_backups_meta()
        self.load_backups()
        
        self.status_label.setText("备注保存成功")
        self.status_label.setObjectName("statusLabelSuccess")

# ============== 工具设置模块（预留功能） ==============
class ToolSettingsWidget(QWidget):
    """工具设置 - 可以设置pvf路径、服务端客户端路径，从lau文件读取并保存"""
    
    def __init__(self, db, config):
        super().__init__()
        self.db = db
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("工具设置")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # 提示文字
        hint = QLabel("修改路径后点击保存按钮生效，配置将保存到config.lau文件。")
        hint.setStyleSheet("""
            color: #888888;
            font-size: 12px;
            font-family: 'Noto Sans SC', 'Microsoft YaHei';
            background-color: transparent;
        """)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        layout.addSpacing(8)
        
        # 服务端路径
        server_label = QLabel("服务端路径：")
        server_label.setObjectName("formLabel")
        layout.addWidget(server_label)
        
        server_layout = QHBoxLayout()
        self.server_input = QLineEdit()
        self.server_input.setText(self.config.get_server_path())
        self.server_input.setFixedWidth(500)
        self.server_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
        """)
        server_layout.addWidget(self.server_input)
        
        server_browse_btn = QPushButton("浏览")
        server_browse_btn.setCursor(Qt.PointingHandCursor)
        server_browse_btn.setFixedWidth(80)
        server_browse_btn.clicked.connect(self.browse_server_path)
        server_layout.addWidget(server_browse_btn)
        server_layout.addStretch()
        layout.addLayout(server_layout)
        
        layout.addSpacing(8)
        
        # 客户端路径
        client_label = QLabel("客户端路径：")
        client_label.setObjectName("formLabel")
        layout.addWidget(client_label)
        
        client_layout = QHBoxLayout()
        self.client_input = QLineEdit()
        self.client_input.setText(self.config.get_client_path())
        self.client_input.setFixedWidth(500)
        self.client_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'Noto Sans SC', 'Microsoft YaHei';
            }
        """)
        client_layout.addWidget(self.client_input)
        
        client_browse_btn = QPushButton("浏览")
        client_browse_btn.setCursor(Qt.PointingHandCursor)
        client_browse_btn.setFixedWidth(80)
        client_browse_btn.clicked.connect(self.browse_client_path)
        client_layout.addWidget(client_browse_btn)
        client_layout.addStretch()
        layout.addLayout(client_layout)
        
        layout.addSpacing(8)
        
        # 检测凭证文件是否存在
        self.credential_file = os.path.join(self.config.gm_dir, ".gm_credential")
        self.has_credential = os.path.exists(self.credential_file)
        
        # PVF路径（只有有凭证文件时才显示，否则隐藏）
        if self.has_credential:
            pvf_label = QLabel("PVF文件路径（可自定义）：")
            pvf_label.setObjectName("formLabel")
            layout.addWidget(pvf_label)
            
            pvf_layout = QHBoxLayout()
            self.pvf_input = QLineEdit()
            # 优先从配置读取PVF路径，否则自动计算
            pvf_path = self.config.get_pvf_path()
            self.pvf_input.setText(pvf_path if pvf_path else "")
            self.pvf_input.setReadOnly(False)
            self.pvf_input.setFixedWidth(500)
            self.pvf_input.setStyleSheet("""
                QLineEdit {
                    background-color: #1a1a1a;
                    color: #ffffff;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-family: 'Noto Sans SC', 'Microsoft YaHei';
                }
            """)
            pvf_layout.addWidget(self.pvf_input)
            
            # 添加浏览按钮
            pvf_browse_btn = QPushButton("浏览")
            pvf_browse_btn.setCursor(Qt.PointingHandCursor)
            pvf_browse_btn.setFixedWidth(80)
            pvf_browse_btn.clicked.connect(self.browse_pvf_path)
            pvf_layout.addWidget(pvf_browse_btn)
            
            pvf_layout.addStretch()
            layout.addLayout(pvf_layout)
        else:
            # 没有凭证文件时，不显示PVF路径框，但保留属性引用避免报错
            self.pvf_input = None
        
        layout.addStretch()
        
        # 保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setFixedWidth(120)
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self.save_settings)
        save_layout.addWidget(self.save_btn)
        
        layout.addLayout(save_layout)
    
    def browse_server_path(self):
        """浏览选择服务端路径"""
        path = QFileDialog.getExistingDirectory(self, "选择服务端目录", self.server_input.text())
        if path:
            self.server_input.setText(path)
            # 自动更新PVF路径（只有有凭证文件时才更新输入框）
            if self.pvf_input:
                pvf_path = os.path.join(path, "runtime", "data", "dnf", "Script.pvf")
                self.pvf_input.setText(pvf_path)
    
    def browse_client_path(self):
        """浏览选择客户端路径"""
        path = QFileDialog.getExistingDirectory(self, "选择客户端目录", self.client_input.text())
        if path:
            self.client_input.setText(path)
    
    def browse_pvf_path(self):
        """浏览选择PVF文件（需要凭证文件）"""
        path, _ = QFileDialog.getOpenFileName(self, "选择PVF文件", self.pvf_input.text(), "PVF文件 (*.pvf);;所有文件 (*.*)")
        if path:
            self.pvf_input.setText(path)
    
    def save_settings(self):
        """保存设置到config.lau"""
        try:
            server_path = self.server_input.text().strip()
            client_path = self.client_input.text().strip()
            pvf_path = self.pvf_input.text().strip() if self.pvf_input else ""
            
            # 更新配置
            self.config.config['server_path'] = server_path
            self.config.config['client_path'] = client_path
            # 只有有凭证文件时才保存自定义PVF路径
            if self.has_credential and pvf_path:
                self.config.config['pvf_path'] = pvf_path
            elif not self.has_credential:
                # 没有凭证文件时，清除自定义PVF路径
                self.config.config.pop('pvf_path', None)
            
            # 保存到文件
            success = self.config.save_config()
            
            if success:
                # 重新加载配置
                self.config.config = self.config._load_config()
                # 更新PVF路径显示（如果没有自定义路径，自动计算）
                if not self.has_credential or not pvf_path:
                    auto_pvf = self.config.get_pvf_path()
                    if self.pvf_input:
                        self.pvf_input.setText(auto_pvf if auto_pvf else "未找到PVF文件")
                # 显示成功提示
                self.save_btn.setText("保存成功！")
                QTimer.singleShot(2000, lambda: self.save_btn.setText("保存设置"))
            else:
                self.save_btn.setText("保存失败！")
                QTimer.singleShot(3000, lambda: self.save_btn.setText("保存设置"))
            
        except Exception as e:
            self.save_btn.setText(f"保存失败: {str(e)[:20]}")
            QTimer.singleShot(3000, lambda: self.save_btn.setText("保存设置"))

# ============== GM工具主窗口 ==============
class GMToolMainWindow(QMainWindow):
    """GM工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = GMConfig()
        self.db = GMDatabase(self.config)
        self.current_widget = None
        self.nav_buttons = []
        self.items_data = None  # PVF预加载的物品数据
        self.pvf_loading = False  # PVF是否正在加载
        
        self.init_ui()
        # 延迟连接数据库，避免阻塞主线程导致窗口不显示
        QTimer.singleShot(100, self.connect_db)
        # 延迟预加载PVF物品数据（在数据库连接后开始）
        QTimer.singleShot(500, self.preload_pvf_items)
    
    def init_ui(self):
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setWindowTitle("gmtool")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setStyleSheet(GLOBAL_QSS)
        
        self.dragging = False
        self.drag_position = QPoint()
        
        # 主容器
        main_container = QWidget()
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet("""
            #mainContainer {
                background-color: #202020;
                border-radius: 10px;
            }
        """)
        
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题栏（左上角添加"多功能GM工具"字样）
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(56)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(24, 0, 16, 0)
        title_layout.setSpacing(8)
        
        # 标题文字（左上角）
        title_label = QLabel("多功能GM工具")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; background-color: transparent;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(32, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("关闭")
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888888; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; padding: 0px; }
            QPushButton:hover { background-color: #e81123; color: #ffffff; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        # 双击标题栏最小化
        title_bar.mouseDoubleClickEvent = self.on_title_double_click
        
        main_layout.addWidget(title_bar)
        
        # 标题栏下横分割线
        title_hline = QFrame()
        title_hline.setFixedHeight(1)
        title_hline.setAttribute(Qt.WA_StyledBackground, True)
        title_hline.setStyleSheet("background-color: #2a2a2a;")
        main_layout.addWidget(title_hline)
        
        # 内容区域（侧边栏 + 主内容）
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
        
        # 导航按钮
        nav_items = [
            ("角色管理", "character"),
            ("背包管理", "inventory"),
            ("道具发放", "item"),
            ("邮件系统", "mail"),
            ("操作日志", "log"),
            ("工具设置", "settings"),
        ]
        
        for text, key in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((btn, key))
        
        sidebar_layout.addStretch()
        
        # 数据库状态（移到侧边栏最下方）
        self.db_status_label = QLabel("数据库: 未连接")
        self.db_status_label.setObjectName("statusLabel")
        self.db_status_label.setAlignment(Qt.AlignCenter)
        self.db_status_label.setWordWrap(True)
        sidebar_layout.addWidget(self.db_status_label)
        
        # 重连数据库按钮
        self.reconnect_db_btn = QPushButton("重连数据库")
        self.reconnect_db_btn.setObjectName("reconnectBtn")
        self.reconnect_db_btn.setCursor(Qt.PointingHandCursor)
        self.reconnect_db_btn.setStyleSheet("""
            QPushButton#reconnectBtn {
                background-color: transparent;
                color: #cccccc;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px 16px;
                text-align: center;
                font-size: 13px;
            }
            QPushButton#reconnectBtn:hover {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #666666;
            }
            QPushButton#reconnectBtn:pressed {
                background-color: #1a1a1a;
            }
        """)
        self.reconnect_db_btn.clicked.connect(self.reconnect_db)
        sidebar_layout.addWidget(self.reconnect_db_btn)
        
        content_layout.addWidget(self.sidebar)
        
        # 主内容区域
        self.content_area = QWidget()
        self.content_area.setObjectName("contentArea")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        content_layout.addWidget(self.content_area)
        
        main_layout.addWidget(content_widget)
        
        # 底部状态栏 - 同步登录器风格
        status_bar = QWidget()
        status_bar.setFixedHeight(28)
        status_bar.setStyleSheet("background-color: transparent; border-top: 1px solid #2a2a2a;")
        
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
        self.module_label = QLabel("角色管理")
        self.module_label.setStyleSheet("color: #777777; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.module_label)
        
        # PVF加载进度条（左下角）
        self.pvf_progress_bar = QProgressBar()
        self.pvf_progress_bar.setObjectName("pvfProgressBar")
        self.pvf_progress_bar.setFixedWidth(200)
        self.pvf_progress_bar.setFixedHeight(18)
        self.pvf_progress_bar.setTextVisible(True)
        self.pvf_progress_bar.setFormat("%p%")
        self.pvf_progress_bar.setValue(0)
        self.pvf_progress_bar.setVisible(False)  # 默认隐藏，加载时显示
        self.pvf_progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 3px;
                text-align: center;
                color: #cccccc;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #2d6cdf;
                border-radius: 2px;
            }
        """)
        status_layout.addWidget(self.pvf_progress_bar)

        # 静默通知标签
        self.notify_label = QLabel("")
        self.notify_label.setStyleSheet("color: #ff6b6b; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.notify_label)
        
        status_layout.addStretch()
        
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #777777; font-size: 12px; background-color: transparent;")
        status_layout.addWidget(self.time_label)
        
        main_layout.addWidget(status_bar)
        
        # 定时器更新时间
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
        self.update_time()
        
        # 使用setCentralWidget设置中央部件（QMainWindow必须这样）
        self.setCentralWidget(main_container)
        
        # 默认显示角色管理
        self.switch_page("character")
    
    def connect_db(self):
        """连接数据库"""
        try:
            self.db.connect()
            self.db_status_label.setText("数据库: 已连接")
            self.db_status_label.setObjectName("statusLabelSuccess")
            self.status_label.setText("数据库连接成功")
        except Exception as e:
            self.db_status_label.setText("数据库: 连接失败")
            self.db_status_label.setObjectName("statusLabelError")
            self.status_label.setText(f"数据库连接失败: {str(e)}")
            GMConfirmDialog.confirm(self, "数据库连接失败", 
                                f"无法连接到数据库:\n{str(e)}\n\n请检查服务端路径和数据库配置。",
                                "确定", "", "normal", "right")
    
    def reconnect_db(self):
        """重连数据库"""
        try:
            self.status_label.setText("正在重连数据库...")
            self.db_status_label.setText("数据库: 重连中...")
            
            # 先关闭旧连接
            self.db.disconnect()
            
            # 重新连接
            self.db.connect()
            
            # 更新状态
            self.db_status_label.setText("数据库: 已连接")
            self.db_status_label.setObjectName("statusLabelSuccess")
            self.status_label.setText("数据库重连成功")
            
            # 更新当前页面的数据库连接
            if self.current_widget and hasattr(self.current_widget, 'db'):
                self.current_widget.db = self.db
            
        except Exception as e:
            self.db_status_label.setText("数据库: 重连失败")
            self.db_status_label.setObjectName("statusLabelError")
            self.status_label.setText(f"数据库重连失败: {str(e)}")
            GMConfirmDialog.confirm(self, "数据库重连失败", 
                                f"无法重连到数据库:\n{str(e)}\n\n请检查服务端路径和数据库配置。",
                                "确定", "", "normal", "right")
    
    def preload_pvf_items(self):
        """预加载PVF物品数据（在后台线程中进行）"""
        if self.pvf_loading:
            return
        
        self.pvf_loading = True
        self.status_label.setText("正在加载PVF物品数据...")
        self.pvf_progress_bar.setVisible(True)
        self.pvf_progress_bar.setValue(0)
        # 记录开始时间，用于计算加载耗时
        import time
        self.pvf_start_time = time.time()
        
        # 使用后台线程加载PVF，避免阻塞UI
        from PyQt5.QtCore import QThread, pyqtSignal
        
        class PVFLoadThread(QThread):
            finished = pyqtSignal(list)
            error = pyqtSignal(str)
            progress = pyqtSignal(int, str)
            
            def run(self):
                try:
                    def progress_callback(percent, message):
                        self.progress.emit(percent, message)
                    
                    items = load_items_from_pvf(progress_callback)
                    if items:
                        self.finished.emit(items)
                    else:
                        self.error.emit("物品列表为空")
                except Exception as e:
                    self.error.emit(str(e))
        
        self.pvf_thread = PVFLoadThread()
        self.pvf_thread.finished.connect(self.on_pvf_loaded)
        self.pvf_thread.error.connect(self.on_pvf_load_error)
        self.pvf_thread.progress.connect(self.on_pvf_progress)
        self.pvf_thread.start()
    
    def on_pvf_progress(self, percent, message):
        """PVF加载进度更新"""
        self.pvf_progress_bar.setValue(percent)
        if percent < 100:
            self.status_label.setText(f"PVF加载中: {message}")
    
    def on_pvf_loaded(self, items):
        """PVF物品数据加载完成"""
        global _pvf_items_dict_cache
        self.items_data = items
        self.pvf_loading = False
        self.pvf_progress_bar.setVisible(False)
        
        # 计算加载耗时
        import time
        elapsed = time.time() - self.pvf_start_time if hasattr(self, 'pvf_start_time') else 0
        self.status_label.setText(f"PVF物品数据加载完成，共 {len(items)} 个物品，耗时 {elapsed:.1f} 秒")
        
        # 重置字典缓存，确保下次获取时使用最新数据（纯内存，不写JSON）
        _pvf_items_dict_cache = None
        
        # 如果当前页面是道具发放或背包管理，刷新数据
        if hasattr(self.current_widget, 'items'):
            self.current_widget.items = items
            if hasattr(self.current_widget, 'status_label'):
                self.current_widget.status_label.setText(f"已加载 {len(items)} 个物品（PVF预加载）")
        if hasattr(self.current_widget, 'items_data'):
            # 转换为字典格式
            items_dict = {}
            for item in items:
                item_id = str(item.get('id', ''))
                if item_id:
                    items_dict[item_id] = item
            self.current_widget.items_data = items_dict
            if hasattr(self.current_widget, 'status_label'):
                self.current_widget.status_label.setText(f"已加载 {len(items_dict)} 个物品信息（PVF预加载）")
            # 自动刷新背包列表
            if hasattr(self.current_widget, 'load_inventory') and hasattr(self.current_widget, 'current_character_id'):
                if self.current_widget.current_character_id:
                    QTimer.singleShot(100, self.current_widget.load_inventory)
    
    def on_pvf_load_error(self, error_msg):
        """PVF物品数据加载失败"""
        self.pvf_loading = False
        self.pvf_progress_bar.setVisible(False)
        self.status_label.setText(f"PVF物品数据加载失败: {error_msg}")
    
    def switch_page(self, page_key):
        """切换页面"""
        # 清除当前内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 更新导航按钮状态 - 同步登录器风格
        for btn, key in self.nav_buttons:
            is_active = key == page_key
            btn.setProperty("class", "active" if is_active else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # 创建对应页面
        if page_key == "character":
            widget = CharacterManagerWidget(self.db, self.config)
        elif page_key == "inventory":
            widget = InventoryManagerWidget(self.db, self.config, self.items_data)
        elif page_key == "item":
            widget = ItemManagerWidget(self.db, self.config, self.items_data)
        elif page_key == "mail":
            widget = MailSystemWidget(self.db, self.config)
        elif page_key == "log":
            widget = LogViewerWidget(self.config)
        elif page_key == "settings":
            widget = ToolSettingsWidget(self.db, self.config)
        else:
            widget = QWidget()
        
        self.current_widget = widget
        self.content_layout.addWidget(widget)
        page_name = self.get_page_name(page_key)
        self.status_label.setText("就绪")
        if hasattr(self, 'module_label'):
            self.module_label.setText(page_name)
    
    def get_page_name(self, page_key):
        """获取页面名称"""
        names = {
            "character": "角色管理",
            "inventory": "背包管理",
            "item": "物品管理",
            "mail": "邮件系统",
            "log": "操作日志",
            "settings": "工具设置",
        }
        return names.get(page_key, "未知")
    
    def go_back(self):
        """返回"""
        self.switch_page("character")
    
    def update_time(self):
        """更新时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)
    
    def show_notify(self, message, duration=3000, color="#ff6b6b"):
        """状态栏静默通知"""
        if hasattr(self, 'notify_label'):
            self.notify_label.setText(message)
            self.notify_label.setStyleSheet(f"color: {color}; font-size: 12px; background-color: transparent;")
            QTimer.singleShot(duration, lambda: self.notify_label.setText(""))
    
    def on_title_double_click(self, event):
        self.showMinimized()
    
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
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            self.db.disconnect()
        except Exception:
            pass
        event.accept()

# ============== 主函数 ==============
def main():
    # 全局异常处理
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        import traceback
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"未捕获异常:\n{error_msg}")
        try:
            GMConfirmDialog.confirm(None, "程序错误", f"发生未捕获异常:\n\n{error_msg}", "确定", "", "danger", "right")
        except Exception:
            pass
    
    sys.excepthook = global_exception_handler
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # 优先从fonts目录加载思源黑体，失败则使用系统字体 - 和登录器一致
    font_family = "Microsoft YaHei"  # 默认回退字体
    font_loaded = False
    
    # 尝试从fonts目录加载（gmtool在module目录下，需要向上找一级）
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
    
    try:
        window = GMToolMainWindow()
        window.show()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"窗口初始化失败:\n{error_msg}")
        GMConfirmDialog.confirm(None, "初始化失败", f"窗口初始化失败:\n\n{error_msg}", "确定", "", "danger", "right")
        sys.exit(1)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
