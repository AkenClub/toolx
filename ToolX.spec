# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugins', 'plugins'),
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'plugins.quick_copy.plugin',
        'plugins.worklog.plugin',
        'plugins.worklog.calculations',
        'plugins.worklog.storage',
        'plugins.worklog.ui',
        'core.plugin_admin',
        'core.plugin_context',
        'core.plugin_manifest',
        'core.plugin_paths',
        'core.settings',
        'core.settings.settings_services',
        'core.settings.settings_widget',
        'core.settings.pages.about',
        'core.settings.pages.appearance',
        'core.settings.pages.general',
        'core.settings.pages.plugin_manager',
        'core.settings.pages.startup',
        'core.settings_services',
        'core.system_context'
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
    name='ToolX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon='assets/app_icon.ico',
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
