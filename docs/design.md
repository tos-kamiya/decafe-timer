# decafe-timer design notes

## Timer states

- active: a timer is running (finish_at in the future).
- expired: the stored finish_at is in the past (no auto-clear).
- cleared: no active timer (finish_at/duration_sec removed).

## Clear command

- Add a CLI command `clear` to explicitly remove the current timer.
- Clearing removes `finish_at` and `duration_sec` from the state file.
- `last_finished` can remain as optional history.

## Unset display

- When there is no active timer (cleared), show `---`.
- This avoids a persistent "you may drink coffee" message in always-on displays.

## State persistence

- `finish_at` is an absolute timestamp, so it does not encode the original duration.
- `duration_sec` is required to render the bar scale.
- Therefore, keep `duration_sec` alongside `finish_at` for active timers.
- If future designs want to compute duration, store `start_at` instead.

## Module structure

- `src/decafe_timer/cli.py`: CLI argument parsing and normalization into a `CliRequest` (aliases for `run`/`clear`, duration string assembly, conflict checks).
- `src/decafe_timer/duration.py`: Duration parsing helpers for `HH:MM:SS`, `AhBmCs`, and `remaining/total` forms.
- `src/decafe_timer/main.py`: Timer lifecycle, state persistence, rendering, and CLI entry point wiring.

## CLI expectations

- `decafe-timer`: show active/expired status if a timer exists; otherwise show `---`.
- `decafe-timer clear`: remove the current timer, then show `---` (or a short confirmation).
