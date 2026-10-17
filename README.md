# file-task-runner

選択したファイル／フォルダ内の各ファイルに対して、定義済みのコマンドを 1 ファイルずつ順番に実行するツール。

Windows のエクスプローラー「送る」、macOS の Finder クイックアクションから呼び出すことを想定している。

> **Status:** 開発開始前（要件整理中）。要件のたたき台は [docs/initial-requirements.md](docs/initial-requirements.md) を参照。

## コンセプト

処理内容を OS 非依存のコマンドテンプレートとして `tasks.toml` に定義し、共通のランナーがそれを実行する。

```toml
# tasks.toml（イメージ）
[convert2mp4]
cmd = ["ffmpeg", "-i", "{path}", "{dir}/{stem}.mp4"]

[convert2wav]
cmd = ["ffmpeg", "-i", "{path}", "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", "{dir}/{stem}.wav", "-y"]
ext = [".mp4", ".mov", ".wav"]

[check_image_size]
script = "tasks/check_image_size.py"
```

```
runner <task名> <ファイル or フォルダ ...>
```

- フォルダが渡されたら再帰的にファイルを展開する
- `ext` で対象拡張子を絞り込む
- テンプレートのプレースホルダ（`{path}` `{dir}` `{stem}` など）を埋めて 1 ファイルずつ実行する

## 呼び出し口

| OS | 呼び出し方 |
|---|---|
| Windows | 「送る」（`shell:sendto`）に `runner <task名>` のショートカットを配置。`tasks.toml` から自動生成する |
| macOS | Finder クイックアクション（Automator「シェルスクリプトを実行」）からランナーを呼ぶ |

Linux は対象外。

## 動作要件（予定）

- Python 3
- 各タスクが利用する外部ツール（ffmpeg, 7-Zip, claude CLI など）
