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
- `duration_sec` is stored alongside `finish_at` to render the bar scale.
- `last_finished` stores the most recently completed timer (`finish_at`, `duration_sec`).

## Module structure

- `src/decafe_timer/cli.py`: CLI argument parsing and normalization into a `CliRequest` (aliases for `run`/`clear`, duration string assembly, conflict checks).
- `src/decafe_timer/duration.py`: Duration parsing helpers for `HH:MM:SS`, `AhBmCs`, and `remaining/total` forms.
- `src/decafe_timer/main.py`: Timer lifecycle, state persistence, bar rendering (3 styles), and entry point wiring.

## CLI expectations

- `decafe-timer`: show a snapshot status if a timer exists; otherwise `---`.
- `decafe-timer --run` (or `run`): live updating mode with a shrinking bar.
- `decafe-timer clear` / `--clear` / `0`: remove the current timer, then show `---`.
- Output formats:
  - default: Remaining + Expires at + bar
  - `--one-line`: `HH:MM:SS` + bar
  - `--graph-only`: bar only
- Bar styles: `greek-cross` (default), `counting-rod`, `blocks`.
- ANSI colors are enabled by default when stdout is a TTY; control via `--color`.
