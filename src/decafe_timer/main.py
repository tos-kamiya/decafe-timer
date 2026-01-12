import hashlib
import json
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from appdirs import user_cache_dir
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    TextColumn,
)
from rich.text import Text

from .__about__ import __version__

APP_NAME = "coffee_timer"
APP_AUTHOR = "tos-kamiya"

CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
STATE_FILE = CACHE_DIR / "timer_state.json"

COLORED_CONSOLE = Console(markup=False, highlight=False)
PLAIN_CONSOLE = Console(color_system=None, markup=False, highlight=False)

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


def _get_console(*, one_line: bool = False, graph_only: bool = False) -> Console:
    return PLAIN_CONSOLE if (one_line or graph_only) else COLORED_CONSOLE


BAR_CHAR_WIDTH = 20
DURATION_PATTERN = re.compile(r"(\d+)([hms])", re.IGNORECASE)
FRACTION_SPLIT_PATTERN = re.compile(r"\s*/\s*")

BAR_STYLE_BLOCKS = "blocks"
BAR_STYLE_BRAILLE = "braille"
BAR_FILLED_CHAR = "\U0001d15b"  # black vertical rectangle
BAR_EMPTY_CHAR = "\U0001d15a"  # white vertical rectangle
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
    bar_style: str = BAR_STYLE_BRAILLE,
):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    try:
        duration_sec = _duration_to_seconds(hours, minutes, seconds)
        finish_at, duration_sec = _schedule_timer_seconds(duration_sec, duration_sec)
    except ValueError as exc:
        console.print(str(exc))
        return

    if not one_line and not graph_only:
        console.print(
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
    finish_at: datetime = None,
    duration_sec: int = None,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_BRAILLE,
):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    # resume 用に state から読み直すケース
    if finish_at is None or duration_sec is None:
        state = load_state()
        if state is None:
            console.print(NO_ACTIVE_TIMER_MESSAGE)
            return
        finish_at, duration_sec = state

    now = datetime.now()
    if (finish_at - now) <= timedelta(0):
        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        console.print(_select_expired_message(finish_at, duration_sec))
        return

    if one_line or graph_only:
        _run_ascii_loop(
            finish_at,
            duration_sec,
            graph_only=graph_only,
            bar_style=bar_style,
        )
        return

    try:
        _run_rich_loop(finish_at, duration_sec)

        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        console.print(_select_expired_message(finish_at, duration_sec))

    except KeyboardInterrupt:
        console.print("\nInterrupted by user. Timer state saved.")


def _run_rich_loop(finish_at: datetime, duration_sec: int):
    last_saved_minute = None
    progress = Progress(
        TextColumn("{task.fields[remaining]}"),
        _GreekCrossBarColumn(bar_width=BAR_CHAR_WIDTH),
        transient=True,
        console=COLORED_CONSOLE,
    )

    with progress:
        task_id = progress.add_task(
            "",
            total=duration_sec,
            remaining="--:--:--",
        )

        while True:
            now = datetime.now()
            remaining = finish_at - now
            remaining_sec = int(remaining.total_seconds())

            if remaining_sec <= 0:
                progress.update(
                    task_id,
                    completed=0,
                    remaining="00:00:00",
                )
                break

            completed = remaining_sec
            remaining_str = _format_remaining(remaining_sec)

            progress.update(
                task_id,
                completed=completed,
                remaining=remaining_str,
            )

            if last_saved_minute != now.minute:
                save_state(finish_at, duration_sec)
                last_saved_minute = now.minute

            time.sleep(1)


def _run_ascii_loop(
    finish_at: datetime,
    duration_sec: int,
    *,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_BRAILLE,
):
    console = _get_console(one_line=True, graph_only=graph_only)
    last_saved_minute = None
    last_line_len = 0

    try:
        while True:
            now = datetime.now()
            remaining = finish_at - now
            remaining_sec = int(remaining.total_seconds())

            if remaining_sec <= 0:
                break

            line = _render_one_line(
                remaining_sec,
                duration_sec,
                graph_only=graph_only,
                bar_style=bar_style,
            )
            pad = max(last_line_len - len(line), 0)
            output = line + (" " * pad)
            console.print(
                output,
                end="\r",
                markup=False,
                highlight=False,
            )
            last_line_len = len(line)

            if last_saved_minute != now.minute:
                save_state(finish_at, duration_sec)
                last_saved_minute = now.minute

            time.sleep(1)

    except KeyboardInterrupt:
        console.print("\nInterrupted by user. Timer state saved.")
        return

    # Clear the current line before printing the final message.
    if last_line_len:
        console.print(" " * last_line_len, end="\r")

    try:
        save_last_finished(finish_at, duration_sec)
    except Exception:
        pass

    console.print(_select_expired_message(finish_at, duration_sec))


