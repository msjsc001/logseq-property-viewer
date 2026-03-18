# -*- mode: python ; coding: utf-8 -*-
"""
Property Query - PyInstaller 构建配置
"""

import os
import sys

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(SPEC))

# 分析入口文件
a = Analysis(
    ['run_app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # 前端构建产物
        ('frontend/dist', 'frontend/dist'),
        # 后端模块
        ('backend', 'backend'),
        # 图标文件
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        # FastAPI 和依赖
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'starlette',
        'starlette.routing',
        'starlette.responses',
        'starlette.middleware',
        'starlette.middleware.cors',
        'pydantic',
        'pydantic_core',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        # watchdog
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.polling',
        'watchdog.events',
        # 项目模块
        'core',
        'cache',
        'config',
        'app_constants',
        'app_logging',
        'backend.main',
        'backend.file_watcher',
        'backend.query_engine',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PropertyQuery',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 关键：不显示终端窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 应用图标
)
