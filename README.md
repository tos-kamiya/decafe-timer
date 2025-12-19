# decafe-timer

[![PyPI - Version](https://img.shields.io/pypi/v/decafe-timer.svg)](https://pypi.org/project/decafe-timer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/decafe-timer.svg)](https://pypi.org/project/decafe-timer)

-----

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

```console
pip install decafe-timer
```

## Usage

The CLI revolves around three ideas:

1. Passing a duration creates a new cooldown; omitting it resumes whatever is already running. You can use single durations (`2h`, `15m30s`, `0:45:00`) or a remaining/total pair like `3h/5h` (spaces around `/` are allowed, and mixed formats like `3h/4:50:00` work too).
2. `--run` decides whether to keep the Rich UI updating until the cooldown expires. Without `--run`, the command prints the current status once and exits.
3. Style flags pick the ASCII layout: default multi-line (`Remaining` / `Expires at` + bar), `--one-line` (`HH:MM:SS 𝅛𝅛𝅛𝅚𝅚…`), or `--graph-only` (bar only, no brackets). They’re accepted on any invocation; when paired with `--run`, the live updates switch to that ASCII style instead of the Rich progress bar. Snapshots print `[You may drink coffee now.]` once the timer finishes.

```console
decafe-timer 45m          # start a new timer, print one snapshot
decafe-timer 3h/5h        # start with 3h remaining out of a 5h total
decafe-timer              # resume the latest timer, one snapshot
decafe-timer --run 45m    # start a new timer and watch it count down
decafe-timer --run        # resume the Rich UI for an active timer
decafe-timer --run --one-line 10m  # live ASCII updates instead of Rich
decafe-timer --graph-only # snapshot with the ASCII bar only
decafe-timer --version    # show the current version
```

## License

`decafe-timer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
