# decafe-timer (日本語版)

[![PyPI - Version](https://img.shields.io/pypi/v/decafe-timer.svg)](https://pypi.org/project/decafe-timer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/decafe-timer.svg)](https://pypi.org/project/decafe-timer)

コーヒーブレイクやカフェイン摂取の間隔を管理する、軽量なCLIクールダウンタイマーです。
カフェインを摂りすぎていないか、依存になっていないか気になる方のために作りました。

![decafe-timer screenshot](https://raw.githubusercontent.com/tos-kamiya/decafe-timer/main/images/shot1.png)

## インストール

```console
pipx install decafe-timer
```

## 使い方

### 基本

```console
decafe-timer 45m          # 新しいタイマーを始めてスナップショットを 1 回表示
decafe-timer 3h/5h        # 3 時間残り / 5 時間のタイマーで開始
decafe-timer              # 保存済みタイマーを再開し、スナップショットを 1 回表示
decafe-timer run 45m      # 新しいタイマーを始め、カウントダウンを表示し続ける
decafe-timer run          # 進行中のタイマーをライブ表示で再開
decafe-timer clear        # タイマーを消去して `---` 表示にする
```

### オプション

```console
decafe-timer --one-line        # ASCII 1 行表示を使う
decafe-timer --graph-only      # ASCII バーのみのスナップショットを表示
decafe-timer --bar-style blocks        # 以前のブロック表示を使う
decafe-timer --bar-style counting-rod  # Counting Rod Numerals のバーを使う
decafe-timer --color=always    # TTY 以外でも ANSI を強制
decafe-timer --color=never     # ANSI を無効化する
decafe-timer --run 45m         # `run` の別名 (カウントダウンを表示し続ける)
decafe-timer --run             # `run` の別名 (ライブ表示で再開)
decafe-timer --clear           # `clear` の別名 (`---` 表示にする)
decafe-timer 0                 # 0 指定でタイマーを消去する
decafe-timer --version         # バージョンを表示
```

## ライセンス

`decafe-timer` は [MIT](https://spdx.org/licenses/MIT.html) ライセンスで配布されています。
