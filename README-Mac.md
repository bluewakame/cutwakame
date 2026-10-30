# カットワカメ Mac版 0.2.1

Apple Silicon（M1/M2/M3/M4以降）向けです。Intel Mac向けバイナリではありません。

## 起動

`.app` とZIPはビルド時に `dist/` に生成されます。Gitリポジトリに実行ファイルは含めていません。

`dist/CutWakame.app` をダブルクリックしてください。PythonやFFmpegの追加インストールは不要です。別のMacへ移す場合は `dist/CutWakame-mac.zip` を展開し、アプリをApplicationsへコピーできます。

Appleの公証はしていません。初回にmacOSが開くことを拒否した場合は、システム設定 → プライバシーとセキュリティ → 「このまま開く」を選択してください。

「＋ メディア追加」で動画を読み込み、クリップを選択してIN/OUT・並び替え・字幕を設定し、「書き出し」でMP4に保存します。タイムライン上の「✂ カット」でプレビュー位置を分割できます。タイムラインの上の境界をドラッグすると高さを変更できます。編集は自動保存です。「ファイル」メニューからプロジェクトを開いたり、別名で保存できます。

既定プロジェクト: `~/Documents/カットワカメ/Untitled.aicut.json`
素材動画はプロジェクト内にコピーされません。読み込んだ素材を移動すると参照できなくなります。

## MCP

`.app` 内の実行ファイルを指定します。画面側と同じプロジェクトのパスを設定してください。

```toml
[mcp_servers.cutwakame]
command = "/Applications/CutWakame.app/Contents/MacOS/CutWakame"
args = ["--mcp", "--project", "/Users/YOUR_NAME/Documents/カットワカメ/Untitled.aicut.json"]
```

## ソースからビルド

macOSで、Tk対応Python 3.12以降と同じCPU向けのFFmpeg・FFprobeを用意します。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
./build-mac.sh
```

PATH以外にある実行ファイルは `FFMPEG` / `FFPROBE`、Pythonは `PYTHON` 環境変数で指定できます。ビルドしたCPU向けのアプリになります。Intel版はIntel環境で別途ビルド・確認が必要です。

## 確認済み

Apple Silicon上でアプリの起動・編集画面表示、同梱実行ファイルからのMCP初期化を確認。自動テストで、同梱ツール検索、日本語フォント、音声あり／なしの動画結合、トリム・分割、日本語字幕付きMP4書き出し、MCP経由のプロジェクト読み取りを確認しています。

元の仕様どおり、プレビューの音声再生・複数映像トラック・トランジションは未実装です。Apple公証と他のmacOSバージョンでの検証は未実施です。

元リポジトリ: https://github.com/bluewakame/cutwakame
