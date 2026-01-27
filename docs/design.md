# decafe-timer design notes

## Timer states

- active: a timer is running (`finish_at` in the future).
- expired: the stored `finish_at` is in the past (no auto-clear; an expired message is printed when checked).
- cleared: no active timer (`finish_at`/`duration_sec` removed, `---` shown).

## Clear command

- The `clear` command is implemented (`decafe-timer clear`, `--clear`, or `0`).
- Clearing removes `finish_at` and `duration_sec` from the state file.
- `last_finished` is preserved as optional history.

## Unset display

- When there is no active timer (cleared), show `---`.
- This avoids a persistent "you may drink coffee" message in always-on displays.

## State persistence

- `finish_at` is an absolute timestamp; it does not encode the original duration.
- `duration_sec` stores the base duration from start (not changed by stack).
- `last_finished` stores the most recently completed timer (`finish_at`, `duration_sec`).
- `last_duration_sec` stores the most recently started duration for `start` defaults.
  - This value is updated only on `start` (not on `stack`).
  - If no active timer exists, the last duration is used; if missing, default to 3h.

## Start defaults

- `start` with no duration uses `last_duration_sec` when available, else defaults to 3h.
- This mirrors the "resume last used duration" behavior even when there is no active timer.

## Stack (time add)

- `stack` adds time to the remaining duration (e.g., remaining 2h + stack 5h = 7h remaining).
- `duration_sec` is unchanged, and the bar scale is always based on `duration_sec`.
- `stack` does not update `last_duration_sec`.
- If the timer is expired, `stack` behaves as a new start using the last-started duration (or 3h).

## Module structure

- `src/decafe_timer/cli.py`: CLI argument parsing and normalization into a `CliRequest` (aliases for `run`/`clear`, duration string assembly, conflict checks).
- `src/decafe_timer/duration.py`: Duration parsing helpers for `HH:MM:SS`, `AhBmCs`, and `remaining/total` forms.
- `src/decafe_timer/main.py`: Timer lifecycle, state persistence, and entry point wiring.
- `src/decafe_timer/render.py`: Bar rendering styles, ANSI color handling, and overflow suffix logic.

## CLI expectations

- `decafe-timer`: show a snapshot status if a timer exists; otherwise `---`.
- `decafe-timer --run` (or `run`): live updating mode with a shrinking bar.
- `decafe-timer clear` / `--clear` / `0`: remove the current timer, then show `---`.
- `decafe-timer start [duration]`: start a new timer; if duration omitted, use `last_duration_sec` or 3h.
- `decafe-timer --stack 5h` / `decafe-timer stack 5h` / `decafe-timer +5h`: add time to the remaining duration.
- `start` / `stack` / `clear` are mutually exclusive.
- `--stack` and `+5h` cannot be combined in the same invocation.
- Output formats:
  - default: Remaining + Expires at + bar
  - `--one-line`: `HH:MM:SS` + bar
  - `--graph-only`: bar only
- Bar styles: `greek-cross` (default), `counting-rod`, `blocks`.
- ANSI colors are enabled by default when stdout is a TTY; control via `--color`.

## Bar rendering

- Bar styles are defined as a dataclass with a `render(ratio, is_overflow, ansi)` function.
- Each `render` function references its style constants (segments, overflow suffix) internally.
- When remaining time exceeds the bar scale, append a style-specific overflow suffix (default: `>>`).
