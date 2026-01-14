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

CLI の流れは次のとおりです。

1. 期間を渡すとタイマーがセットされます。`2h`、`15m30s`、`0:45:00` のような単一指定に加えて、残り/総時間のペア (`3h/5h` など、スラッシュ前後に空白可) も使えます。
2. 期限を過ぎたスナップショットでは `[You may drink coffee now.]` が表示されます。
3. `clear` を使うと保存済みのタイマーを消去し、未設定時の表示を `---` にできます。
4. `--run` はライブ表示を最後まで更新し続けるかどうかを決めます。付けなければ現在の状態を 1 回だけ表示して終了します。
5. スタイル指定で ASCII 表示を切り替えられます。
   - `--one-line` は `HH:MM:SS ✕ ✕ ✕ …` 表記。
   - `--graph-only` はバーのみ。
   - `--bar-style` でバーの文字を切り替えられます (デフォルトは `greek-cross`、`counting-rod`、以前のブロック表示は `blocks`)。
6. 色出力は別項目で制御します。
   - ANSI は TTY のとき自動で有効化されます。
   - `--color=always` で強制オン、`--color=never` で強制オフできます (ライブ/スナップショット共通)。

```console
decafe-timer 45m          # 新しいタイマーを始めてスナップショットを 1 回表示
decafe-timer 3h/5h        # 3 時間残り / 5 時間のタイマーで開始
decafe-timer              # 保存済みタイマーを再開し、スナップショットを 1 回表示
decafe-timer --run 45m    # 新しいタイマーを始め、カウントダウンを表示し続ける
decafe-timer --run        # 進行中のタイマーをライブ表示で再開
decafe-timer --run --one-line 10m  # ASCII 1 行表示でライブ更新
decafe-timer --bar-style blocks   # 以前のブロック表示を使う
decafe-timer --bar-style counting-rod  # Counting Rod Numerals のバーを使う
decafe-timer --graph-only # ASCII バーのみのスナップショットを表示
decafe-timer clear        # タイマーを消去して `---` 表示にする
decafe-timer --color=always # TTY 以外でも ANSI を強制
```

## ライセンス

`decafe-timer` は [MIT](https://spdx.org/licenses/MIT.html) ライセンスで配布されています。
