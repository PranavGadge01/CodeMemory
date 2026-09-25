# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the CodeMemory FastAPI sidecar executable.

This produces a ``codememory-api.exe`` that starts the FastAPI server
with ``api.app:create_app`` — identical behavior to the ``codememory-api``
console script, but as a self-contained Windows executable for use as a
Tauri sidecar.

Usage:
    pip install pyinstaller
    pyinstaller --noconfirm backend/codememory-api.spec

The resulting executable is placed at ``dist/codememory-api.exe``.

Do NOT bundle the user's DuckDB database or data files — those are runtime
artifacts resolved from ``CODEMEMORY_DATA_DIR`` at the process working directory.

Heavy optional packages (torch, tensorflow, scipy, openai, streamlit, plotly)
are excluded to keep the binary size reasonable. The sidecar runs fully
offline using the built-in heuristic AI provider.
"""

block_cipher = None

a = Analysis(
    ['../../src/api/app.py'],
    pathex=['../../src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'duckdb',
        'polars',
        'polars.io',
        'polars.expr',
        'pyarrow',
        'uvicorn',
        'uvicorn.lifespan',
        'uvicorn.middleware',
        'uvicorn.middleware.proxy_headers',
        'uvicorn.middleware.asgi2',
        'uvicorn.middleware.wsgi',
        'cryptography',
        'keyring',
        'rich',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    excludes=[
        'streamlit',
        'torch',
        'tensorflow',
        'scipy',
        'skimage',
        'openai',
        'plotly',
    ],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='codememory-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
