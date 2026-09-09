#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PVF解析器工具 - GUI版本
用于解析DNF的PVF文件，提取文件列表、物品信息等
"""
import sys
import os
import json
import re

# 添加当前目录到路径
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_path)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QTextEdit, QSplitter, QGroupBox, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

from pvf_parser import PVFParser
from gm_tool import extract_item_info_from_pvf, translate_item_type, should_filter_item


# 全局样式
GLOBAL_QSS = """
QMainWindow, QWidget {
    background-color: #202020;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Noto Sans SC", sans-serif;
    font-size: 13px;
}
QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #3a3a3a;
    border: 1px solid #666666;
}
QPushButton:pressed {
    background-color: #1a1a1a;
}
QLineEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px 8px;
}
QLineEdit:focus {
    border: 1px solid #0078d4;
}
QTableWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #333333;
    gridline-color: #333333;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #444444;
    padding: 6px;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #333333;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #aaaaaa;
    border: 1px solid #444444;
    padding: 8px 16px;
}
QTabBar::tab:selected {
    background-color: #0078d4;
    color: #ffffff;
}
QProgressBar {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
QTextEdit {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #333333;
}
QGroupBox {
    border: 1px solid #444444;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLabel {
    color: #cccccc;
}
"""


class ParseThread(QThread):
    """解析PVF的后台线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, pvf_path, extract_items=False):
        super().__init__()
        self.pvf_path = pvf_path
        self.extract_items = extract_items
        self.parser = None
    
    def run(self):
        try:
            self.progress.emit(5, "正在读取PVF文件...")
            self.parser = PVFParser(self.pvf_path)
            self.parser.load()
            
            self.progress.emit(30, "正在获取文件列表...")
            files = self.parser.list_files()
            
            result = {
                'file_count': self.parser.file_count,
                'group_count': self.parser.group_count,
                'body_size': self.parser.body_size,
                'str_a_size': len(self.parser.str_a) if self.parser.str_a else 0,
                'str_w_size': len(self.parser.str_w) if self.parser.str_w else 0,
                'files': files,
                'items': []
            }
            
            # 统计文件类型
            extensions = {}
            for f in files:
                name = f['name']
                if '.' in name:
                    ext = name.rsplit('.', 1)[1].lower()
                    extensions[ext] = extensions.get(ext, 0) + 1
            result['extensions'] = extensions
            
            # 提取物品信息
            if self.extract_items:
                self.progress.emit(40, "正在提取物品信息...")
                items = []
                
                stackable_files = [f for f in files if 'stackable' in f['archive_path'].lower() and f['name'].endswith('.stk')]
                equ_files = [f for f in files if 'equipment/character/' in f['archive_path'].lower() and f['name'].endswith('.equ')]
                
                total = len(stackable_files) + len(equ_files)
                current = 0
                
                # 处理消耗品
                for f in stackable_files:
                    current += 1
                    if current % 500 == 0 or current == total:
                        percent = 40 + int((current / max(total, 1)) * 50)
                        self.progress.emit(percent, f"处理消耗品: {current}/{total}")
                    
                    item_info = extract_item_info_from_pvf(self.parser, f['archive_path'], f['name'])
                    if item_info and not should_filter_item(item_info['name']):
                        translated_type = translate_item_type(
                            kind=item_info.get('kind', ''),
                            equipment_type=item_info.get('equipment_type', ''),
                            stackable_type=item_info.get('stackable_type', '')
                        )
                        item_info['type'] = translated_type
                        items.append(item_info)
                
                # 处理装备
                for f in equ_files:
                    current += 1
                    if current % 500 == 0 or current == total:
                        percent = 40 + int((current / max(total, 1)) * 50)
                        self.progress.emit(percent, f"处理装备: {current}/{total}")
                    
                    item_info = extract_item_info_from_pvf(self.parser, f['archive_path'], f['name'])
                    if item_info and not should_filter_item(item_info['name']):
                        translated_type = translate_item_type(
                            kind=item_info.get('kind', 'equipment'),
                            equipment_type=item_info.get('equipment_type', ''),
                            stackable_type=item_info.get('stackable_type', '')
                        )
                        item_info['type'] = translated_type
                        items.append(item_info)
                
                result['items'] = items
            
            self.progress.emit(100, "解析完成！")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class PVFToolWindow(QMainWindow):
    """PVF解析器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.parser = None
        self.parse_result = None
        self.parse_thread = None
        self.filtered_items = None
        self.all_files = []
        self.all_items = []
        
        # 搜索延迟定时器
        self.file_search_timer = QTimer()
        self.file_search_timer.setSingleShot(True)
        self.file_search_timer.timeout.connect(self._do_filter_files)
        
        self.item_search_timer = QTimer()
        self.item_search_timer.setSingleShot(True)
        self.item_search_timer.timeout.connect(self._do_filter_items)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("PVF解析器工具")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setStyleSheet(GLOBAL_QSS)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # 文件选择区域
        file_group = QGroupBox("PVF文件")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("请选择或输入PVF文件路径...")
        file_layout.addWidget(self.file_path_edit)
        
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        self.parse_btn = QPushButton("解析PVF")
        self.parse_btn.clicked.connect(self.parse_pvf)
        file_layout.addWidget(self.parse_btn)
        
        self.extract_items_check = QComboBox()
        self.extract_items_check.addItems(["仅解析文件信息", "提取物品信息"])
        file_layout.addWidget(self.extract_items_check)
        
        main_layout.addWidget(file_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 文件信息页
        self.info_widget = QWidget()
        self.info_layout = QVBoxLayout(self.info_widget)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_layout.addWidget(self.info_text)
        self.tab_widget.addTab(self.info_widget, "文件信息")
        
        # 文件列表页
        self.files_widget = QWidget()
        files_layout = QVBoxLayout(self.files_widget)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.file_search_edit = QLineEdit()
        self.file_search_edit.setPlaceholderText("输入文件名或路径关键词（停止输入300ms后自动搜索）...")
        self.file_search_edit.textChanged.connect(lambda: self.file_search_timer.start(300))
        search_layout.addWidget(self.file_search_edit)
        files_layout.addLayout(search_layout)
        
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["文件名", "路径", "大小"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        files_layout.addWidget(self.files_table)
        
        self.tab_widget.addTab(self.files_widget, "文件列表")
        
        # 物品列表页
        self.items_widget = QWidget()
        items_layout = QVBoxLayout(self.items_widget)
        
        # 搜索和导出
        items_top_layout = QHBoxLayout()
        items_top_layout.addWidget(QLabel("搜索:"))
        self.item_search_edit = QLineEdit()
        self.item_search_edit.setPlaceholderText("输入物品ID或名称（停止输入300ms后自动搜索）...")
        self.item_search_edit.textChanged.connect(lambda: self.item_search_timer.start(300))
        items_top_layout.addWidget(self.item_search_edit)
        
        self.export_btn = QPushButton("导出JSON")
        self.export_btn.clicked.connect(self.export_items)
        self.export_btn.setEnabled(False)
        items_top_layout.addWidget(self.export_btn)
        
        items_layout.addLayout(items_top_layout)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["ID", "名称", "类型", "种类"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        items_layout.addWidget(self.items_table)
        
        self.tab_widget.addTab(self.items_widget, "物品列表")
        
        main_layout.addWidget(self.tab_widget)
        
        # 底部状态栏
        self.bottom_status = QLabel("PVF解析器工具 v1.0")
        self.bottom_status.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.bottom_status)
    
    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PVF文件", "", "PVF文件 (*.pvf);;所有文件 (*.*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def parse_pvf(self):
        """解析PVF文件"""
        pvf_path = self.file_path_edit.text().strip()
        if not pvf_path:
            QMessageBox.warning(self, "警告", "请先选择PVF文件！")
            return
        
        if not os.path.exists(pvf_path):
            QMessageBox.warning(self, "警告", "文件不存在！")
            return
        
        extract_items = self.extract_items_check.currentIndex() == 1
        
        # 禁用按钮
        self.parse_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 启动解析线程
        self.parse_thread = ParseThread(pvf_path, extract_items)
        self.parse_thread.progress.connect(self.on_progress)
        self.parse_thread.finished.connect(self.on_parse_finished)
        self.parse_thread.error.connect(self.on_parse_error)
        self.parse_thread.start()
    
    def on_progress(self, percent, message):
        """进度更新"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def on_parse_finished(self, result):
        """解析完成"""
        self.parse_result = result
        self.parse_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"解析完成！共 {result['file_count']} 个文件")
        
        # 显示文件信息
        self.show_file_info(result)
        
        # 显示文件列表
        self.show_file_list(result['files'])
        
        # 显示物品列表
        if result['items']:
            self.show_item_list(result['items'])
            self.export_btn.setEnabled(True)
        else:
            self.items_table.setRowCount(0)
            self.export_btn.setEnabled(False)
    
    def on_parse_error(self, error_msg):
        """解析错误"""
        self.parse_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("解析失败！")
        QMessageBox.critical(self, "错误", f"解析失败：\n{error_msg}")
    
    def show_file_info(self, result):
        """显示文件信息"""
        info_text = f"""PVF文件信息
{'='*50}

文件总数: {result['file_count']:,}
分组数量: {result['group_count']:,}
主体大小: {result['body_size']:,} 字节 ({result['body_size']/1024/1024:.2f} MB)
strA (UTF-8) 大小: {result['str_a_size']:,} 字节 ({result['str_a_size']/1024/1024:.2f} MB)
strW (UTF-16) 大小: {result['str_w_size']:,} 字节 ({result['str_w_size']/1024/1024:.2f} MB)

文件类型统计:
{'-'*50}
"""
        for ext, count in sorted(result['extensions'].items(), key=lambda x: x[1], reverse=True)[:30]:
            info_text += f"  .{ext}: {count:,} 个\n"
        
        if result['items']:
            info_text += f"\n提取物品总数: {len(result['items']):,}\n"
        
        self.info_text.setText(info_text)
    
    def show_file_list(self, files):
        """显示文件列表"""
        self.all_files = files if files else []
        self._do_filter_files()
    
    def filter_files(self):
        """过滤文件列表（触发延迟搜索）"""
        self.file_search_timer.start(300)
    
    def _do_filter_files(self):
        """实际执行文件搜索"""
        if not self.all_files:
            return
        
        keyword = self.file_search_edit.text().strip().lower()
        if not keyword:
            filtered = self.all_files
        else:
            filtered = [f for f in self.all_files 
                       if keyword in f['name'].lower() 
                       or keyword in f['archive_path'].lower()]
        
        # 限制显示数量，避免卡顿
        max_display = 1000
        display_files = filtered[:max_display]
        
        self.files_table.setRowCount(len(display_files))
        for row, f in enumerate(display_files):
            self.files_table.setItem(row, 0, QTableWidgetItem(f['name']))
            self.files_table.setItem(row, 1, QTableWidgetItem(f['archive_path']))
            self.files_table.setItem(row, 2, QTableWidgetItem(f"{f.get('size', 0):,}"))
        
        if len(filtered) > max_display:
            self.status_label.setText(f"显示前{max_display}个文件，共匹配 {len(filtered):,} 个")
        else:
            self.status_label.setText(f"共 {len(filtered):,} 个文件")
    
    def show_item_list(self, items):
        """显示物品列表"""
        self.all_items = items if items else []
        self._do_filter_items()
    
    def filter_items(self):
        """过滤物品列表（触发延迟搜索）"""
        self.item_search_timer.start(300)
    
    def _do_filter_items(self):
        """实际执行物品搜索"""
        if not self.all_items:
            return
        
        keyword = self.item_search_edit.text().strip().lower()
        if not keyword:
            filtered = self.all_items
        else:
            filtered = [item for item in self.all_items 
                       if keyword in str(item.get('id', '')).lower() 
                       or keyword in item.get('name', '').lower()]
        
        # 限制显示数量
        max_display = 1000
        display_items = filtered[:max_display]
        
        self.items_table.setRowCount(len(display_items))
        for row, item in enumerate(display_items):
            self.items_table.setItem(row, 0, QTableWidgetItem(str(item.get('id', ''))))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.get('type', '')))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.get('kind', '')))
        
        if len(filtered) > max_display:
            self.status_label.setText(f"显示前{max_display}个物品，共匹配 {len(filtered):,} 个")
        else:
            self.status_label.setText(f"共 {len(filtered):,} 个物品")
    
    def export_items(self):
        """导出物品信息为JSON"""
        if not self.parse_result or not self.parse_result['items']:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出物品信息", "items.json", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.parse_result['items'], f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", f"物品信息已导出到：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = PVFToolWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
