# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import shutil

BLOCK_CIPHER = None

SPEC_DIR = Path(SPECPATH).resolve()

# ===== Files and Names =====
ENTRY_SCRIPT = str(SPEC_DIR / '..' / 'FyShare.py')
FYSHARE_ICON = str(SPEC_DIR / '..' / 'static' / 'images' / 'fyshare_logo_256x256.ico')
DIST_DIR = 'dist'
CONTENTS_DIR = 'runtime'
APP_NAME = 'Fyshare'

ASSETS_TO_COPY = [
    ('../static', 'static'),
    ('../templates', 'templates'),
    ('../config.json', 'config.json'),
    ('../config_example.json', 'config_example.json'),
    ('../README.md', 'README.md'),
    ('../LICENSE', 'LICENSE')
]

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=[FYSHARE_ICON],
    contents_directory=CONTENTS_DIR,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name=DIST_DIR,
)


# =========================================================
# POST-BUILD -- Copy Files
# =========================================================

DIST_ROOT = Path(DISTPATH) / DIST_DIR

print(f"\n[*] Customizing layout in: {DIST_ROOT}")

for src, dest in ASSETS_TO_COPY:
    src_path = (SPEC_DIR / src).resolve()
    dest_path = DIST_ROOT / dest

    if src_path.exists():
        if src_path.is_dir():
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)

        print(f"    [OK] Deployed: {dest_path}")
    else:
        print(f"    [!] Missing: {src_path}")