def _print_snapshot_status(
    finish_at: datetime,
    duration_sec: int,
    *,
    one_line: bool = False,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_BRAILLE,
):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    remaining_sec = int((finish_at - datetime.now()).total_seconds())
    if remaining_sec <= 0:
        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        console.print(_select_expired_message(finish_at, duration_sec))
        return

    if graph_only:
        line = _render_one_line(
            remaining_sec,
            duration_sec,
            graph_only=True,
            bar_style=bar_style,
        )
        console.print(line, markup=False)
        return

    if one_line:
        line = _render_one_line(
            remaining_sec,
            duration_sec,
            graph_only=False,
            bar_style=bar_style,
        )
        console.print(line, markup=False)
        return

    expires_at = finish_at.strftime("%Y-%m-%d %H:%M:%S")
    remaining_str = _format_remaining(remaining_sec)
    bar_line = _render_one_line(
        remaining_sec,
        duration_sec,
        graph_only=True,
        bar_style=bar_style,
    )
    console.print(f"Remaining: {remaining_str}")
    console.print(f"Expires at: {expires_at}")
    console.print(bar_line, markup=False)


def _format_remaining(remaining_sec: int) -> str:
    h = remaining_sec // 3600
    m = (remaining_sec % 3600) // 60
    s = remaining_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _render_one_line(
    remaining_sec: int,
    duration_sec: int,
    *,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_BRAILLE,
) -> str:
    remaining_str = _format_remaining(max(remaining_sec, 0))
    segments = BAR_CHAR_WIDTH
    if duration_sec <= 0:
        bar = _render_empty_bar(segments, bar_style)
    else:
        ratio = max(0.0, min(remaining_sec / duration_sec, 1.0))
        bar = _render_filled_bar(segments, ratio, bar_style)
    if graph_only:
        return f"{bar}"
    return f"{remaining_str} {bar}"


def _render_empty_bar(segments: int, bar_style: str) -> str:
    if bar_style == BAR_STYLE_BLOCKS:
        return BAR_EMPTY_CHAR * segments
    return GREEK_CROSS_EMPTY_CHAR * segments


def _render_filled_bar(segments: int, ratio: float, bar_style: str) -> str:
    ratio = max(0.0, min(ratio, 1.0))
    if bar_style == BAR_STYLE_BLOCKS:
        filled_segments = int(ratio * segments + 0.5)
        filled_segments = max(0, min(filled_segments, segments))
        empty_segments = segments - filled_segments
        return (BAR_FILLED_CHAR * filled_segments) + (BAR_EMPTY_CHAR * empty_segments)

    units_per_block = len(GREEK_CROSS_LEVELS) - 1
    total_units = segments * units_per_block
    filled_units = int(ratio * total_units + 0.5)
    filled_units = max(0, min(filled_units, total_units))
    full_blocks = filled_units // units_per_block
    remainder = filled_units % units_per_block
    empty_blocks = segments - full_blocks - (1 if remainder else 0)
    bar = GREEK_CROSS_FULL_CHAR * full_blocks
    if remainder:
        bar += GREEK_CROSS_LEVELS[remainder]
    if empty_blocks > 0:
        bar += GREEK_CROSS_EMPTY_CHAR * empty_blocks
    return bar


