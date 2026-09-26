# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/api/app.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=['uvicorn.lifespan', 'uvicorn.middleware', 'uvicorn.middleware.proxy_headers', 'uvicorn.middleware.asgi2', 'uvicorn.middleware.wsgi', 'duckdb', 'polars', 'polars.io', 'polars.expr', 'pyarrow', 'cryptography', 'keyring', 'rich'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['streamlit', 'torch', 'tensorflow', 'scipy', 'skimage', 'plotly', 'openai'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
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
