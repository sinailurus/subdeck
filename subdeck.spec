# -*- mode: python ; coding: utf-8 -*-
# SubDeck 桌面包打包配置（PyInstaller 6.x，v1.6.0 起）
# 产物：dist/SubDeck（单文件，控制台窗口版）
# CI 中由 .github/workflows/docker-publish.yml 调用：
#   - build-windows（windows-latest → SubDeck.exe）
#   - build-macos（macos-15-intel Intel / macos-15 Apple Silicon → SubDeck）
# icon：Windows 用 ico；macOS 用 icns（Dock 图标）。

import sys

# v1.6.0 起：Windows 用 ico；v1.6.4 起 macOS 用 icns（Dock 图标）
EXE_ICON = ('packaging/subdeck.ico' if sys.platform == 'win32'
            else 'packaging/subdeck.icns' if sys.platform == 'darwin' else None)

a = Analysis(
    ['run_exe.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static')],
    # uvicorn 启动时按 loop/protocol 动态导入子模块，显式声明防漏
    hiddenimports=[
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.none_impl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'PIL', 'numpy', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SubDeck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 保留黑色控制台窗口：看得见日志，关窗即停止
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=EXE_ICON,
)
