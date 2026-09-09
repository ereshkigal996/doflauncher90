# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gm_tool.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pymysql', 'pymysql.cursors', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gmtool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:/Users/56518/Downloads/DBObject/pip/gmtool/version_info.txt',
    uac_admin=True,
    icon=['C:/Users/56518/Downloads/DBObject/pip/icons/gmtool.ico'],
    contents_directory='lib',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='gmtool',
)
