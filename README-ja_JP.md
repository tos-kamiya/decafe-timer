# decafe-timer (日本語版)

[![PyPI - Version](https://img.shields.io/pypi/v/decafe-timer.svg)](https://pypi.org/project/decafe-timer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/decafe-timer.svg)](https://pypi.org/project/decafe-timer)

体内のカフェインが抜けるまでの時間を管理する、軽量なCLIタイマーです。
カフェインを摂りすぎていないか気になる方のために作りました。

![decafe-timer screenshot](https://raw.githubusercontent.com/tos-kamiya/decafe-timer/main/images/shot1.png)

## インストール

```console
pipx install decafe-timer
```

## 使い方

モデルの考え方はシンプルです。

- メモリ（`mem`）はバーの最大長で、`intake` の既定量になります。
- 残り時間は、体内に残っているカフェイン量として扱います。
- `intake` で残量を追加し、時間経過とともにバーが縮みます。
- 0 になる前に `intake` すると `mem` を超えるため、バー末尾に `>>` が表示されます。

### 基本

```console
decafe-timer              # タイマーがあればスナップショットを 1 回表示、なければ ---
decafe-timer mem 3h       # バーの基準時間（メモリ）を設定する
decafe-timer mem          # 現在のメモリを表示する
decafe-timer intake 45m   # カフェイン摂取量を追加する（未設定なら新規開始）
decafe-timer intake       # メモリと同量を追加する
decafe-timer +5h          # intake 5h の短縮形
decafe-timer clear        # タイマーを消去して `---` 表示にする
decafe-timer run          # 進行中のタイマーをライブ表示で再開
decafe-timer config       # メモリ・バー・レイアウトを表示する
```

### オプション

```console
decafe-timer --layout one-line        # ASCII 1 行表示を使う（一時的）
decafe-timer --layout graph-only      # ASCII バーのみのスナップショットを表示（一時的）
decafe-timer --one-line               # --layout one-line の旧エイリアス（一時的）
decafe-timer --graph-only             # --layout graph-only の旧エイリアス（一時的）
decafe-timer --bar-style blocks        # 以前のブロック表示を使う（一時的）
decafe-timer --bar-style counting-rod  # Counting Rod Numerals のバーを使う（一時的）
decafe-timer --color=always    # TTY 以外でも ANSI を強制
decafe-timer --color=never     # ANSI を無効化する
decafe-timer --version         # バージョンを表示
```

### 設定の保存

```console
decafe-timer config --bar-style blocks       # 既定のバー表示を保存
decafe-timer config --layout one-line        # 既定のレイアウトを保存
decafe-timer config --layout graph-only      # 既定のレイアウトを保存
decafe-timer config --one-line               # 旧レイアウト設定（保存）
decafe-timer config --graph-only             # 旧レイアウト設定（保存）
```

### メモ

- `run` / `intake` / `mem` / `config` / `clear` は同時に使えません。
- `intake` は残量だけを増やし、バーの基準長は変えません。
- 期限切れ後の `intake` は新規開始になります。
- `mem` が未設定の場合は 3h を使います。
- `config --bar-style` と `config --layout` は既定値として保存されます。
- `--bar-style` / `--layout` / `--one-line` / `--graph-only` は一時的に反映されます。
- 残量がバーの基準より長い場合は、末尾に `>>` が表示されます。
- `decafe-timer` は状態表示のみ。`decafe-timer 45m` はエラーです。

## ライセンス

`decafe-timer` は [MIT](https://spdx.org/licenses/MIT.html) ライセンスで配布されています。
