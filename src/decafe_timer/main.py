import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .cli import CliRequest, normalize_cli_request, parse_cli_args
from .duration import INVALID_DURATION_MESSAGE, duration_to_seconds, parse_duration

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


BAR_CHAR_WIDTH = 20
BAR_CHAR_WIDTH_BLOCKS = BAR_CHAR_WIDTH * 2
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

BAR_STYLE_BLOCKS = "blocks"
BAR_STYLE_GREEK_CROSS = "greek-cross"
BAR_STYLE_COUNTING_ROD = "counting-rod"
BAR_FILLED_CHAR = "\U0001d15b"  # black vertical rectangle
BAR_EMPTY_CHAR = "\U0001d15a"  # white vertical rectangle
# ANSI color helpers for live mode.
ANSI_RESET = "\x1b[0m"
ANSI_DIM = "\x1b[2m"
ANSI_RED = "\x1b[31m"
ANSI_YELLOW = "\x1b[33m"
ANSI_GREEN = "\x1b[32m"
ANSI_BLUE = "\x1b[34m"
# Greek cross levels from THIN to EXTREMELY HEAVY (U+1F7A1..U+1F7A7).
GREEK_CROSS_LEVELS = [
    "\U0001f7a1",
    "\U0001f7a2",
    "\U0001f7a3",
    "\U0001f7a4",
    "\U0001f7a5",
    "\U0001f7a6",
    "\U0001f7a7",
]
GREEK_CROSS_EMPTY_CHAR = GREEK_CROSS_LEVELS[0]
GREEK_CROSS_FULL_CHAR = GREEK_CROSS_LEVELS[-1]
# Counting rod numerals from lowest to highest (U+1D369..U+1D36D).
COUNTING_ROD_LEVELS = [
    "\U0001d369",
    "\U0001d36a",
    "\U0001d36b",
    "\U0001d36c",
    "\U0001d36d",
]
COUNTING_ROD_EMPTY_CHAR = COUNTING_ROD_LEVELS[0]
COUNTING_ROD_FULL_CHAR = COUNTING_ROD_LEVELS[-1]



def _ansi_table(enabled: bool) -> dict[str, str]:
    if not enabled:
        return {
            "reset": "",
            "dim": "",
            "red": "",
            "yellow": "",
            "green": "",
            "blue": "",
        }
    return {
        "reset": ANSI_RESET,
        "dim": ANSI_DIM,
        "red": ANSI_RED,
        "yellow": ANSI_YELLOW,
        "green": ANSI_GREEN,
        "blue": ANSI_BLUE,
    }


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


def _schedule_timer_seconds(remaining_sec: int, total_sec: int):
    """Create a new timer from seconds, persist it, and return (finish_at, duration_sec)."""
    if remaining_sec <= 0 or total_sec <= 0:
        raise ValueError("Duration must be positive.")
    finish_at = datetime.now() + timedelta(seconds=remaining_sec)
    save_state(finish_at, total_sec)
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


def save_state(finish_at: datetime, duration_sec: int):
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
    _write_state_payload(payload)


def load_state():
    """Load finish time and total duration from cache."""
    data = _read_state_payload()
    finish_at_raw = data.get("finish_at")
    duration_raw = data.get("duration_sec")
    if finish_at_raw is None or duration_raw is None:
        return None
    try:
        finish_at = datetime.fromisoformat(finish_at_raw)
        duration_sec = int(duration_raw)
    except Exception:
        return None
    return finish_at, duration_sec


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


