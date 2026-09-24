# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

hiddenimports = (
    ["oracledb.thin_impl", "_cffi_backend"]
    + collect_submodules("keyring.backends")
    + collect_submodules("cryptography")
    + ["win32timezone", "win32cred", "win32ctypes.pywin32"]
)

binaries = collect_dynamic_libs("cryptography")

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        ('examples\\caso1\\query.sql', 'examples/caso1'),
        ('examples\\caso1\\input.xlsx', 'examples/caso1'),
        ('examples\\caso1\\output_atteso.xlsx', 'examples/caso1'),
    ],
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='ReportGenerator',
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

