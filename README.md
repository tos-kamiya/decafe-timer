# decafe-timer

[![PyPI - Version](https://img.shields.io/pypi/v/decafe-timer.svg)](https://pypi.org/project/decafe-timer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/decafe-timer.svg)](https://pypi.org/project/decafe-timer)

A lightweight CLI timer for caffeine clearance and intake tracking.
It was created for people who want to pace caffeine and avoid overuse.

Note: The command structure changed significantly in 0.9.0.

![decafe-timer screenshot](https://raw.githubusercontent.com/tos-kamiya/decafe-timer/main/images/shot1.png)

## Installation

```console
pipx install decafe-timer
```

## Usage

The model is intentionally simple:

- Memory (`mem`) is the bar's maximum length and the default intake size.
- Remaining time is treated as the amount of caffeine still in your body.
- `intake` adds to the remaining amount; the bar shrinks as it clears.
- If you intake again before it reaches zero, remaining can exceed `mem` and the bar shows `>>`.

### Basics

```console
decafe-timer              # show a snapshot if active; otherwise show ---
decafe-timer mem 3h       # set bar memory (default intake size)
decafe-timer mem          # show current bar memory
decafe-timer intake 45m   # add intake time (starts a new timer if none)
decafe-timer intake       # add the memory amount
decafe-timer +5h          # short form for intake 5h
decafe-timer clear        # clear the current timer (shows ---)
decafe-timer run          # resume the live UI for an active timer
decafe-timer config       # show memory + bar style + layout
```

### Options

```console
decafe-timer --layout one-line        # use the single-line ASCII layout (temporary)
decafe-timer --layout graph-only      # snapshot with the ASCII bar only (temporary)
decafe-timer --one-line               # legacy alias for --layout one-line (temporary)
decafe-timer --graph-only             # legacy alias for --layout graph-only (temporary)
decafe-timer --bar-style blocks        # use the classic block bar (temporary)
decafe-timer --bar-style counting-rod  # use the counting rod bar (temporary)
decafe-timer --color=always    # force ANSI colors on
decafe-timer --color=never     # force ANSI colors off
decafe-timer --version         # show the current version
```

### Configuration

```console
decafe-timer config --bar-style blocks       # save the default bar style
decafe-timer config --layout one-line        # save the default layout
decafe-timer config --layout graph-only      # save the default layout
decafe-timer config --one-line               # legacy layout setter (saves default)
decafe-timer config --graph-only             # legacy layout setter (saves default)
```

### Notes

- `run`, `intake`, `mem`, `config`, and `clear` are mutually exclusive in the same invocation.
- `intake` extends the remaining time without changing the bar scale.
- If the timer is expired, `intake` starts a new timer from now.
- `mem` defaults to 3h when not yet set.
- `--bar-style` and `--layout` are temporary unless used with `config`.
- When the remaining time exceeds the bar scale, a `>>` suffix is shown at the end of the bar.
- `decafe-timer` shows status without changing state; `decafe-timer 45m` is invalid.

## License

`decafe-timer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