def _render_greek_cross_bar_text(
    segments: int,
    ratio: float,
    complete_style: str,
    empty_style: str,
) -> Text:
    ratio = max(0.0, min(ratio, 1.0))
    units_per_block = len(GREEK_CROSS_LEVELS) - 1
    total_units = segments * units_per_block
    filled_units = int(ratio * total_units + 0.5)
    filled_units = max(0, min(filled_units, total_units))
    full_blocks = filled_units // units_per_block
    remainder = filled_units % units_per_block
    empty_blocks = segments - full_blocks - (1 if remainder else 0)

    text = Text()
    pieces = []
    pieces.extend([(GREEK_CROSS_FULL_CHAR, complete_style)] * full_blocks)
    if remainder:
        pieces.append((GREEK_CROSS_LEVELS[remainder], complete_style))
    pieces.extend([(GREEK_CROSS_EMPTY_CHAR, empty_style)] * empty_blocks)

    for index, (char, style) in enumerate(pieces):
        if index:
            text.append(" ")
        text.append(char, style=style)
    return text


class _GreekCrossBarColumn(ProgressColumn):
    def __init__(
        self,
        *,
        bar_width: int,
        complete_style: str = "progress.bar",
        empty_style: str = "dim",
    ):
        super().__init__()
        self.bar_width = bar_width
        self.complete_style = complete_style
        self.empty_style = empty_style

    def render(self, task) -> Text:
        if not task.total:
            ratio = 0.0
        else:
            ratio = task.completed / task.total
        if ratio >= 0.3:
            complete_style = "red"
        elif ratio >= 0.15:
            complete_style = "yellow"
        elif ratio >= 0.07:
            complete_style = "green"
        else:
            complete_style = "blue"
        return _render_greek_cross_bar_text(
            self.bar_width,
            ratio,
            complete_style,
            self.empty_style,
        )


def resume_timer(*, one_line=False, graph_only=False, bar_style: str = BAR_STYLE_BRAILLE):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    state = load_state()
    if state is None:
        last_finished = load_last_finished()
        if last_finished is not None:
            console.print(_select_expired_message(*last_finished))
        else:
            if one_line or graph_only:
                console.print(_select_expired_message(None, None))
            else:
                console.print(NO_ACTIVE_TIMER_MESSAGE)
        return

    finish_at, duration_sec = state
    if finish_at <= datetime.now():
        try:
            save_last_finished(finish_at, duration_sec)
        except Exception:
            pass
        console.print(_select_expired_message(finish_at, duration_sec))
        return
    if not one_line and not graph_only:
        console.print(
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
    )


def _parse_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Coffee cooldown timer (rich version)")
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
        choices=(BAR_STYLE_BRAILLE, BAR_STYLE_BLOCKS),
        default=BAR_STYLE_BRAILLE,
        help="Pick the ASCII bar style (default: braille).",
    )
    return parser.parse_args(argv)


def _resolve_timer_state(args):
    console = _get_console(one_line=args.one_line, graph_only=args.graph_only)
    finish_at = None
    duration_sec = None
    new_timer_started = False

    if args.duration:
        try:
            remaining_sec, total_sec = parse_duration(args.duration)
        except ValueError as exc:
            message = str(exc) if str(exc) else INVALID_DURATION_MESSAGE
            console.print(message)
            return None
        try:
            finish_at, duration_sec = _schedule_timer_seconds(remaining_sec, total_sec)
        except ValueError as exc:
            console.print(str(exc))
            return None
        new_timer_started = True
    else:
        state = load_state()
        if state is None:
            if args.run:
                console.print(NO_ACTIVE_TIMER_MESSAGE)
            else:
                last_finished = load_last_finished()
                if last_finished is not None:
                    console.print(_select_expired_message(*last_finished))
                else:
                    if args.one_line or args.graph_only:
                        console.print(_select_expired_message(None, None))
                    else:
                        console.print(NO_ACTIVE_TIMER_MESSAGE)
            return None
        finish_at, duration_sec = state

    return finish_at, duration_sec, new_timer_started


def _run_live_mode(args, finish_at, duration_sec, new_timer_started):
    console = _get_console(
        one_line=args.one_line,
        graph_only=args.graph_only,
    )
    if finish_at > datetime.now():
        if new_timer_started:
            console.print(
                "Coffee cooldown started. "
                f"Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            console.print(
                "Resuming cooldown. "
                f"Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
    run_timer_loop(
        finish_at,
        duration_sec,
        one_line=args.one_line,
        graph_only=args.graph_only,
        bar_style=args.bar_style,
    )


if __name__ == "__main__":
    main()
