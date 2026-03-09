# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Collect all data and binaries for problematic packages
datas = []
binaries = []
hiddenimports = []

# sentence-transformers / torch
td, tb, th = collect_all('sentence_transformers')
datas += td; binaries += tb; hiddenimports += th

td, tb, th = collect_all('torch')
datas += td; binaries += tb; hiddenimports += th

td, tb, th = collect_all('transformers')
datas += td; binaries += tb; hiddenimports += th

# ChromaDB
td, tb, th = collect_all('chromadb')
datas += td; binaries += tb; hiddenimports += th

# FastAPI / uvicorn / starlette
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('starlette')
hiddenimports += collect_submodules('fastapi')

# Google GenAI
td, tb, th = collect_all('google.genai')
datas += td; binaries += tb; hiddenimports += th

# Pydantic
hiddenimports += collect_submodules('pydantic')

# Include templates and static files
datas += [
    ('templates', 'templates'),
    ('static', 'static'),
]

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'slugify',
        'tqdm',
        'ollama',
        'chromadb.migrations',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='automacao3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # set False if you want no terminal window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='automacao3',
)