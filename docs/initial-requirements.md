# 初期要件（たたき台）

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
- 実装言語: Python 3
- 処理定義: `tasks.toml` にコマンドテンプレートとして宣言的に記述。複雑な処理のみ Python スクリプトで書く
- 呼び出し口: Windows は「送る」、macOS は Finder クイックアクション
- tkinter によるファイル選択 UI は廃止（OS 側の選択 UI に任せる）
- 既存の `sequential_execution` フォルダはそのまま残す

## 機能要件（案）

1. `runner <task> <path...>` で、各パスに対しタスクを実行する
2. フォルダは再帰的にファイルへ展開する
3. タスクごとに対象拡張子でフィルタできる
4. プレースホルダ: `{path}`（フルパス）、`{dir}`（親ディレクトリ）、`{name}`（ファイル名）、`{stem}`（拡張子なし名）、`{ext}`（拡張子）
5. 1 ファイルずつ順次実行し、失敗したファイルを最後に一覧表示する
6. Windows 用「送る」ショートカットを `tasks.toml` から生成するコマンド
7. macOS 用クイックアクションのセットアップ手段

## 未決事項

- 配布方法（pip / pipx / リポジトリを clone して使う）
- 並列実行の要否
- 実行時のコンソール表示（ウィンドウを閉じずに結果を見せる等）
- 出力先の既存ファイルがある場合の扱い
- ライセンス

## 既存タスクの移行対象

| 既存ファイル | 内容 | 移行方針 |
|---|---|---|
| `convert2mp4.bat` | `ffmpeg -i %1 %~n1.mp4` | テンプレート |
| `convert2mp3.bat` | 中身が convert2mp4 と同一（出力が `.mp4` になっているバグ） | テンプレート（mp3 出力に修正） |
| `convert2mp3_split.bat` | L/R チャンネルを別 mp3 に分割 | テンプレート |
| `convert2png.bat` | `ffmpeg -i %1 %~n1.png` | テンプレート |
| `convert2wav.bat` | 22050Hz / mono / pcm_s16le | テンプレート |
| `7zip_sha256.bat` | `7z h -scrcsha256` の結果を `.sha256` に保存 | テンプレート（stdout のファイル保存が必要） |
| `claude_transrate_jp.bat` | claude CLI でファイルを日本語訳し `_jp` 付きで保存 | テンプレート |
| `image_resize_1024.bat` | 画像を 1024 にリサイズ | Python スクリプト or テンプレート |
| `check_image_size.bat` | 画像サイズを拡張子別ハッシュカラーで表示 | Python スクリプト |
| `ffprobe-simple.bat` | codec / 解像度 / FPS をハッシュカラーで表示 | Python スクリプト |
| `docx2md.ps1` / `docx2txt.ps1` | docx を Markdown / テキストに変換 | Python スクリプト（標準ライブラリで zip/XML 読み取り） |
| `MotionBuilderAutoReduction.bat` | MotionBuilder で FBX をリダクション | Windows 専用タスクとして扱う（OS 指定可能にするか要検討） |
