import json
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
APP_AUTHOR = "toshihiro"  # お好みで

CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
STATE_FILE = CACHE_DIR / "timer_state.json"

console = Console()


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
def start_timer(hours=0, minutes=0, seconds=0):
    duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    duration_sec = int(duration.total_seconds())
    if duration_sec <= 0:
        console.print("[red]Duration must be positive.[/red]")
        return

    finish_at = datetime.now() + timedelta(seconds=duration_sec)
    save_state(finish_at, duration_sec)

    console.print(
        f"[bold cyan]Coffee cooldown started.[/bold cyan] "
        f"Expires at [yellow]{finish_at.strftime('%Y-%m-%d %H:%M:%S')}[/yellow]"
    )
    run_timer_loop(finish_at, duration_sec)


def run_timer_loop(finish_at: datetime = None, duration_sec: int = None):
    # resume 用に state から読み直すケース
    if finish_at is None or duration_sec is None:
        state = load_state()
        if state is None:
            console.print("[yellow]No active timer.[/yellow]")
            return
        finish_at, duration_sec = state

    # すでに期限切れなら即終了
    now = datetime.now()
    if (finish_at - now) <= timedelta(0):
        try:
            STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        console.print("[bold green]Cooldown already expired![/bold green] ☕")
        return

    last_saved_minute = None

    # rich の Progress を使ってバーを表示
    progress = Progress(
        TextColumn("[white]{task.fields[remaining]}[/white]"),
        BarColumn(bar_width=60),
        transient=True,  # 終了後にバーを消す
        console=console,
    )

    try:
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
                    # 残り 0 なので completed=0 として「バーが完全に消えた状態」に
                    progress.update(
                        task_id,
                        completed=0,
                        remaining="00:00:00",
                    )
                    break

                # 経過時間 = 全体 - 残り
                completed = remaining_sec

                # 残り時間を HH:MM:SS に整形
                h = remaining_sec // 3600
                m = (remaining_sec % 3600) // 60
                s = remaining_sec % 60
                remaining_str = f"{h:02d}:{m:02d}:{s:02d}"

                progress.update(
                    task_id,
                    completed=completed,
                    remaining=remaining_str,
                )

                # 1分ごとに状態保存
                if last_saved_minute != now.minute:
                    save_state(finish_at, duration_sec)
                    last_saved_minute = now.minute

                time.sleep(1)

        # Progress コンテキストを抜けたあとにメッセージ表示
        try:
            STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        console.print("[bold green]Cooldown expired![/bold green] ☕ You may drink coffee now.")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Timer state saved.[/yellow]")


def resume_timer():
    state = load_state()
    if state is None:
        console.print("[yellow]No active timer.[/yellow]")
        return

    finish_at, duration_sec = state
    console.print(
        f"[bold cyan]Resuming cooldown.[/bold cyan] "
        f"Expires at [yellow]{finish_at.strftime('%Y-%m-%d %H:%M:%S')}[/yellow]"
    )
    run_timer_loop(finish_at, duration_sec)


# ------------------------------
# エントリポイント
# ------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Coffee cooldown timer (rich version)")
    parser.add_argument(
        "--start",
        metavar="HH:MM:SS",
        help="Start a new timer with the given duration (e.g. 2:00:00)",
    )
    args = parser.parse_args()

    if args.start:
        try:
            h, m, s = map(int, args.start.split(":"))
        except ValueError:
            console.print("[red]Invalid format. Use HH:MM:SS (e.g. 0:25:00).[/red]")
        else:
            start_timer(hours=h, minutes=m, seconds=s)
    else:
        # 引数なしなら再開
        resume_timer()


if __name__ == "__main__":
    main()
