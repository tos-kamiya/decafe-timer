import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from appdirs import user_cache_dir

from .__about__ import __version__

APP_NAME = "coffee_timer"
APP_AUTHOR = "tos-kamiya"

CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
STATE_FILE = CACHE_DIR / "timer_state.json"

EXPIRED_MESSAGES = [
    "Cooldown expired! ☕ You may drink coffee now.",
    # やさしく励ましてくれる系
    "Your break is over -- enjoy your coffee, gently.",
    "You’ve waited well. Treat yourself to a warm cup.",
    # ふんわり癒し系
    "Your coffee time has arrived -- relax and enjoy.",
    "A warm cup is waiting for you.",
    "The timer’s done. Brew a moment of comfort.",
    # ちょっとユーモア系
    "Permission granted: caffeination may proceed.",
    "Coffee mode unlocked. Use wisely.",
    # 行動変容をそっと支援する系
    "If you choose to, a small cup won’t hurt now.",
    "Ready when you are. Keep listening to your body.",
]
NO_ACTIVE_TIMER_MESSAGE = "No active timer."


BAR_CHAR_WIDTH = 20
BAR_CHAR_WIDTH_BLOCKS = BAR_CHAR_WIDTH * 2
DURATION_PATTERN = re.compile(r"(\d+)([hms])", re.IGNORECASE)
FRACTION_SPLIT_PATTERN = re.compile(r"\s*/\s*")
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

BAR_STYLE_BLOCKS = "blocks"
BAR_STYLE_GREEK_CROSS = "greek-cross"
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

INVALID_DURATION_MESSAGE = (
    "Invalid duration. Use AhBmCs (e.g. 2h30m) or HH:MM:SS. "
    "You can also use remaining/total like 3h/5h."
)


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
    duration_sec = _duration_to_seconds(hours, minutes, seconds)
    return _schedule_timer_seconds(duration_sec, duration_sec)


# ------------------------------
# 永続化まわり
# ------------------------------
def _read_state_payload():
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(finish_at: datetime, duration_sec: int):
    """終了予定時刻と総時間、現在時刻をキャッシュに保存"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
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
    STATE_FILE.write_text(json.dumps(payload))


def load_state():
    """キャッシュから終了予定時刻と総時間を読み出す"""
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
    """直近に終了したタイマーの情報だけを保持"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_finished": {
            "finish_at": finish_at.isoformat(),
            "duration_sec": int(duration_sec),
        }
    }
    STATE_FILE.write_text(json.dumps(payload))


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


# ------------------------------
# タイマー本体
# ------------------------------
def _parse_single_duration(duration_str: str):
    """Parse duration from HH:MM:SS or AhBmCs style into (h, m, s)."""
    duration_str = duration_str.strip()
    if not duration_str:
        raise ValueError

    if ":" in duration_str:
        parts = duration_str.split(":")
        if len(parts) != 3:
            raise ValueError
        try:
            h, m, s = map(int, parts)
        except ValueError as exc:
            raise ValueError from exc
        if any(value < 0 for value in (h, m, s)):
            raise ValueError
        if h == m == s == 0:
            raise ValueError
        return h, m, s

    normalized = duration_str.replace(" ", "").lower()
    if not normalized:
        raise ValueError

    pos = 0
    hours = minutes = seconds = 0
    for match in DURATION_PATTERN.finditer(normalized):
        if match.start() != pos:
            raise ValueError
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit == "h":
            hours += value
        elif unit == "m":
            minutes += value
        elif unit == "s":
            seconds += value
        pos = match.end()

    if pos != len(normalized):
        raise ValueError

    if hours == minutes == seconds == 0:
        raise ValueError

    return hours, minutes, seconds


def _duration_to_seconds(hours: int, minutes: int, seconds: int) -> int:
    return int(timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds())


