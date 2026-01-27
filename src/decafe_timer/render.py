import re
from dataclasses import dataclass
from typing import Callable


BAR_CHAR_WIDTH = 20
BAR_CHAR_WIDTH_BLOCKS = BAR_CHAR_WIDTH * 2
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

BAR_STYLE_BLOCKS = "blocks"
BAR_STYLE_GREEK_CROSS = "greek-cross"
BAR_STYLE_COUNTING_ROD = "counting-rod"
BAR_FILLED_CHAR = "\U0001d15b"  # black vertical rectangle
BAR_EMPTY_CHAR = "\U0001d15a"  # white vertical rectangle
BAR_OVERFLOW_SUFFIX = ">>"

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


@dataclass(frozen=True)
class BarStyle:
    name: str
    render: Callable[[float, bool, dict[str, str]], str]


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


def format_remaining(remaining_sec: int) -> str:
    h = remaining_sec // 3600
    m = (remaining_sec % 3600) // 60
    s = remaining_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def render_live_line(
    remaining_sec: int,
    bar_scale_sec: int,
    *,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
) -> str:
    return render_snapshot_line(
        remaining_sec,
        bar_scale_sec,
        graph_only=graph_only,
        bar_style=bar_style,
        use_ansi=use_ansi,
    )


def render_snapshot_line(
    remaining_sec: int,
    bar_scale_sec: int,
    *,
    graph_only: bool = False,
    bar_style: str = BAR_STYLE_GREEK_CROSS,
    use_ansi: bool = False,
) -> str:
    ansi = _ansi_table(use_ansi)
    remaining_str = format_remaining(max(remaining_sec, 0))
    if bar_scale_sec <= 0:
        ratio = 0.0
        is_overflow = False
    else:
        ratio = max(0.0, min(remaining_sec / bar_scale_sec, 1.0))
        is_overflow = remaining_sec > bar_scale_sec
    style = BAR_STYLES.get(bar_style, BAR_STYLES[BAR_STYLE_GREEK_CROSS])
    bar = style.render(ratio, is_overflow, ansi)
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


def _render_greek_cross(ratio: float, is_overflow: bool, ansi: dict[str, str]) -> str:
    bar = _render_greek_cross_bar(BAR_CHAR_WIDTH, ratio, ansi=ansi)
    if is_overflow:
        bar += BAR_OVERFLOW_SUFFIX
    return bar


def _render_counting_rod(ratio: float, is_overflow: bool, ansi: dict[str, str]) -> str:
    bar = _render_counting_rod_bar(BAR_CHAR_WIDTH, ratio, ansi=ansi)
    if is_overflow:
        bar += BAR_OVERFLOW_SUFFIX
    return bar


def _render_blocks(ratio: float, is_overflow: bool, ansi: dict[str, str]) -> str:
    bar = _render_blocks_bar(BAR_CHAR_WIDTH_BLOCKS, ratio, ansi=ansi)
    if is_overflow:
        bar += BAR_OVERFLOW_SUFFIX
    return bar


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


def visible_length(text: str) -> int:
    return len(ANSI_ESCAPE_PATTERN.sub("", text))


BAR_STYLES = {
    BAR_STYLE_GREEK_CROSS: BarStyle(BAR_STYLE_GREEK_CROSS, _render_greek_cross),
    BAR_STYLE_COUNTING_ROD: BarStyle(BAR_STYLE_COUNTING_ROD, _render_counting_rod),
    BAR_STYLE_BLOCKS: BarStyle(BAR_STYLE_BLOCKS, _render_blocks),
}
