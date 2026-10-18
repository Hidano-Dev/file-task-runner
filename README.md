# file-task-runner

選択したファイル／フォルダ内の各ファイルに対して、定義済みのコマンドを 1 ファイルずつ順番に実行するツール。

Windows のエクスプローラー「送る」、macOS の Finder クイックアクションから呼び出すことを想定している。Linux は対象外。

要件と決定事項の詳細は [docs/initial-requirements.md](docs/initial-requirements.md) を参照。

## 動作要件

- Python 3.11 以上
- [pipx](https://pipx.pypa.io/) または [uv](https://docs.astral.sh/uv/)
- 各タスクが利用する外部ツール（ffmpeg / ffprobe, 7-Zip, claude CLI など）が PATH 上にあること

## インストール

```sh
pipx install git+https://github.com/Hidano-Dev/file-task-runner
# または
uv tool install git+https://github.com/Hidano-Dev/file-task-runner

runner install    # 「送る」/ クイックアクションを作成
```

開発時はリポジトリを clone して `pipx install -e .`（または `uv tool install -e .`）。

## 使い方

```
runner <task> <ファイル or フォルダ ...>
```

- フォルダは再帰的にファイルへ展開される
- タスクの `ext` に合わないファイルは無視される
- 1 ファイルずつ順に実行し、最後に成功 / 失敗 / スキップのサマリを表示して Enter 待ちになる
- 出力ファイルが既にある場合は、実行前に一覧を表示して `[O]上書き / [R]別名 / [S]スキップ / [C]キャンセル` を 1 回だけ聞く

| コマンド | 内容 |
|---|---|
| `runner <task> <path...>` | タスクを実行（`--on-exists overwrite\|rename\|skip\|cancel` で確認を省略、`--no-pause` で終了時に待たない） |
| `runner list` | タスク一覧 |
| `runner install` / `runner uninstall` | Windows「送る」/ macOS クイックアクションを作成・削除（タスクを追加したら `install` し直す） |
| `runner open-config` | ユーザー設定フォルダを開く |

## タスクを追加する

アプリ本体には触らず、ユーザー設定フォルダの `tasks/` に `*.toml` を置くだけで追加できる（`runner open-config` で開く）。組み込みタスクと同名なら上書きされる。

- Windows: `%APPDATA%\file-task-runner\tasks\`
- macOS: `~/Library/Application Support/file-task-runner/tasks/`

```toml
# tasks/my_tasks.toml
[convert2webm]
description = "WebM に変換"
cmd = ["ffmpeg", "-hide_banner", "-y", "-i", "{path}", "{output}"]
output = "{dir}/{stem}.webm"
ext = [".mp4", ".mov"]

[my_check]
script = "my_check.py"      # この toml と同じフォルダの my_check.py
pause = "on_error"
```

| キー | 内容 |
|---|---|
| `cmd` / `script` | どちらか必須。`cmd` はコマンドの配列（シェルを介さない）、`script` は Python スクリプト（`script.py <path> [<output>...]` として実行） |
| `output` | 出力ファイル（文字列または配列）。衝突チェックに使い、`cmd` では `{output}` / `{output[1]}` で参照 |
| `stdout` | 標準出力を保存するファイル |
| `ext` | 対象拡張子 |
| `os` | `["windows"]` / `["macos"]` |
| `pause` | `"always"`（既定）/ `"on_error"` / `"never"` |
| `description` | 一覧・メニューに表示する名前 |

プレースホルダ: `{path}` `{dir}` `{name}` `{stem}` `{ext}` `{output}`。

`script` からは `file_task_runner.colors`（ANSI 色、ハッシュカラー）を import できる。

## 組み込みタスク

| タスク | 内容 |
|---|---|
| `convert2mp4` / `convert2mp3` / `convert2png` / `convert2wav` | ffmpeg で変換（wav は 22050Hz / mono / pcm_s16le） |
| `convert2mp3_split` | L/R チャンネルを `_left.mp3` / `_right.mp3` に分割 |
| `7zip_sha256` | `7z h -scrcsha256` の結果を `.sha256` に保存 |
| `claude_translate_jp` | claude CLI で日本語訳し `_jp` 付きで保存 |
| `image_resize_1024` | 1024x1024 にリサイズして `output/` に保存 |
| `check_image_size` | 画像サイズを拡張子別の色で表示（2048 超は赤） |
| `ffprobe_simple` | codec / 解像度 / FPS / 音声有無を色付きで表示 |
| `docx2md` / `docx2txt` | docx を Markdown / テキストに変換 |

## 開発

```sh
uv run pytest
```

## ライセンス

MIT
