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

Running `decafe-timer` with no options now prints a **single snapshot** of the current cooldown status—remaining time plus the ASCII bar—and exits immediately. This makes it perfect for status bars or `watch` loops:

```console
decafe-timer
decafe-timer --graph-only  # bar only
```

(Both snapshot modes display `[You may drink coffee now.]` once the cooldown finishes so the output width stays consistent.)

To start/resume the interactive Rich UI that keeps updating until the cooldown expires, pass `--run` in front of any duration or state-display options. Durations accept either `HH:MM:SS` or a shorthand like `2h30m`, `15m`, or `45s`.

```console
decafe-timer --run 2h
decafe-timer --run        # resume an active timer
```

`--one-line` / `--graph-only` are for the snapshot mode only; omit them when running with `--run` so the progress bar can render until completion.

## License

`decafe-timer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
