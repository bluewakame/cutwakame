# Mac配布物の依存関係

このローカルビルドは次を含みます。各プロジェクトのライセンスが適用されます。

- Python 3.12.14 / Tcl・Tk 9: PSF / Tcl-Tk license。Pythonはuv管理のpython-build-standaloneから取得。
  https://github.com/astral-sh/python-build-standalone
  https://docs.python.org/3/license.html
  https://www.tcl-lang.org/software/tcltk/license.html
- Pillow 13.0.0: HPND。https://github.com/python-pillow/Pillow
- PyInstaller 6.22.3: GPL-2.0-or-later + bootloader exception。https://github.com/pyinstaller/pyinstaller
- FFmpeg 7.1 arm64: imageio-ffmpeg 0.7.0の同梱バイナリ。libx264を含むGPL構成。
  https://github.com/imageio/imageio-ffmpeg
  https://github.com/imageio/imageio-binaries
  https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz
  https://ffmpeg.org/legal.html
- FFprobe 4.4.1 arm64: npm @ffprobe-installer/darwin-arm64 5.0.1配布物（パッケージの表記はLGPL-2.1）。
  https://www.npmjs.com/package/@ffprobe-installer/darwin-arm64
  https://ffmpeg.org/releases/ffmpeg-4.4.1.tar.xz

日本語字幕にはmacOS付属フォントを実行時に使用します。フォントファイルは同梱していません。

この成果物はユーザーのローカル利用向けに作成しています。外部への再配布時には、同梱バイナリのライセンス本文、ビルド設定・対応ソースの提供要件を別途整えてください。
