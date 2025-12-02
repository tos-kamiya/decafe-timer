import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from appdirs import user_cache_dir
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
)

APP_NAME = "coffee_timer"
APP_AUTHOR = "tos-kamiya"

CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
STATE_FILE = CACHE_DIR / "timer_state.json"

COLORED_CONSOLE = Console(markup=False, highlight=False)
PLAIN_CONSOLE = Console(color_system=None, markup=False, highlight=False)

ASCII_EXPIRED_MESSAGE = "You may drink coffee now."


def _get_console(*, one_line: bool = False, graph_only: bool = False) -> Console:
    return PLAIN_CONSOLE if (one_line or graph_only) else COLORED_CONSOLE


def _print_ascii_expired(console: Console):
    console.print(f"[{ASCII_EXPIRED_MESSAGE}]")


ONE_LINE_BAR_WIDTH = len(ASCII_EXPIRED_MESSAGE)
DURATION_PATTERN = re.compile(r"(\d+)([hms])", re.IGNORECASE)
BAR_FILLED_CHAR = "█"
BAR_EMPTY_CHAR = "░"


# ------------------------------
# 永続化まわり
# ------------------------------
def save_state(finish_at: datetime, duration_sec: int):
    """終了予定時刻と総時間、現在時刻をキャッシュに保存"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    data = {
        "finish_at": finish_at.isoformat(),
        "duration_sec": int(duration_sec),
        "last_saved_at": now.isoformat(),
    }
    STATE_FILE.write_text(json.dumps(data))


def load_state():
    """キャッシュから終了予定時刻と総時間を読み出す"""
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text())
        finish_at = datetime.fromisoformat(data["finish_at"])
        duration_sec = int(data["duration_sec"])
        return finish_at, duration_sec
    except Exception:
        return None


# ------------------------------
# タイマー本体
# ------------------------------
def parse_duration(duration_str: str):
    """Parse duration from HH:MM:SS or AhBmCs style."""
    duration_str = duration_str.strip()
    if not duration_str:
        raise ValueError("Duration string is empty.")

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


def start_timer(
    hours=0,
    minutes=0,
    seconds=0,
    *,
    one_line=False,
    graph_only=False,
):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    duration_sec = int(duration.total_seconds())
    if duration_sec <= 0:
        console.print("Duration must be positive.")
        return

    finish_at = datetime.now() + timedelta(seconds=duration_sec)
    save_state(finish_at, duration_sec)

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
    )


def run_timer_loop(
    finish_at: datetime = None,
    duration_sec: int = None,
    *,
    one_line: bool = False,
    graph_only: bool = False,
):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    # resume 用に state から読み直すケース
    if finish_at is None or duration_sec is None:
        state = load_state()
        if state is None:
            console.print("No active timer.")
            return
        finish_at, duration_sec = state

    now = datetime.now()
    if (finish_at - now) <= timedelta(0):
        try:
            STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        if one_line or graph_only:
            _print_ascii_expired(console)
        else:
            console.print("Cooldown already expired! ☕")
        return

    if one_line or graph_only:
        _print_one_line_status(
            finish_at,
            duration_sec,
            graph_only=graph_only,
        )
        return

    try:
        _run_rich_loop(finish_at, duration_sec)

        try:
            STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        console.print("Cooldown expired! ☕ You may drink coffee now.")

    except KeyboardInterrupt:
        console.print("\nInterrupted by user. Timer state saved.")


def _run_rich_loop(finish_at: datetime, duration_sec: int):
    last_saved_minute = None
    progress = Progress(
        TextColumn("{task.fields[remaining]}"),
        BarColumn(bar_width=60),
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


def _print_one_line_status(
    finish_at: datetime,
    duration_sec: int,
    *,
    graph_only: bool = False,
):
    console = _get_console(one_line=True, graph_only=graph_only)
    remaining_sec = int((finish_at - datetime.now()).total_seconds())
    if remaining_sec <= 0:
        try:
            STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        _print_ascii_expired(console)
        return

    line = _render_one_line(
        remaining_sec,
        duration_sec,
        graph_only=graph_only,
    )
    console.print(line, markup=False)


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
) -> str:
    remaining_str = _format_remaining(max(remaining_sec, 0))
    if duration_sec <= 0:
        bar = BAR_EMPTY_CHAR * ONE_LINE_BAR_WIDTH
    else:
        ratio = max(0, min(remaining_sec / duration_sec, 1))
        filled = min(
            ONE_LINE_BAR_WIDTH,
            int(round(ratio * ONE_LINE_BAR_WIDTH)),
        )
        bar = (
            BAR_FILLED_CHAR * filled
            + BAR_EMPTY_CHAR * (ONE_LINE_BAR_WIDTH - filled)
        )
    if graph_only:
        return f"[{bar}]"
    return f"{remaining_str} [{bar}]"


def resume_timer(*, one_line=False, graph_only=False):
    console = _get_console(one_line=one_line, graph_only=graph_only)
    state = load_state()
    if state is None:
        if one_line or graph_only:
            _print_ascii_expired(console)
        else:
            console.print("No active timer.")
        return

    finish_at, duration_sec = state
    if finish_at <= datetime.now():
        try:
            STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        if one_line or graph_only:
            _print_ascii_expired(console)
        else:
            console.print("Cooldown already expired! ☕")
        return
    if not one_line and not graph_only:
        console.print(
            "Resuming cooldown. "
            f"Expires at {finish_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    run_timer_loop(
        finish_at,
        duration_sec,
        one_line=one_line,
        graph_only=graph_only,
    )


# ------------------------------
# エントリポイント
# ------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Coffee cooldown timer (rich version)")
    parser.add_argument(
        "duration",
        nargs="?",
        metavar="DURATION",
        help="Start a new timer (e.g. 2h, 15m30s, or 0:25:00)",
    )
    parser.add_argument(
        "--one-line",
        action="store_true",
        help="Print a single ASCII snapshot (time + bar) and exit.",
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="Print only the ASCII bar (no time). Implies --one-line.",
    )
    args = parser.parse_args()
    if args.graph_only:
        args.one_line = True

    if args.duration:
        try:
            h, m, s = parse_duration(args.duration)
        except ValueError:
            _get_console(
                one_line=args.one_line,
                graph_only=args.graph_only,
            ).print("Invalid duration. Use AhBmCs (e.g. 2h30m) or HH:MM:SS.")
            return
        start_timer(
            hours=h,
            minutes=m,
            seconds=s,
            one_line=args.one_line,
            graph_only=args.graph_only,
        )
    else:
        # 引数なしなら再開
        resume_timer(one_line=args.one_line, graph_only=args.graph_only)


if __name__ == "__main__":
    main()