def parse_duration(duration_str: str):
    """Parse duration; support remaining/total with a slash or a single duration.

    Returns (remaining_seconds, total_seconds).
    """
    duration_str = duration_str.strip()
    if not duration_str:
        raise ValueError(INVALID_DURATION_MESSAGE)

    fraction_parts = FRACTION_SPLIT_PATTERN.split(duration_str, maxsplit=1)
    if len(fraction_parts) == 2:
        remaining_raw, total_raw = fraction_parts
        try:
            rh, rm, rs = _parse_single_duration(remaining_raw)
            th, tm, ts = _parse_single_duration(total_raw)
        except ValueError:
            raise ValueError(INVALID_DURATION_MESSAGE)

        remaining_sec = _duration_to_seconds(rh, rm, rs)
        total_sec = _duration_to_seconds(th, tm, ts)

        if remaining_sec <= 0 or total_sec <= 0:
            raise ValueError(
                "Duration must be positive (parsed as remaining/total like 3h/5h)."
            )
        if remaining_sec > total_sec:
            raise ValueError(
                "Remaining duration cannot exceed total duration "
                "(parsed as remaining/total like 3h/5h)."
            )

        return remaining_sec, total_sec

    try:
        h, m, s = _parse_single_duration(duration_str)
    except ValueError:
        raise ValueError(INVALID_DURATION_MESSAGE)
    single_sec = _duration_to_seconds(h, m, s)
    return single_sec, single_sec


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
        duration_sec = _duration_to_seconds(hours, minutes, seconds)
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
    # resume 用に state から読み直すケース
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
    last_saved_minute = None
    last_line_len = 0

    while True:
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

        if last_saved_minute != now.minute:
            save_state(finish_at, duration_sec)
            last_saved_minute = now.minute

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


def _compute_greek_cross_segments(segments: int, ratio: float):
    ratio = max(0.0, min(ratio, 1.0))
    units_per_block = len(GREEK_CROSS_LEVELS) - 1
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
    full_blocks, remainder, empty_blocks = _compute_greek_cross_segments(
        segments, ratio
    )
    filled_style = _bar_color_for_ratio(ratio, ansi=ansi)
    pieces = []
    pieces.extend([(GREEK_CROSS_FULL_CHAR, filled_style)] * full_blocks)
    if remainder:
        pieces.append((GREEK_CROSS_LEVELS[remainder], filled_style))
    pieces.extend([(GREEK_CROSS_EMPTY_CHAR, ansi["dim"])] * empty_blocks)
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
        last_finished = load_last_finished()
        if last_finished is not None:
            print(_select_expired_message(*last_finished))
        else:
            if one_line or graph_only:
                print(_select_expired_message(None, None))
            else:
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
# エントリポイント
# ------------------------------
def main(argv=None):
    args = _parse_args(argv)
    resolved = _resolve_timer_state(args)
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


def _parse_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Coffee cooldown timer")
    parser.add_argument(
        "duration",
        nargs="?",
        metavar="DURATION",
        help=(
            "Set a new timer (e.g. 2h, 15m30s, 0:25:00, or remaining/total like 3h/5h). "
            "Omit to resume."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--one-line",
        action="store_true",
        help="Use the single-line ASCII format (time + bar).",
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="Show only the ASCII bar (no time).",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Keep updating continuously until the timer expires.",
    )
    parser.add_argument(
        "--bar-style",
        choices=(BAR_STYLE_GREEK_CROSS, BAR_STYLE_BLOCKS),
        default=BAR_STYLE_GREEK_CROSS,
        help="Pick the ASCII bar style (default: greek-cross).",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="Control ANSI colors (auto, always, never).",
    )
    return parser.parse_args(argv)


def _resolve_timer_state(args):
    finish_at = None
    duration_sec = None
    new_timer_started = False

    if args.duration:
        try:
            remaining_sec, total_sec = parse_duration(args.duration)
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
            if args.run:
                print(NO_ACTIVE_TIMER_MESSAGE)
            else:
                last_finished = load_last_finished()
                if last_finished is not None:
                    print(_select_expired_message(*last_finished))
                else:
                    if args.one_line or args.graph_only:
                        print(_select_expired_message(None, None))
                    else:
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
