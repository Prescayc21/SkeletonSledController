# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

# Platform-specific settings
is_mac = sys.platform == 'darwin'
is_windows = sys.platform == 'win32'

# Define data files to include (add any needed files here)
data_files = []

# Check if icon files exist
icon_file_windows = os.path.join(os.getcwd(), 'app_icon.ico')
icon_file_mac = os.path.join(os.getcwd(), 'app_icon.icns')

windows_icon = icon_file_windows if os.path.exists(icon_file_windows) else None
mac_icon = icon_file_mac if os.path.exists(icon_file_mac) else None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'numpy', 'serial', 'serial.tools.list_ports'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SkeletonSledController',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    icon=windows_icon,
)

# Create a directory with all dependencies
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SkeletonSledController',
)

# For macOS, create a .app bundle
if is_mac:
    app = BUNDLE(
        coll,
        name='SkeletonSledController.app',
        icon=mac_icon,
        bundle_identifier='com.example.skeletonsled',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': 'True',
            'NSPrincipalClass': 'NSApplication',
            'LSBackgroundOnly': 'False',
            'CFBundleDisplayName': 'SkeletonSledController',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
