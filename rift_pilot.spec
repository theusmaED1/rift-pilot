# -*- mode: python ; coding: utf-8 -*-
# Gerar com: pyinstaller rift_pilot.spec

a = Analysis(
    ["src/rift_pilot/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("config.yaml", "."),
        ("icon.ico", "."),
    ],
    hiddenimports=[
        "edge_tts",
        "edge_tts.communicate",
        "httpx",
        "yaml",
        "tkinter",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["piper_tts", "piper_phonemize"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="rift-pilot",
    icon="icon.ico",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    onefile=True,
)
