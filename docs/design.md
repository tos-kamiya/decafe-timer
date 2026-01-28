# decafe-timer design notes

## Timer states

- active: a timer is running (`finish_at` in the future).
- expired: a timer exists and has reached zero (`finish_at` in the past); show an expired label and a "you may drink coffee" message.
- cleared: no active timer (`finish_at` removed, `---` shown).

## Clear command

- The `clear` command is implemented (`decafe-timer clear`).
- Clearing removes `finish_at` from the state file.

## Unset display

- When there is no active timer (cleared), show `---`.
- This avoids a persistent "you may drink coffee" message in always-on displays.

## State persistence

- `finish_at` is an absolute timestamp; remaining time is computed as `finish_at - now`.
- `mem_sec` stores the display memory (bar maximum and default intake amount).
- `bar_style`, `one_line`, and `graph_only` are stored when saved via `config`.
- If no `mem_sec` exists, default to 3h.

## Memory defaults

- `mem` sets the display memory for the bar and the default intake amount.

## Intake (time add)

- `intake` adds time to the remaining duration (e.g., remaining 2h + intake 5h = 7h remaining).
- If the timer is expired or cleared, `intake` starts a new timer from now.
- If `intake` is called without a duration, it uses `mem_sec`.

## Module structure

- `src/decafe_timer/cli.py`: CLI argument parsing and normalization into a `CliRequest` (subcommand parsing, conflict checks).
- `src/decafe_timer/duration.py`: Duration parsing helpers for `HH:MM:SS`, `AhBmCs`, and `remaining/total` forms.
- `src/decafe_timer/main.py`: Timer lifecycle, state persistence, and entry point wiring.
- `src/decafe_timer/render.py`: Bar rendering styles, ANSI color handling, and overflow suffix logic.

## CLI expectations

- `decafe-timer`: show a snapshot status if a timer exists; otherwise `---`.
- `decafe-timer run`: live updating mode with a shrinking bar.
- `decafe-timer clear`: remove the current timer, then show `---`.
- `decafe-timer intake [duration]`: add time to the remaining duration; if duration omitted, use `mem_sec`.
- `decafe-timer +5h`: same as `intake 5h`.
- `decafe-timer mem [duration]`: show or set the display memory for the bar.
- `decafe-timer config`: show saved memory + bar style + layout; `config --bar-style` and `config --layout` persist settings.
- `decafe-timer 3h`: invalid; duration requires `intake` or `+duration`.
- `run` / `intake` / `mem` / `config` / `clear` are mutually exclusive.
- `intake 5h` and `+5h` cannot be combined in the same invocation.
- Output formats:
  - default: Remaining + Clears at + bar
  - `--layout one-line` (or `--one-line`): `HH:MM:SS` + bar
  - `--layout graph-only` (or `--graph-only`): bar only
- Bar styles: `greek-cross` (default), `counting-rod`, `blocks`.
- ANSI colors are enabled by default when stdout is a TTY; control via `--color`.
- `--bar-style` / `--layout` / `--one-line` / `--graph-only` are temporary unless used with `config`.

## Bar rendering

- Bar styles are defined as a dataclass with a `render(ratio, is_overflow, ansi)` function.
- Each `render` function references its style constants (segments, overflow suffix) internally.
- When remaining time exceeds the bar scale, append a style-specific overflow suffix (default: `>>`).
