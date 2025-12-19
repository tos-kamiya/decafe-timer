# decafe-timer (日本語版)

[![PyPI - Version](https://img.shields.io/pypi/v/decafe-timer.svg)](https://pypi.org/project/decafe-timer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/decafe-timer.svg)](https://pypi.org/project/decafe-timer)

-----

## 目次

- [インストール](#インストール)
- [使い方](#使い方)
- [ライセンス](#ライセンス)

## インストール

```console
pip install decafe-timer
```

## 使い方

CLI の基本は次の 3 点です。

1. `2h`、`15m30s`、`0:45:00` のように長さを渡すと新しいクールダウンが作成され、引数なしなら保存済みのタイマーを再開します。
2. `--run` はリッチな進行状況を最後まで表示し続けるかどうかを決めます。付けなければ現在の状態を 1 回だけ表示して終了します。
3. スタイル指定で ASCII レイアウトを切り替えられます。デフォルトは複数行 (`Remaining` / `Expires at` + バー)、`--one-line` は `HH:MM:SS 𝅛𝅛𝅚𝅚…` 表記、`--graph-only` は時間表示なしのバーのみ。どのモードでも指定できます。`--run` と併用した場合はリッチ Progress の代わりに指定した ASCII 表示でライブ更新されます。スナップショット表示ではクールダウン完了時に `[You may drink coffee now.]` が表示されます。

```console
decafe-timer 45m          # 新しいタイマーを始めてスナップショットを 1 回表示
decafe-timer              # 保存済みタイマーを再開し、スナップショットを 1 回表示
decafe-timer --run 45m    # 新しいタイマーを始め、カウントダウンを表示し続ける
decafe-timer --run        # 進行中のタイマーをリッチ UI で再開
decafe-timer --run --one-line 10m  # リッチ UI の代わりに ASCII でライブ更新
decafe-timer --graph-only # ASCII バーのみのスナップショットを表示
```

## ライセンス

`decafe-timer` は [MIT](https://spdx.org/licenses/MIT.html) ライセンスで配布されています。
