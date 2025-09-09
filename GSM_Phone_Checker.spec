# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_enhanced.py'],
    pathex=[],
    binaries=[],
    datas=[('README.md', '.'), ('template_de_lai_loi_nhan_ok.wav', '.'), ('template_so_khong_dung_ok.wav', '.'), ('template_thue_bao_ok.wav', '.')],
    hiddenimports=['serial', 'serial.tools', 'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.scrolledtext', 'threading', 'queue', 'logging', 'datetime', 'time', 'os', 'typing', 'matplotlib', 'matplotlib.pyplot', 'numpy', 'scipy', 'scipy.signal', 'pyaudio'],
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
    a.binaries,
    a.datas,
    [],
    name='GSM_Phone_Checker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
