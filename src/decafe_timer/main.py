import hashlib
import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .cli import CliRequest, normalize_cli_request, parse_cli_args
from .duration import (
    INVALID_DURATION_MESSAGE,
    duration_to_seconds,
    parse_duration,
    parse_simple_duration,
)
from .render import (
    BAR_STYLE_GREEK_CROSS,
    format_remaining,
    render_live_line,
    render_snapshot_line,
    visible_length,
)

APP_NAME = "coffee_timer"
APP_AUTHOR = "tos-kamiya"


def _cache_dir() -> Path:
    from appdirs import user_cache_dir

    return Path(user_cache_dir(APP_NAME, APP_AUTHOR))


def _state_file() -> Path:
    return _cache_dir() / "timer_state.json"

EXPIRED_MESSAGES = [
    "Cooldown expired! ☕ You may drink coffee now.",
    # Gentle encouragement
    "Your break is over -- enjoy your coffee, gently.",
    "You’ve waited well. Treat yourself to a warm cup.",
    "Time’s up. A calm sip is yours.",
    # Soft, calming tone
    "Your coffee time has arrived -- relax and enjoy.",
    "A warm cup is waiting for you.",
    "The timer’s done. Brew a moment of comfort.",
    "Ease back in. Coffee is ready when you are.",
    # Light humor
    "Permission granted: caffeination may proceed.",
    "Coffee mode unlocked. Use wisely.",
    "Alert: Bean protocol complete.",
    # Gentle behavior support
    "If you choose to, a small cup won’t hurt now.",
    "Ready when you are. Keep listening to your body.",
    "You did the wait. Now choose what feels right.",
]
NO_ACTIVE_TIMER_MESSAGE = "---"
BROKEN_STATE_MESSAGE = "State file is invalid; ignoring it."

DEFAULT_DURATION_SEC = duration_to_seconds(3, 0, 0)


def _select_expired_message(
    finish_at: Optional[datetime],
    duration_sec: Optional[int],
) -> str:
    if finish_at is None or duration_sec is None:
        return random.choice(EXPIRED_MESSAGES)
    key = f"{finish_at.isoformat()}-{duration_sec}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    index = int.from_bytes(digest[:8], "big") % len(EXPIRED_MESSAGES)
    return EXPIRED_MESSAGES[index]


def _schedule_timer_seconds(
    remaining_sec: int, total_sec: int, *, bar_scale_sec: Optional[int] = None
):
    """Create a new timer from seconds, persist it, and return (finish_at, duration_sec)."""
    if remaining_sec <= 0 or total_sec <= 0:
        raise ValueError("Duration must be positive.")
    finish_at = datetime.now() + timedelta(seconds=remaining_sec)
    save_state(finish_at, total_sec, bar_scale_sec=bar_scale_sec)
    return finish_at, total_sec


def _schedule_timer(hours: int, minutes: int, seconds: int):
    """Create a new timer, persist it, and return (finish_at, duration_sec)."""
    duration_sec = duration_to_seconds(hours, minutes, seconds)
    return _schedule_timer_seconds(duration_sec, duration_sec)


# ------------------------------
# Persistence helpers
# ------------------------------
_broken_state_notice_shown = False


def _warn_broken_state():
    global _broken_state_notice_shown
    if _broken_state_notice_shown:
        return
    print(BROKEN_STATE_MESSAGE)
    _broken_state_notice_shown = True


def _read_state_payload():
    state_file = _state_file()
    if not state_file.exists():
        return {}
    try:
        text = state_file.read_text()
    except OSError:
        _warn_broken_state()
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        _warn_broken_state()
        return {}
    if not isinstance(data, dict):
        _warn_broken_state()
        return {}
    return data


def _write_state_payload(payload: dict):
    state_file = _state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_file.with_name(f"{state_file.name}.tmp")
    tmp_path.write_text(json.dumps(payload))
    tmp_path.replace(state_file)