def clear_state():
    payload = _read_state_payload()
    last_finished = payload.get("last_finished")
    if isinstance(last_finished, dict):
        _write_state_payload({"last_finished": last_finished})
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
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = True,
):
    # Refresh from state for resume.
    if finish_at is None or duration_sec is None:
        state = load_state()
        if state is None:
            print(NO_ACTIVE_TIMER_MESSAGE)
            return
        finish_at, duration_sec = state

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
            finish_at, duration_sec = state

        now = datetime.now()
        remaining = finish_at - now
        remaining_sec = int(remaining.total_seconds())

        if remaining_sec <= 0:
            break

        line = _render_live_line(
            remaining_sec,
            duration_sec,
            graph_only=graph_only,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        visible_len = _visible_length(line) if use_ansi else len(line)
        pad = max(last_line_len - visible_len, 0)
        print(line + (" " * pad), end="\r", flush=True)
        last_line_len = visible_len

        time.sleep(1)

    if last_line_len:
        print(" " * last_line_len, end="\r", flush=True)


def _print_snapshot_status(
    finish_at: datetime,
    duration_sec: int,
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
        line = _render_snapshot_line(
            remaining_sec,
            duration_sec,
            graph_only=True,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        print(line)
        return

    if one_line:
        line = _render_snapshot_line(
            remaining_sec,
            duration_sec,
            graph_only=False,
            bar_style=bar_style,
            use_ansi=use_ansi,
        )
        print(line)
        return

    expires_at = finish_at.strftime("%Y-%m-%d %H:%M:%S")
    remaining_str = _format_remaining(remaining_sec)
    bar_line = _render_snapshot_line(
        remaining_sec,
        duration_sec,
        graph_only=True,
        bar_style=bar_style,
        use_ansi=use_ansi,
    )
    print(f"Remaining: {remaining_str}")
    print(f"Expires at: {expires_at}")
    print(bar_line)


def _format_remaining(remaining_sec: int) -> str:
    h = remaining_sec // 3600
    m = (remaining_sec % 3600) // 60
    s = remaining_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _render_live_line(
    remaining_sec: int,
    duration_sec: int,
    *,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
) -> str:
    return _render_snapshot_line(
        remaining_sec,
        duration_sec,
        graph_only=graph_only,
        bar_style=bar_style,
        use_ansi=use_ansi,
    )


def _render_snapshot_line(
    remaining_sec: int,
    duration_sec: int,
    *,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
) -> str:
    ansi = _ansi_table(use_ansi)
    remaining_str = _format_remaining(max(remaining_sec, 0))
    if duration_sec <= 0:
        ratio = 0.0
    else:
        ratio = max(0.0, min(remaining_sec / duration_sec, 1.0))
    bar = _render_bar(_bar_segments(bar_style), ratio, bar_style, ansi)
    if graph_only:
        return bar
    return f"{remaining_str} {bar}"


def _compute_level_segments(levels: list[str], segments: int, ratio: float):
    ratio = max(0.0, min(ratio, 1.0))
    units_per_block = len(levels) - 1
    total_units = segments * units_per_block
    filled_units = int(ratio * total_units + 0.5)
    filled_units = max(0, min(filled_units, total_units))
    full_blocks = filled_units // units_per_block
    remainder = filled_units % units_per_block
    empty_blocks = segments - full_blocks - (1 if remainder else 0)
    return full_blocks, remainder, empty_blocks


def _bar_color_for_ratio(ratio: float, *, ansi: dict[str, str]) -> str:
    if ratio >= 0.3:
        return ansi["red"]
    if ratio >= 0.15:
        return ansi["yellow"]
    if ratio >= 0.07:
        return ansi["green"]
    return ansi["blue"]


def _render_greek_cross_bar(
    segments: int, ratio: float, *, ansi: dict[str, str]
) -> str:
    full_blocks, remainder, empty_blocks = _compute_level_segments(
        GREEK_CROSS_LEVELS, segments, ratio
    )
    filled_style = _bar_color_for_ratio(ratio, ansi=ansi)
    pieces = []
    pieces.extend([(GREEK_CROSS_FULL_CHAR, filled_style)] * full_blocks)
    if remainder:
        pieces.append((GREEK_CROSS_LEVELS[remainder], filled_style))
    pieces.extend([(GREEK_CROSS_EMPTY_CHAR, ansi["dim"])] * empty_blocks)
    return _render_ansi_spaced(pieces, ansi=ansi)


def _render_counting_rod_bar(
    segments: int, ratio: float, *, ansi: dict[str, str]
) -> str:
    full_blocks, remainder, empty_blocks = _compute_level_segments(
        COUNTING_ROD_LEVELS, segments, ratio
    )
    filled_style = _bar_color_for_ratio(ratio, ansi=ansi)
    pieces = []
    pieces.extend([(COUNTING_ROD_FULL_CHAR, filled_style)] * full_blocks)
    if remainder:
        pieces.append((COUNTING_ROD_LEVELS[remainder], filled_style))
    pieces.extend([(COUNTING_ROD_EMPTY_CHAR, ansi["dim"])] * empty_blocks)
    return _render_ansi_spaced(pieces, ansi=ansi)


def _render_blocks_bar(segments: int, ratio: float, *, ansi: dict[str, str]) -> str:
    ratio = max(0.0, min(ratio, 1.0))
    filled_segments = int(ratio * segments + 0.5)
    filled_segments = max(0, min(filled_segments, segments))
    empty_segments = segments - filled_segments
    color = _bar_color_for_ratio(ratio, ansi=ansi)
    return (
        f"{ansi['reset']}{color}"
        + (BAR_FILLED_CHAR * filled_segments)
        + f"{ansi['reset']}{ansi['dim']}"
        + (BAR_EMPTY_CHAR * empty_segments)
        + ansi["reset"]
    )


def _render_bar(segments: int, ratio: float, bar_style: str, ansi: dict[str, str]) -> str:
    if bar_style == BAR_STYLE_BLOCKS:
        return _render_blocks_bar(segments, ratio, ansi=ansi)
    if bar_style == BAR_STYLE_COUNTING_ROD:
        return _render_counting_rod_bar(segments, ratio, ansi=ansi)
    return _render_greek_cross_bar(segments, ratio, ansi=ansi)


def _render_ansi_spaced(pieces, *, ansi: dict[str, str]):
    output = []
    current_style = None
    for index, (char, style) in enumerate(pieces):
        if index:
            output.append(" ")
        if style != current_style:
            output.append(ansi["reset"])
            if style:
                output.append(style)
            current_style = style
        output.append(char)
    if current_style is not None:
        output.append(ansi["reset"])
    return "".join(output)


def _visible_length(text: str) -> int:
    return len(ANSI_ESCAPE_PATTERN.sub("", text))


def _bar_segments(bar_style: str) -> int:
    if bar_style == BAR_STYLE_BLOCKS:
        return BAR_CHAR_WIDTH_BLOCKS
    return BAR_CHAR_WIDTH


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

    finish_at, duration_sec = state
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
    finish_at, duration_sec, new_timer_started = resolved

    if args.run:
        _run_live_mode(
            args,
            finish_at,
            duration_sec,
            new_timer_started,
        )
        return

    _print_snapshot_status(
        finish_at,
        duration_sec,
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=args.bar_style,
        use_ansi=_should_use_ansi(args),
    )

def _resolve_timer_state(args, request: CliRequest):
    finish_at = None
    duration_sec = None
    new_timer_started = False

    if request.clear:
        clear_state()
        print(NO_ACTIVE_TIMER_MESSAGE)
        return None

    if request.duration:
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
        new_timer_started = True
    else:
        state = load_state()
        if state is None:
            print(NO_ACTIVE_TIMER_MESSAGE)
            return None
        finish_at, duration_sec = state

    return finish_at, duration_sec, new_timer_started


def _run_live_mode(args, finish_at, duration_sec, new_timer_started):
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
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=args.bar_style,
        use_ansi=_should_use_ansi(args),
    )


if __name__ == "__main__":
    main()
