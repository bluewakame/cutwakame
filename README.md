# カットワカメ 0.1.0

AIから操作できるWindows用の小さな動画編集ソフトです。`CutWakame.exe` は単体で起動でき、FFmpeg/FFprobeを同梱しています。Windows 11で動作確認しました。

## 画面から使う

`CutWakame.exe` をダブルクリックします。動画を追加し、クリップを選んでトリム・削除・並べ替えを行い、`Export MP4` で書き出します。現在の画面はクリップ一覧方式で、プレビューや波形表示は未実装です。

プロジェクトは既定で `Documents\カットワカメ\Untitled.aicut.json` に保存されます。別のプロジェクトを使う場合:

```powershell
.\CutWakame.exe --project "C:\path\my-edit.aicut.json"
```

## MCP接続

このアプリ自身がMCP stdioサーバーになります。MCPクライアントの設定で次のコマンドと引数を指定します。画面とMCPで同じプロジェクトパスを指定してください。

```toml
[mcp_servers.cutwakame]
command = "C:\\path\\to\\CutWakame.exe"
args = ["--mcp", "--project", "C:\\path\\to\\my-edit.aicut.json"]
```

提供ツール: `get_project`, `add_clip`, `trim_clip`, `remove_clip`, `move_clip`, `export_video`。クリップIDは `add_clip` または `get_project` の結果から取得します。`move_clip` の `index` は0始まりです。

操作例: 「動画Aの0〜8秒と動画Bの12〜18秒を追加して、順序を入れ替え、`output.mp4` に書き出して」

## 書き出し仕様

MP4/H.264/AAC、1280×720、30 fps。縦横比を維持し余白を付けます。無音の素材にも対応します。元動画は上書きしません。高解像度設定、字幕、複数トラック、トランジション、プレビューは今後の拡張対象です。

## 再ビルド

Python 3.14、PyInstaller 6、FFmpeg/FFprobeが必要です。`build.ps1` を実行すると `CutWakame.exe` を再生成できます。編集可能なソースは `aicut.py` です。


