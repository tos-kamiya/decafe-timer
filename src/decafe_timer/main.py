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
    duration_to_seconds,
    parse_simple_duration,
)
from .render import (
    BAR_STYLE_BLOCKS,
    BAR_STYLE_COUNTING_ROD,
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

DEFAULT_MEM_SEC = duration_to_seconds(3, 0, 0)
DEFAULT_BAR_STYLE = BAR_STYLE_GREEK_CROSS
BAR_STYLE_CHOICES = (
    BAR_STYLE_GREEK_CROSS,
    BAR_STYLE_COUNTING_ROD,
    BAR_STYLE_BLOCKS,
)


def _select_expired_message(
    finish_at: Optional[datetime],
    mem_sec: Optional[int],
) -> str:
    if finish_at is None or mem_sec is None:
        return random.choice(EXPIRED_MESSAGES)
    key = f"{finish_at.isoformat()}-{mem_sec}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    index = int.from_bytes(digest[:8], "big") % len(EXPIRED_MESSAGES)
    return EXPIRED_MESSAGES[index]


def _schedule_timer_seconds(remaining_sec: int, mem_sec: int):
    """Create a new timer from seconds, persist it, and return (finish_at, mem_sec)."""
    if remaining_sec <= 0 or mem_sec <= 0:
        raise ValueError("Duration must be positive.")
    finish_at = datetime.now() + timedelta(seconds=remaining_sec)
    save_state(finish_at, mem_sec, DEFAULT_BAR_STYLE)
    return finish_at, mem_sec


def _schedule_timer(hours: int, minutes: int, seconds: int):
    """Create a new timer, persist it, and return (finish_at, mem_sec)."""
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


def _parse_finish_at(value) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _parse_mem_sec(value) -> Optional[int]:
    if value is None:
        return None
    try:
        mem_sec = int(value)
    except (TypeError, ValueError):
        return None
    if mem_sec <= 0:
        return None
    return mem_sec


def _parse_bar_style(value) -> Optional[str]:
    if value is None:
        return None
    if value in BAR_STYLE_CHOICES:
        return value
    return None


def _resolve_mem_sec(payload: dict) -> Optional[int]:
    mem_sec = _parse_mem_sec(payload.get("mem_sec"))
    if mem_sec is None:
        mem_sec = _parse_mem_sec(payload.get("duration_sec"))
    return mem_sec


def _resolve_bar_style(payload: dict) -> Optional[str]:
    return _parse_bar_style(payload.get("bar_style"))


def _write_state_payload(payload: dict):
    state_file = _state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_file.with_name(f"{state_file.name}.tmp")
    tmp_path.write_text(json.dumps(payload))
    tmp_path.replace(state_file)


def save_state(
    finish_at: datetime,
    mem_sec: int,
    bar_style: str,
):
    """Save finish time, display memory, and current time to cache."""
    now = datetime.now()
    payload = {
        "finish_at": finish_at.isoformat(),
        "mem_sec": int(mem_sec),
        "bar_style": bar_style,
        "last_saved_at": now.isoformat(),
    }
    _write_state_payload(payload)


def load_state():
    """Load finish time and display memory from cache."""
    data = _read_state_payload()
    finish_at = _parse_finish_at(data.get("finish_at"))
    mem_sec = _resolve_mem_sec(data) or DEFAULT_MEM_SEC
    return finish_at, mem_sec


def save_mem(mem_sec: int, bar_style: Optional[str] = None):
    payload = _read_state_payload()
    finish_at_raw = payload.get("finish_at")
    resolved_bar_style = bar_style or _resolve_bar_style(payload) or DEFAULT_BAR_STYLE
    payload = {
        "mem_sec": int(mem_sec),
        "bar_style": resolved_bar_style,
        "last_saved_at": datetime.now().isoformat(),
    }
    if finish_at_raw is not None:
        payload["finish_at"] = finish_at_raw
    _write_state_payload(payload)


def load_mem_sec() -> int:
    data = _read_state_payload()
    return _resolve_mem_sec(data) or DEFAULT_MEM_SEC


def load_bar_style() -> str:
    data = _read_state_payload()
    return _resolve_bar_style(data) or DEFAULT_BAR_STYLE


def clear_state():
    payload = _read_state_payload()
    mem_sec = _resolve_mem_sec(payload)
    bar_style = _resolve_bar_style(payload)
    if mem_sec is not None or bar_style is not None:
        _write_state_payload(
            {
                **({"mem_sec": int(mem_sec)} if mem_sec is not None else {}),
                "bar_style": bar_style or DEFAULT_BAR_STYLE,
                "last_saved_at": datetime.now().isoformat(),
            }
        )
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
        intake_sec = duration_to_seconds(hours, minutes, seconds)
        finish_at, mem_sec = _schedule_timer_seconds(intake_sec, intake_sec)
    except ValueError as exc:
        print(str(exc))
        return

    if not one_line and not graph_only:
        print(
            "Caffeine intake recorded. "
            f"Clears at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    run_timer_loop(
        finish_at,
        mem_sec,
        one_line=one_line,
        graph_only=graph_only,
        bar_style=bar_style,
    )


def run_timer_loop(
    finish_at: Optional[datetime] = None,
    mem_sec: Optional[int] = None,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = True,
):
    # Refresh from state for resume.
    if finish_at is None or mem_sec is None:
        finish_at, mem_sec = load_state()
        if finish_at is None:
            print(NO_ACTIVE_TIMER_MESSAGE)
            return

    now = datetime.now()
    if (finish_at - now) <= timedelta(0):
        _print_expired_message(finish_at, mem_sec)
        return

    try:
        finish_at, mem_sec, was_cleared = _run_live_loop(
            finish_at,
            mem_sec,
            one_line=one_line,
            graph_only=graph_only,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )

        if was_cleared:
            print(NO_ACTIVE_TIMER_MESSAGE)
            return

        _print_expired_message(finish_at, mem_sec)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Timer state saved.")


def _run_live_loop(
    finish_at: datetime,
    mem_sec: int,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
):
    last_line_len = 0
    was_cleared = False

    while True:
        finish_at, mem_sec = load_state()
        if finish_at is None:
            was_cleared = True
            break

        now = datetime.now()
        remaining = finish_at - now
        remaining_sec = int(remaining.total_seconds())

        if remaining_sec <= 0:
            break

        line = render_live_line(
            remaining_sec,
            mem_sec,
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
    return finish_at, mem_sec, was_cleared


def _print_snapshot_status(
    finish_at: Optional[datetime],
    mem_sec: int,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
):
    if finish_at is None:
        print(NO_ACTIVE_TIMER_MESSAGE)
        return
    remaining_sec = int((finish_at - datetime.now()).total_seconds())
    if remaining_sec <= 0:
        _print_expired_message(finish_at, mem_sec)
        return

    if graph_only:
        line = render_snapshot_line(
            remaining_sec,
            mem_sec,
            graph_only=True,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        print(line)
        return

    if one_line:
        line = render_snapshot_line(
            remaining_sec,
            mem_sec,
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
        mem_sec,
        graph_only=True,
        bar_style=bar_style,
        use_ansi=use_ansi,
    )
    print(f"Remaining: {remaining_str}")
    print(f"Clears at: {expires_at}")
    print(bar_line)


def _print_expired_message(finish_at: Optional[datetime], mem_sec: Optional[int]):
    print("Expired")
    print(_select_expired_message(finish_at, mem_sec))


def _should_use_ansi(args) -> bool:
    color = getattr(args, "color", "auto")
    if color == "always":
        return True
    if color == "never":
        return False
    return sys.stdout.isatty()


def _resolve_effective_bar_style(args) -> str:
    return args.bar_style or load_bar_style()


def resume_timer(
    *, one_line=False, graph_only=False, bar_style: str = BAR_STYLE_GREEK_CROSS
):
    finish_at, mem_sec = load_state()
    if finish_at is None:
        print(NO_ACTIVE_TIMER_MESSAGE)
        return
    if finish_at <= datetime.now():
        _print_expired_message(finish_at, mem_sec)
        return
    if not one_line and not graph_only:
        print(
            f"Resuming caffeine clearance. Clears at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    run_timer_loop(
        finish_at,
        mem_sec,
        one_line=one_line,
        graph_only=graph_only,
        bar_style=bar_style,
    )


# ------------------------------
# Entry point
# ------------------------------
def main(argv=None):
    args = parse_cli_args(argv)
    effective_bar_style = _resolve_effective_bar_style(args)
    request, error = normalize_cli_request(args)
    if error:
        print(error)
        return
    args.run = request.run
    resolved = _resolve_timer_state(args, request, effective_bar_style)
    if resolved is None:
        return
    finish_at, mem_sec, new_timer_started = resolved

    if args.run:
        _run_live_mode(
            args,
            finish_at,
            mem_sec,
            new_timer_started,
            bar_style=effective_bar_style,
        )
        return

    _print_snapshot_status(
        finish_at,
        mem_sec,
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=effective_bar_style,
        use_ansi=_should_use_ansi(args),
    )

def _resolve_timer_state(args, request: CliRequest, bar_style: str):
    finish_at = None
    mem_sec = None
    new_timer_started = False

    if request.clear:
        clear_state()
        print(NO_ACTIVE_TIMER_MESSAGE)
        return None

    if request.config:
        mem_sec = load_mem_sec()
        saved_bar_style = load_bar_style()
        print(f"Memory: {format_remaining(mem_sec)}")
        print(f"Bar style: {saved_bar_style}")
        return None

    if request.mem:
        if request.mem_duration is None:
            mem_sec = load_mem_sec()
            print(f"Memory: {format_remaining(mem_sec)}")
            return None
        try:
            mem_sec = parse_simple_duration(request.mem_duration or "")
        except ValueError as exc:
            message = str(exc)
            print(message)
            return None
        save_mem(mem_sec, bar_style=bar_style)
        print(f"Memory set to: {format_remaining(mem_sec)}")
        return None

    if request.intake:
        try:
            if request.duration:
                added_sec = parse_simple_duration(request.duration)
            else:
                added_sec = load_mem_sec()
        except ValueError as exc:
            message = str(exc)
            print(message)
            return None

        finish_at, mem_sec = load_state()
        now = datetime.now()
        if finish_at is None or finish_at <= now:
            finish_at = now + timedelta(seconds=added_sec)
            save_state(finish_at, mem_sec, bar_style)
            new_timer_started = True
        else:
            finish_at = finish_at + timedelta(seconds=added_sec)
            save_state(finish_at, mem_sec, bar_style)
        return finish_at, mem_sec, new_timer_started

    finish_at, mem_sec = load_state()
    if finish_at is None:
        print(NO_ACTIVE_TIMER_MESSAGE)
        return None

    return finish_at, mem_sec, new_timer_started


def _run_live_mode(
    args, finish_at, mem_sec, new_timer_started, *, bar_style: str
):
    if finish_at > datetime.now():
        if new_timer_started:
            print(
                "Caffeine intake recorded. "
                f"Clears at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            print(
                "Resuming caffeine clearance. "
                f"Clears at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
    run_timer_loop(
        finish_at,
        mem_sec,
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=bar_style,
        use_ansi=_should_use_ansi(args),
    )


if __name__ == "__main__":
    main()
