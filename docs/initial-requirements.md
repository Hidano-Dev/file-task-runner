# 初期要件

開発着手前に検討済みの前提と要件の整理。

## 背景

既存ツール `sequential_execution`（非 Git 管理のローカルフォルダ）は以下の構成だった。

- `sequential_execution.py`: tkinter でファイル複数選択 or フォルダ選択 → フォルダは再帰展開 → 指定 bat を 1 ファイルずつ `bat %1` で実行
- 処理ごとの `.bat`（多くは ffmpeg 等の 1 行ラッパー）

課題:

- `.bat` が Windows 専用で Mac ユーザーに提供できない
- 処理ごとに bat を書く必要があり、`%~n1` 等の bat 固有記法に依存

既存の汎用ツール（Nilesoft Shell、Double Commander、DropIt など）を調査したが、「処理を選ぶ → ファイル/フォルダを選ぶ → 再帰展開して 1 件ずつ実行」をそのまま満たすものは無く、作り直すことにした。

## 決定事項

- 対象 OS: Windows（メイン）、macOS。Linux は対象外
- 実装言語: Python 3.11 以上（標準ライブラリ `tomllib` を使うため）
- 処理定義: TOML にコマンドテンプレートとして宣言的に記述。複雑な処理のみ Python スクリプトで書く
- 呼び出し口: Windows は「送る」、macOS は Finder クイックアクション
- tkinter によるファイル選択 UI は廃止（OS 側の選択 UI に任せる）
- 既存の `sequential_execution` フォルダはそのまま残す
- 配布方法: `pyproject.toml` でパッケージ化し、`pipx install git+...` / `uv tool install` で導入する。開発時は editable install
- 並列実行: 初版は順次実行のみ。将来 `jobs` 指定を追加できる構造にしておく
- コンソール表示: 終了時に成功 / 失敗 / スキップのサマリを表示して待機する。タスクごとに `pause = "always" | "on_error" | "never"`（既定 `always`）で制御。macOS はクイックアクションから Terminal.app を開いてその中で実行する
- 既存出力ファイルの扱い: タスクに `output` を宣言しておき、実行前に全ファイルの出力先を一括チェックする。衝突があれば一覧を表示し、1 回だけ以下から選ばせる
  - `[O]` すべて上書き
  - `[R]` 別名で保存（`name (1).ext` 形式）
  - `[S]` 出力が既にあるファイルはスキップ
  - `[C]` キャンセル（何も実行しない）
- OS 専用タスク: 任意キー `os = ["windows"]` で指定。対象外 OS ではショートカット生成から除外し、実行時もエラーにする
- タスクの置き場所: 既存から移植したタスクはパッケージに同梱（組み込みタスク）。インストール済みの PC では、ユーザー設定フォルダの `tasks/` に `*.toml`（と参照する `*.py`）を置くだけでタスクを追加できる。組み込みと同名のタスクはユーザー側で上書き
  - Windows: `%APPDATA%\file-task-runner\tasks\`
  - macOS: `~/Library/Application Support/file-task-runner/tasks/`
  - 環境変数 `FILE_TASK_RUNNER_HOME` で設定フォルダの場所を変更可能
- ライセンス: MIT

## タスク定義仕様

```toml
[convert2mp4]
description = "Convert to MP4"
cmd = ["ffmpeg", "-i", "{path}", "{output}"]
output = "{dir}/{stem}.mp4"
ext = [".mov", ".avi", ".mkv"]

[7zip_sha256]
cmd = ["7z", "h", "-scrcsha256", "{path}"]
stdout = "{dir}/{stem}.sha256"

