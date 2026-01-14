# AGENTS

## Repository Overview
- Python package providing a "coffee cooldown" countdown timer to help limit coffee intake; exposes a CLI entry point `decafe-timer` defined in `pyproject.toml`.
- Core logic lives in `src/decafe_timer/main.py`, which persists state with `appdirs` (`timer_state.json` under the user cache dir) and renders a shrinking Rich progress bar while the cooldown is active.
- `aichat/20251202.md` captures the original user conversation/spec: countdown timer, 1-minute persistence, resume across restarts, preference for "Expires at" messaging, Rich-based UI, and a bar that starts full (red) and shortens over time.

## How To Run
- Install deps (system Python 3.10+): `pip install -e .` (uses Hatch build backend; dependencies are `appdirs` and `rich`).
- Start a cooldown: `decafe-timer --start 02:00:00` (or `python -m decafe_timer --start 02:00:00`).
- Resume an existing timer (after restart or interruption): run `decafe-timer` with no args; it reads `STATE_FILE` in the cache dir and resumes the Rich loop.

## Implementation Notes
- `save_state()`/`load_state()` serialize `finish_at`, `duration_sec`, and `last_saved_at` to JSON; the persisted finish time ensures elapsed time during OS restarts is accounted for.
- `run_timer_loop()` drives the Rich `Progress` widget. `total` equals the original duration (seconds) and `completed` is set to the remaining seconds so the bar shrinks to zero; the loop updates once per second and re-saves once per minute.
- When the timer reaches zero the cache file is deleted and `console.print` announces `Cooldown expired! ☕ You may drink coffee now.`

## Testing & Tooling
- No automated tests yet (`tests/` only has an empty `__init__.py`).
- Type checking via `hatch run types:check` (mypy) is configured but optional.

## Future Agent Tips
- Respect the cached state format if you extend features (other tools may rely on `finish_at` + `duration_sec`).
- Rich configuration lives entirely in `run_timer_loop`; UI tweaks (colors, columns, new text) should stay within that block.
- Before adding new dependencies, update both `pyproject.toml` and `README.md` and consider whether the CLI output must remain bilingual (the current strings mix English UI with Japanese comments).
- Follow the current implementation for state persistence (uses `appdirs` user cache dir); do not relocate cache files to the project root unless explicitly requested.
- Use semantic commit messages (`feat: ...`, `fix: ...`, etc.) when committing changes.
- Testing (including launching the Python interpreter) is handled manually by humans; describe what should be run, but do not execute tests yourself.
