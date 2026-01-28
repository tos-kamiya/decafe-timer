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
DEFAULT_ONE_LINE = False
DEFAULT_GRAPH_ONLY = False
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
    save_state(finish_at, mem_sec)
    return finish_at, mem_sec


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


def _parse_bool(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(int(value))
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    return None


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


def _resolve_one_line(payload: dict) -> Optional[bool]:
    return _parse_bool(payload.get("one_line"))


def _resolve_graph_only(payload: dict) -> Optional[bool]:
    return _parse_bool(payload.get("graph_only"))


def _write_state_payload(payload: dict):
    state_file = _state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_file.with_name(f"{state_file.name}.tmp")
    tmp_path.write_text(json.dumps(payload))
    tmp_path.replace(state_file)


def save_state(
    finish_at: datetime,
    mem_sec: int,
):
    """Save finish time, display memory, and current time to cache."""
    existing = _read_state_payload()
    now = datetime.now()
    payload = {
        "finish_at": finish_at.isoformat(),
        "mem_sec": int(mem_sec),
        "last_saved_at": now.isoformat(),
    }
    if "bar_style" in existing:
        bar_style = _resolve_bar_style(existing)
        if bar_style is not None:
            payload["bar_style"] = bar_style
    if "one_line" in existing:
        one_line = _resolve_one_line(existing)
        if one_line is not None:
            payload["one_line"] = one_line
    if "graph_only" in existing:
        graph_only = _resolve_graph_only(existing)
        if graph_only is not None:
            payload["graph_only"] = graph_only
    _write_state_payload(payload)


def load_state():
    """Load finish time and display memory from cache."""
    data = _read_state_payload()
    finish_at = _parse_finish_at(data.get("finish_at"))
    mem_sec = _resolve_mem_sec(data) or DEFAULT_MEM_SEC
    return finish_at, mem_sec


def save_mem(mem_sec: int):
    payload = _read_state_payload()
    finish_at_raw = payload.get("finish_at")
    resolved_bar_style = _resolve_bar_style(payload)
    resolved_one_line = _resolve_one_line(payload)
    resolved_graph_only = _resolve_graph_only(payload)
    payload = {
        "mem_sec": int(mem_sec),
        "last_saved_at": datetime.now().isoformat(),
    }
    if resolved_bar_style is not None:
        payload["bar_style"] = resolved_bar_style
    if resolved_one_line is not None:
        payload["one_line"] = resolved_one_line
    if resolved_graph_only is not None:
        payload["graph_only"] = resolved_graph_only
    if finish_at_raw is not None:
        payload["finish_at"] = finish_at_raw
    _write_state_payload(payload)


def load_mem_sec() -> int:
    data = _read_state_payload()
    return _resolve_mem_sec(data) or DEFAULT_MEM_SEC


def load_bar_style() -> str:
    data = _read_state_payload()
    return _resolve_bar_style(data) or DEFAULT_BAR_STYLE


def load_render_flags() -> tuple[bool, bool]:
    data = _read_state_payload()
    one_line = _resolve_one_line(data)
    graph_only = _resolve_graph_only(data)
    return (
        one_line if one_line is not None else DEFAULT_ONE_LINE,
        graph_only if graph_only is not None else DEFAULT_GRAPH_ONLY,
    )


def save_render_config(
    *, bar_style: str, one_line: bool, graph_only: bool, mem_sec: Optional[int]
):
    payload = {
        "bar_style": bar_style,
        "one_line": bool(one_line),
        "graph_only": bool(graph_only),
        "last_saved_at": datetime.now().isoformat(),
    }
    if mem_sec is not None:
        payload["mem_sec"] = int(mem_sec)
    finish_at_raw = _read_state_payload().get("finish_at")
    if finish_at_raw is not None:
        payload["finish_at"] = finish_at_raw
    _write_state_payload(payload)


def clear_state():
    payload = _read_state_payload()
    mem_sec = _resolve_mem_sec(payload)
    bar_style = _resolve_bar_style(payload)
    one_line = _resolve_one_line(payload)
    graph_only = _resolve_graph_only(payload)
    if mem_sec is not None or bar_style is not None or one_line is not None or graph_only is not None:
        _write_state_payload(
            {
                **({"mem_sec": int(mem_sec)} if mem_sec is not None else {}),
                "bar_style": bar_style or DEFAULT_BAR_STYLE,
                **({"one_line": one_line} if one_line is not None else {}),
                **({"graph_only": graph_only} if graph_only is not None else {}),
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
        loaded_finish_at, mem_sec = load_state()
        if loaded_finish_at is None:
            was_cleared = True
            break
        finish_at = loaded_finish_at

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


def _resolve_effective_render_flags(args) -> tuple[bool, bool]:
    saved_one_line, saved_graph_only = load_render_flags()
    one_line = args.one_line if args.one_line is not None else saved_one_line
    graph_only = args.graph_only if args.graph_only is not None else saved_graph_only
    if args.layout:
        one_line = args.layout == "one-line"
        graph_only = args.layout == "graph-only"
    if one_line and graph_only:
        graph_only = False
    return bool(one_line), bool(graph_only)


# ------------------------------
# Entry point
# ------------------------------
def main(argv=None):
    args = parse_cli_args(argv)
    effective_bar_style = _resolve_effective_bar_style(args)
    effective_one_line, effective_graph_only = _resolve_effective_render_flags(args)
    request, error = normalize_cli_request(args)
    if error:
        print(error)
        return
    args.run = request.run
    resolved = _resolve_timer_state(
        args,
        request,
        effective_bar_style,
        effective_one_line,
        effective_graph_only,
    )
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
            one_line=effective_one_line,
            graph_only=effective_graph_only,
        )
        return

    _print_snapshot_status(
        finish_at,
        mem_sec,
        one_line=effective_one_line,
        graph_only=effective_graph_only,
        bar_style=effective_bar_style,
        use_ansi=_should_use_ansi(args),
    )

def _resolve_timer_state(
    args,
    request: CliRequest,
    bar_style: str,
    one_line: bool,
    graph_only: bool,
):
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
        saved_one_line, saved_graph_only = load_render_flags()
        next_bar_style = saved_bar_style
        next_one_line = saved_one_line
        next_graph_only = saved_graph_only
        if args.bar_style is not None:
            next_bar_style = args.bar_style
        if args.layout:
            next_one_line = args.layout == "one-line"
            next_graph_only = args.layout == "graph-only"
        else:
            if args.one_line is not None:
                next_one_line = bool(args.one_line)
                if args.graph_only is None:
                    next_graph_only = False
            if args.graph_only is not None:
                next_graph_only = bool(args.graph_only)
                if args.one_line is None:
                    next_one_line = False
        if (
            next_bar_style != saved_bar_style
            or next_one_line != saved_one_line
            or next_graph_only != saved_graph_only
        ):
            save_render_config(
                bar_style=next_bar_style,
                one_line=next_one_line,
                graph_only=next_graph_only,
                mem_sec=mem_sec,
            )
            saved_bar_style = next_bar_style
            saved_one_line = next_one_line
            saved_graph_only = next_graph_only
        layout = (
            "graph-only"
            if saved_graph_only
            else "one-line"
            if saved_one_line
            else "default"
        )
        print(f"Memory: {format_remaining(mem_sec)}")
        print(f"Bar style: {saved_bar_style}")
        print(f"Layout: {layout}")
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
        save_mem(mem_sec)
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
            save_state(finish_at, mem_sec)
            new_timer_started = True
        else:
            finish_at = finish_at + timedelta(seconds=added_sec)
            save_state(finish_at, mem_sec)
        return finish_at, mem_sec, new_timer_started

    finish_at, mem_sec = load_state()
    if finish_at is None:
        print(NO_ACTIVE_TIMER_MESSAGE)
        return None

    return finish_at, mem_sec, new_timer_started


def _run_live_mode(
    args,
    finish_at,
    mem_sec,
    new_timer_started,
    *,
    bar_style: str,
    one_line: bool,
    graph_only: bool,
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
        one_line=one_line,
        graph_only=graph_only,
        bar_style=bar_style,
        use_ansi=_should_use_ansi(args),
    )


if __name__ == "__main__":
    main()