def save_state(finish_at: datetime, duration_sec: int, bar_scale_sec: Optional[int] = None):
    """Save finish time, total duration, and current time to cache."""
    now = datetime.now()
    payload = {
        "finish_at": finish_at.isoformat(),
        "duration_sec": int(duration_sec),
        "last_saved_at": now.isoformat(),
    }
    existing = _read_state_payload()
    last_finished = existing.get("last_finished")
    if isinstance(last_finished, dict):
        payload["last_finished"] = last_finished
    last_duration = existing.get("last_duration_sec")
    if isinstance(last_duration, (int, float, str)):
        try:
            payload["last_duration_sec"] = int(last_duration)
        except (TypeError, ValueError):
            pass
    if bar_scale_sec is None or bar_scale_sec <= 0:
        bar_scale_sec = int(duration_sec)
    payload["bar_scale_sec"] = int(bar_scale_sec)
    _write_state_payload(payload)


def load_state():
    """Load finish time, total duration, and bar scale from cache."""
    data = _read_state_payload()
    finish_at_raw = data.get("finish_at")
    duration_raw = data.get("duration_sec")
    bar_scale_raw = data.get("bar_scale_sec")
    if finish_at_raw is None or duration_raw is None:
        return None
    try:
        finish_at = datetime.fromisoformat(finish_at_raw)
        duration_sec = int(duration_raw)
    except Exception:
        return None
    try:
        bar_scale_sec = int(bar_scale_raw) if bar_scale_raw is not None else duration_sec
    except Exception:
        bar_scale_sec = duration_sec
    if bar_scale_sec <= 0:
        bar_scale_sec = duration_sec
    return finish_at, duration_sec, bar_scale_sec


def save_last_finished(finish_at: datetime, duration_sec: int):
    """Persist only the most recent finished timer details."""
    payload = _read_state_payload()
    payload["last_finished"] = {
        "finish_at": finish_at.isoformat(),
        "duration_sec": int(duration_sec),
    }
    _write_state_payload(payload)


def load_last_finished():
    data = _read_state_payload()
    last_finished = data.get("last_finished")
    if not isinstance(last_finished, dict):
        return None
    finish_at_raw = last_finished.get("finish_at")
    duration_raw = last_finished.get("duration_sec")
    if finish_at_raw is None or duration_raw is None:
        return None
    try:
        finish_at = datetime.fromisoformat(finish_at_raw)
        duration_sec = int(duration_raw)
    except Exception:
        return None
    return finish_at, duration_sec


def save_last_duration(duration_sec: int):
    payload = _read_state_payload()
    payload["last_duration_sec"] = int(duration_sec)
    _write_state_payload(payload)


def load_last_duration():
    data = _read_state_payload()
    raw = data.get("last_duration_sec")
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def clear_state():
    payload = _read_state_payload()
    last_finished = payload.get("last_finished")
    last_duration = payload.get("last_duration_sec")
    to_keep = {}
    if isinstance(last_finished, dict):
        to_keep["last_finished"] = last_finished
    if isinstance(last_duration, (int, float, str)):
        try:
            to_keep["last_duration_sec"] = int(last_duration)
        except (TypeError, ValueError):
            pass
    if to_keep:
        _write_state_payload(to_keep)
        return
    state_file = _state_file()
    if state_file.exists():
        try:
            state_file.unlink()
        except OSError:
            pass


# ------------------------------
# Timer core
# ------------------------------
def start_timer(
    hours=0,
    minutes=0,
    seconds=0,
    *,
    one_line=False,
    graph_only=False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
):
    try:
        duration_sec = duration_to_seconds(hours, minutes, seconds)
        finish_at, duration_sec = _schedule_timer_seconds(duration_sec, duration_sec)
        save_last_duration(duration_sec)
    except ValueError as exc:
        print(str(exc))
        return

    if not one_line and not graph_only:
        print(
            "Coffee cooldown started. "
            f"Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    run_timer_loop(
        finish_at,
        duration_sec,
        one_line=one_line,
        graph_only=graph_only,
        bar_style=bar_style,
    )


