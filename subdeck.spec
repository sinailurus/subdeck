# -*- mode: python ; coding: utf-8 -*-
# SubDeck Windows 桌面包打包配置（PyInstaller 6.x，v1.6.0）
# 产物：dist/SubDeck.exe（单文件，控制台窗口版）
# CI 中由 .github/workflows/docker-publish.yml 的 build-windows job 调用。

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
    icon='packaging/subdeck.ico',
)
