# -*- mode: python ; coding: utf-8 -*-
# 测试版：适配Python版服务端

a = Analysis(
    ['launcher_test.py'],
    pathex=[],
    binaries=[],
    datas=[('DFO.ico', '.')],
    hiddenimports=['bcrypt._bcrypt', 'bcrypt', 'psutil', 'psutil._psutil_windows'],
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
    name='launcher_test',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['DFO.ico'],
    contents_directory='lib',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='launcher_test',
)