def run_timer_loop(
    finish_at: Optional[datetime] = None,
    duration_sec: Optional[int] = None,
    bar_scale_sec: Optional[int] = None,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = True,
):
    # Refresh from state for resume.
    if finish_at is None or duration_sec is None or bar_scale_sec is None:
        state = load_state()
        if state is None:
            print(NO_ACTIVE_TIMER_MESSAGE)
            return
        finish_at, duration_sec, bar_scale_sec = state

    now = datetime.now()
    if (finish_at - now) <= timedelta(0):
        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        print(_select_expired_message(finish_at, duration_sec))
        return

    try:
        _run_live_loop(
            finish_at,
            duration_sec,
            bar_scale_sec,
            one_line=one_line,
            graph_only=graph_only,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )

        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        print(_select_expired_message(finish_at, duration_sec))

    except KeyboardInterrupt:
        print("\nInterrupted by user. Timer state saved.")


def _run_live_loop(
    finish_at: datetime,
    duration_sec: int,
    bar_scale_sec: int,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
):
    last_line_len = 0

    while True:
        state = load_state()
        if state is not None:
            finish_at, duration_sec, bar_scale_sec = state

        now = datetime.now()
        remaining = finish_at - now
        remaining_sec = int(remaining.total_seconds())

        if remaining_sec <= 0:
            break

        line = render_live_line(
            remaining_sec,
            bar_scale_sec,
            graph_only=graph_only,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        visible_len = visible_length(line) if use_ansi else len(line)
        pad = max(last_line_len - visible_len, 0)
        print(line + (" " * pad), end="\r", flush=True)
        last_line_len = visible_len

        time.sleep(1)

    if last_line_len:
        print(" " * last_line_len, end="\r", flush=True)


def _print_snapshot_status(
    finish_at: datetime,
    duration_sec: int,
    bar_scale_sec: int,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
):
    remaining_sec = int((finish_at - datetime.now()).total_seconds())
    if remaining_sec <= 0:
        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        print(_select_expired_message(finish_at, duration_sec))
        return

    if graph_only:
        line = render_snapshot_line(
            remaining_sec,
            bar_scale_sec,
            graph_only=True,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        print(line)
        return

    if one_line:
        line = render_snapshot_line(
            remaining_sec,
            bar_scale_sec,
            graph_only=False,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        print(line)
        return

    expires_at = finish_at.strftime("%Y-%m-%d %H:%M:%S")
    remaining_str = format_remaining(remaining_sec)
    bar_line = render_snapshot_line(
        remaining_sec,
        bar_scale_sec,
        graph_only=True,
        bar_style=bar_style,
        use_ansi=use_ansi,
    )
    print(f"Remaining: {remaining_str}")
    print(f"Expires at: {expires_at}")
    print(bar_line)


def _should_use_ansi(args) -> bool:
    color = getattr(args, "color", "auto")
    if color == "always":
        return True
    if color == "never":
        return False
    return sys.stdout.isatty()


def resume_timer(
    *, one_line=False, graph_only=False, bar_style: str = BAR_STYLE_GREEK_CROSS
):
    state = load_state()
    if state is None:
        print(NO_ACTIVE_TIMER_MESSAGE)
        return

    finish_at, duration_sec, bar_scale_sec = state
    if finish_at <= datetime.now():
        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        print(_select_expired_message(finish_at, duration_sec))
        return
    if not one_line and not graph_only:
        print(
            f"Resuming cooldown. Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    run_timer_loop(
        finish_at,
        duration_sec,
        bar_scale_sec,
        one_line=one_line,
        graph_only=graph_only,
        bar_style=bar_style,
    )


# ------------------------------
# Entry point
# ------------------------------
def main(argv=None):
    args = parse_cli_args(argv)
    request, error = normalize_cli_request(args)
    if error:
        print(error)
        return
    args.run = request.run
    resolved = _resolve_timer_state(args, request)
    if resolved is None:
        return
    finish_at, duration_sec, bar_scale_sec, new_timer_started = resolved

    if args.run:
        _run_live_mode(
            args,
            finish_at,
            duration_sec,
            bar_scale_sec,
            new_timer_started,
        )
        return

    _print_snapshot_status(
        finish_at,
        duration_sec,
        bar_scale_sec,
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=args.bar_style,
        use_ansi=_should_use_ansi(args),
    )

def _resolve_timer_state(args, request: CliRequest):
    finish_at = None
    duration_sec = None
    bar_scale_sec = None
    new_timer_started = False

    if request.clear:
        clear_state()
        print(NO_ACTIVE_TIMER_MESSAGE)
        return None

    if request.stack:
        try:
            added_sec = parse_simple_duration(request.duration or "")
        except ValueError as exc:
            message = str(exc) if str(exc) else INVALID_DURATION_MESSAGE
            print(message)
            return None

        state = load_state()
        now = datetime.now()
        if state is None:
            base_duration = load_last_duration() or DEFAULT_DURATION_SEC
            finish_at = now + timedelta(seconds=added_sec)
            duration_sec = base_duration
            bar_scale_sec = base_duration
            save_state(finish_at, duration_sec, bar_scale_sec=bar_scale_sec)
            new_timer_started = True
        else:
            finish_at, duration_sec, bar_scale_sec = state
            if finish_at <= now:
                try:
                    save_last_finished(finish_at, duration_sec)
                except Exception:
                    pass
                base_duration = load_last_duration() or DEFAULT_DURATION_SEC
                finish_at = now + timedelta(seconds=added_sec)
                duration_sec = base_duration
                bar_scale_sec = base_duration
                save_state(finish_at, duration_sec, bar_scale_sec=bar_scale_sec)
                new_timer_started = True
            else:
                remaining_sec = int((finish_at - now).total_seconds())
                finish_at = now + timedelta(seconds=remaining_sec + added_sec)
                duration_sec = duration_sec + added_sec
                save_state(finish_at, duration_sec, bar_scale_sec=bar_scale_sec)
        if bar_scale_sec is None:
            bar_scale_sec = duration_sec
        return finish_at, duration_sec, bar_scale_sec, new_timer_started

    if request.start:
        duration_sec = load_last_duration() or DEFAULT_DURATION_SEC
        finish_at, duration_sec = _schedule_timer_seconds(duration_sec, duration_sec)
        bar_scale_sec = duration_sec
        save_last_duration(duration_sec)
        new_timer_started = True
        return finish_at, duration_sec, bar_scale_sec, new_timer_started

    if request.duration is not None:
        try:
            remaining_sec, total_sec = parse_duration(request.duration)
        except ValueError as exc:
            message = str(exc) if str(exc) else INVALID_DURATION_MESSAGE
            print(message)
            return None
        try:
            finish_at, duration_sec = _schedule_timer_seconds(remaining_sec, total_sec)
        except ValueError as exc:
            print(str(exc))
            return None
        bar_scale_sec = duration_sec
        save_last_duration(duration_sec)
        new_timer_started = True
        return finish_at, duration_sec, bar_scale_sec, new_timer_started

    state = load_state()
    if state is None:
        print(NO_ACTIVE_TIMER_MESSAGE)
        return None
    finish_at, duration_sec, bar_scale_sec = state

    return finish_at, duration_sec, bar_scale_sec, new_timer_started


def _run_live_mode(args, finish_at, duration_sec, bar_scale_sec, new_timer_started):
    if finish_at > datetime.now():
        if new_timer_started:
            print(
                "Coffee cooldown started. "
                f"Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            print(
                "Resuming cooldown. "
                f"Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
    run_timer_loop(
        finish_at,
        duration_sec,
        bar_scale_sec,
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=args.bar_style,
        use_ansi=_should_use_ansi(args),
    )


if __name__ == "__main__":
    main()
