# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Danh sách các file dữ liệu cần đóng gói
datas = [('icon.ico', '.'), ('icon.png', '.')]

# Danh sách các thư viện cần ẩn import
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'threading',
    'queue',
    'time',
    'logging',
    'pathlib',
    'datetime',
    'os',
    'sys',
    'json',
    'pandas',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils.dataframe',
    'numpy',
    'librosa',
    'soundfile',
    'pydub',
    'torch',
    'transformers',
    'transformers.models.wav2vec2',
    'transformers.models.wav2vec2.modeling_wav2vec2',
    'transformers.models.wav2vec2.tokenization_wav2vec2',
    'transformers.models.wav2vec2.processing_wav2vec2',
    'transformers.tokenization_utils',
    'transformers.models.wav2vec2.configuration_wav2vec2',
    'transformers.models.wav2vec2.feature_extraction_wav2vec2',
    'transformers.models.wav2vec2.processing_wav2vec2',
    'scipy',
    'scipy.signal',
    'scipy.io',
    'scipy.io.wavfile',
]

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='GSM_Classification_System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Ẩn console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,  # Sử dụng icon nếu có
)