[check_image_size]
script = "check_image_size.py"
ext = [".png", ".jpg"]
```

| キー | 必須 | 内容 |
|---|---|---|
| `cmd` | `cmd` か `script` のどちらか | 実行するコマンド（文字列の配列）。シェルを介さずに実行する |
| `script` | 〃 | Python スクリプトのパス（TOML ファイルからの相対パス）。ランナーと同じ Python で `script.py <path> [<output>...]` として実行する |
| `output` | 任意 | 出力ファイルのパス（文字列または配列）。衝突チェックに使い、`cmd` 内では `{output}`（配列なら `{output[0]}` など）で参照する。親フォルダは自動作成 |
| `stdout` | 任意 | 標準出力を保存するファイルのパス。`output` と同様に衝突チェックの対象 |
| `ext` | 任意 | 対象拡張子（大文字小文字は区別しない）。省略時は全ファイル |
| `os` | 任意 | 対象 OS（`"windows"` / `"macos"`）。省略時は全 OS |
| `pause` | 任意 | 終了時の待機。`"always"`（既定）/ `"on_error"` / `"never"` |
| `description` | 任意 | 一覧や「送る」メニューに表示する名前 |

プレースホルダ:

| 名前 | 内容 | 例（`C:\work\a.mov`） |
|---|---|---|
| `{path}` | フルパス | `C:\work\a.mov` |
| `{dir}` | 親フォルダ | `C:\work` |
| `{name}` | ファイル名 | `a.mov` |
| `{stem}` | 拡張子なしファイル名 | `a` |
| `{ext}` | 拡張子 | `.mov` |
| `{output}` | `output` を展開した結果 | `C:\work\a.mp4` |

`{` `}` そのものを書く場合は `{{` `}}` とする。終了コードが 0 以外、またはコマンドが見つからない場合は失敗として扱う。

## 機能要件

1. `runner <task> <path...>` で、各パスに対しタスクを実行する
2. フォルダは再帰的にファイルへ展開する
3. タスクごとに対象拡張子でフィルタできる
4. プレースホルダでパスを組み立てられる（上表）
5. 1 ファイルずつ順次実行し、失敗したファイルを最後に一覧表示する
6. 実行前に出力ファイルの衝突をチェックし、上書き / 別名 / スキップ / キャンセルを選ばせる
7. `runner list` でタスク一覧を表示する
8. `runner install` / `runner uninstall` で Windows の「送る」ショートカット、macOS のクイックアクションを生成・削除する
9. `runner open-config` でユーザー設定フォルダを開く

## 既存タスクの移行対象

| 既存ファイル | 内容 | 移行方針 |
|---|---|---|
| `convert2mp4.bat` | `ffmpeg -i %1 %~n1.mp4` | テンプレート |
| `convert2mp3.bat` | 中身が convert2mp4 と同一（出力が `.mp4` になっているバグ） | テンプレート（mp3 出力に修正） |
| `convert2mp3_split.bat` | L/R チャンネルを別 mp3 に分割 | テンプレート（`output` を 2 つ宣言） |
| `convert2png.bat` | `ffmpeg -i %1 %~n1.png` | テンプレート |
| `convert2wav.bat` | 22050Hz / mono / pcm_s16le | テンプレート |
| `7zip_sha256.bat` | `7z h -scrcsha256` の結果を `.sha256` に保存 | テンプレート（`stdout` で保存） |
| `claude_transrate_jp.bat` | claude CLI でファイルを日本語訳し `_jp` 付きで保存 | テンプレート（タスク名を `claude_translate_jp` に修正） |
| `image_resize_1024.bat` | 画像を 1024 にリサイズして `output/` に保存 | テンプレート |
| `check_image_size.bat` | 画像サイズを拡張子別ハッシュカラーで表示 | Python スクリプト |
| `ffprobe-simple.bat` | codec / 解像度 / FPS をハッシュカラーで表示 | Python スクリプト |
| `docx2md.ps1` / `docx2txt.ps1` | docx を Markdown / テキストに変換 | Python スクリプト（標準ライブラリで zip/XML 読み取り） |

旧 bat の出力はカレントディレクトリ（`%~n1`）だったが、新ツールでは入力ファイルと同じフォルダに出力する。
