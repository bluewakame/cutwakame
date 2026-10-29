# カットワカメ 0.2.0

AIからMCPで操作できるWindows向け動画編集ソフトです。`CutWakame.exe` はFFmpeg/FFprobeを同梱した単体実行ファイルです。

## 編集画面

- **直感的な操作**: メディア追加、クリックでクリップを選択、タイムラインで全体を確認、フレームプレビューとスクラブ
- **細かな編集**: IN/OUTの秒単位指定、再生位置での分割、複製、削除、順序変更
- **構成を再利用**: 動画クリップとテキストレイヤー、書き出し設定をJSONプロジェクトに保存。MCPから同じ構成を編集可能
- **書き出し**: 720p、1080p、縦動画のプリセット。H.264/AACのMP4

起動するには `CutWakame.exe` をダブルクリックします。プロジェクトの既定保存先は `Documents\カットワカメ\Untitled.aicut.json` です。別のプロジェクトを開く場合:

```powershell
.\CutWakame.exe --project "C:\path\my-edit.aicut.json"
```

## MCP接続

アプリ自身がMCP stdioサーバーになります。画面とMCPで同じプロジェクトパスを指定してください。

```toml
[mcp_servers.cutwakame]
command = "C:\\path\\to\\CutWakame.exe"
args = ["--mcp", "--project", "C:\\path\\to\\my-edit.aicut.json"]
```

ツール: `get_project`, `add_clip`, `trim_clip`, `split_clip`, `duplicate_clip`, `remove_clip`, `move_clip`, `add_title`, `remove_title`, `set_export`, `export_video`。クリップIDは `add_clip` / `get_project` の応答から取得します。`move_clip` の `index` は0始まりです。

## 制限と開発

プレビューは選択した素材をフレーム単位で確認する方式で、音声は再生しません。完成タイムライン全体のリアルタイム合成プレビュー、波形、トランジション、複数映像トラックは未実装です。既存の0.1プロジェクトは読み込み可能です。

ソースからの実行には Python 3.14、Pillow、FFmpeg/FFprobeが必要です。`python aicut.py` で起動し、PyInstallerを入れて `build.ps1` を実行すると `.exe` を作れます。


