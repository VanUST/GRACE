# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for GRACE Context Manager — standalone executable."""

import sys, os
from pathlib import Path

HERE = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(HERE / 'launcher.py')],
    pathex=[str(HERE)],
    binaries=[],
    datas=[
        (str(HERE / 'grace_app' / 'assets'), 'grace_app/assets'),
    ],
    hiddenimports=[
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GRACE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(HERE / 'grace_app' / 'assets' / 'icon.png'),
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='GRACE.app',
        icon=str(HERE / 'grace_app' / 'assets' / 'icon.ico'),
        bundle_identifier='com.grace.manager',
        info_plist={
            'CFBundleName': 'GRACE Context Manager',
            'CFBundleDisplayName': 'GRACE',
            'CFBundleShortVersionString': '4.0.0',
            'NSHighResolutionCapable': True,
        },
    )
