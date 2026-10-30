#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
FFMPEG="${FFMPEG:-$(command -v ffmpeg || true)}"
FFPROBE="${FFPROBE:-$(command -v ffprobe || true)}"
[[ "$(uname -s)" == Darwin ]] || { echo 'macOS上で実行してください' >&2; exit 1; }
[[ -x "$FFMPEG" && -x "$FFPROBE" ]] || { echo 'FFMPEG/FFPROBEに実行ファイルのパスを指定してください' >&2; exit 1; }
"$PYTHON" -c 'import tkinter, PIL, PyInstaller'
export PYINSTALLER_CONFIG_DIR="$PWD/build/pyinstaller-cache"
mkdir -p build/media
cp "$FFMPEG" build/media/ffmpeg
cp "$FFPROBE" build/media/ffprobe
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed --onedir \
  --name CutWakame --osx-bundle-identifier jp.cutwakame.editor \
  --paths . --hidden-import studio_tk \
  --add-binary 'build/media/ffmpeg:bin' --add-binary 'build/media/ffprobe:bin' aicut.py
mkdir -p dist/CutWakame.app/Contents/Resources/docs
cp README-Mac.md THIRD-PARTY-Mac.md dist/CutWakame.app/Contents/Resources/docs/
codesign --force --deep --sign - dist/CutWakame.app
ditto -c -k --sequesterRsrc --keepParent dist/CutWakame.app dist/CutWakame-mac.zip
