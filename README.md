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

### Basics

```console
decafe-timer 45m          # start a new timer, print one snapshot
decafe-timer 3h/5h        # start with 3h remaining out of a 5h total
decafe-timer              # show a snapshot if active; otherwise show ---
decafe-timer start        # start using the last duration (or 3h on first run)
decafe-timer run 45m      # start a new timer and watch it count down
decafe-timer run          # resume the live UI for an active timer
decafe-timer stack 5h     # add time to the remaining duration
decafe-timer +5h          # short form for stack 5h
decafe-timer clear        # clear the current timer (shows ---)
```

### Options

```console
decafe-timer --one-line        # use the single-line ASCII layout
decafe-timer --graph-only      # snapshot with the ASCII bar only
decafe-timer --bar-style blocks        # use the classic block bar
decafe-timer --bar-style counting-rod  # use the counting rod bar
decafe-timer --color=always    # force ANSI colors on
decafe-timer --color=never     # force ANSI colors off
decafe-timer --stack 5h        # add time to the remaining duration
decafe-timer --run 45m         # alias for `run` (start live countdown)
decafe-timer --run             # alias for `run` (resume live countdown)
decafe-timer --clear           # alias for `clear` (shows ---)
decafe-timer 0                 # clear using a zero duration
decafe-timer --version         # show the current version
```

### Notes

- `start`, `stack`, and `clear` are mutually exclusive in the same invocation.
- `stack` extends the remaining time without changing the duration or bar scale; it does not change the last-started duration.
- If the timer is expired, `stack` starts a new timer using the last-started duration (or 3h).
- When the remaining time exceeds the bar scale, a `>>` suffix is shown at the end of the bar.

## License

`decafe-timer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
