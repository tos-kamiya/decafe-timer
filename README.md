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

Start a new cooldown by passing the duration as a positional argument. Durations accept either `HH:MM:SS` or a shorthand like `2h30m`, `15m`, or `45s`.

```console
decafe-timer 2h
```

Running the command without arguments resumes any active timer (expired timers are cleaned up automatically).

## License

`decafe-timer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
