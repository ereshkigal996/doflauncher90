# -*- mode: python ; coding: utf-8 -*-
"""
GameServer 服务端 Python 实现 - PyInstaller 打包配置
版本: 0.1.0
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

# 项目根目录
project_root = os.path.abspath('.')

# 收集所有Python模块
hidden_imports = [
    'pymysql',
    'pymysql.cursors',
    'bcrypt',
]

# 收集所有自定义模块的子模块
hidden_imports += collect_submodules('config')
hidden_imports += collect_submodules('database')
hidden_imports += collect_submodules('network')
hidden_imports += collect_submodules('pvf')
hidden_imports += collect_submodules('game')
hidden_imports += collect_submodules('utils')

# 数据文件
datas = [
    # 配置模板
    (os.path.join(project_root, 'data', 'config', 'instance.example.json'), 'data/config'),
    (os.path.join(project_root, 'data', 'config', 'instance.sqlite.json'), 'data/config'),
    (os.path.join(project_root, 'data', 'config', 'instance.mysql.json'), 'data/config'),
]

# 分析
a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'gtk',
        'pytest',
        'unittest',
        'doctest',
    ],
    noarchive=False,
    optimize=0,
)

# 打包PYZ
pyz = PYZ(a.pure)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='game_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 收集所有文件
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='game_server',
)
