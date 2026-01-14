# decafe-timer

[![PyPI - Version](https://img.shields.io/pypi/v/decafe-timer.svg)](https://pypi.org/project/decafe-timer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/decafe-timer.svg)](https://pypi.org/project/decafe-timer)

A lightweight CLI cooldown timer for coffee breaks and caffeine tracking.
It was created for people who worry about taking too much caffeine and becoming dependent on it.

![decafe-timer screenshot](https://raw.githubusercontent.com/tos-kamiya/decafe-timer/main/images/shot1.png)

## Installation

```console
pipx install decafe-timer
```

## Usage

The CLI follows a simple story:

1. Provide a duration to set a timer. You can use single durations (`2h`, `15m30s`, `0:45:00`) or a remaining/total pair like `3h/5h` (spaces around `/` are allowed, and mixed formats like `3h/4:50:00` work too).
2. Once the timer expires, snapshots show `[You may drink coffee now.]`.
3. `clear` removes the stored timer so idle displays show `---`.
4. `--run` keeps the display updating until the cooldown expires; without it, a snapshot is printed once.
5. Style flags customize the ASCII layout.
   - `--one-line` uses `HH:MM:SS ✕ ✕ ✕ …`.
   - `--graph-only` prints just the bar.
   - `--bar-style` swaps the bar characters (`greek-cross` default, `counting-rod`, or `blocks` for the previous look).
6. Color output is controlled separately.
   - ANSI is auto-enabled on TTYs.
   - `--color=always` forces ANSI on; `--color=never` forces it off (applies to both live and snapshot output).

```console
decafe-timer 45m          # start a new timer, print one snapshot
decafe-timer 3h/5h        # start with 3h remaining out of a 5h total
decafe-timer              # resume the latest timer, one snapshot
decafe-timer --run 45m    # start a new timer and watch it count down
decafe-timer --run        # resume the live UI for an active timer
decafe-timer --run --one-line 10m  # live ASCII updates on one line
decafe-timer --bar-style blocks   # use the classic block bar
decafe-timer --bar-style counting-rod  # use the counting rod bar
decafe-timer --graph-only # snapshot with the ASCII bar only
decafe-timer clear        # clear the current timer (shows ---)
decafe-timer --version    # show the current version
```

## License

`decafe-timer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
