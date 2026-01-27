import contextlib

import pytest

from decafe_timer import render


@contextlib.contextmanager
def _ascii_render_symbols():
    originals = {
        "BAR_FILLED_CHAR": render.BAR_FILLED_CHAR,
        "BAR_EMPTY_CHAR": render.BAR_EMPTY_CHAR,
        "GREEK_CROSS_LEVELS": render.GREEK_CROSS_LEVELS,
        "GREEK_CROSS_EMPTY_CHAR": render.GREEK_CROSS_EMPTY_CHAR,
        "GREEK_CROSS_FULL_CHAR": render.GREEK_CROSS_FULL_CHAR,
        "COUNTING_ROD_LEVELS": render.COUNTING_ROD_LEVELS,
        "COUNTING_ROD_EMPTY_CHAR": render.COUNTING_ROD_EMPTY_CHAR,
        "COUNTING_ROD_FULL_CHAR": render.COUNTING_ROD_FULL_CHAR,
    }
    try:
        render.BAR_FILLED_CHAR = "#"
        render.BAR_EMPTY_CHAR = "-"
        render.GREEK_CROSS_LEVELS = [".", ":", "-", "=", "+", "*", "#"]
        render.GREEK_CROSS_EMPTY_CHAR = render.GREEK_CROSS_LEVELS[0]
        render.GREEK_CROSS_FULL_CHAR = render.GREEK_CROSS_LEVELS[-1]
        render.COUNTING_ROD_LEVELS = ["-", "=", "#", "%", "@"]
        render.COUNTING_ROD_EMPTY_CHAR = render.COUNTING_ROD_LEVELS[0]
        render.COUNTING_ROD_FULL_CHAR = render.COUNTING_ROD_LEVELS[-1]
        yield
    finally:
        for key, value in originals.items():
            setattr(render, key, value)


@pytest.fixture(autouse=True)
def _patch_ascii_symbols():
    with _ascii_render_symbols():
        yield


def test_format_remaining():
    assert render.format_remaining(3661) == "01:01:01"


def test_visible_length_strips_ansi():
    ansi = render._ansi_table(True)
    bar = render._render_blocks_bar(12, 0.5, ansi=ansi)
    assert render.visible_length(bar) == 12


def test_compute_level_segments_rounding():
    levels = ["-", "=", "#", "%", "@"]
    full_blocks, remainder, empty_blocks = render._compute_level_segments(
        levels, 4, 0.5
    )
    assert (full_blocks, remainder, empty_blocks) == (2, 0, 2)
    full_blocks, remainder, empty_blocks = render._compute_level_segments(
        levels, 4, 0.2
    )
    assert (full_blocks, remainder, empty_blocks) == (0, 3, 3)


def test_render_snapshot_line_graph_only_no_overflow():
    bar = render.render_snapshot_line(
        50, 100, graph_only=True, bar_style=render.BAR_STYLE_GREEK_CROSS
    )
    assert render.BAR_OVERFLOW_SUFFIX not in bar
    assert render.visible_length(bar) == render.BAR_CHAR_WIDTH * 2 - 1


def test_render_snapshot_line_graph_only_overflow():
    bar = render.render_snapshot_line(
        120, 100, graph_only=True, bar_style=render.BAR_STYLE_GREEK_CROSS
    )
    assert bar.endswith(render.BAR_OVERFLOW_SUFFIX)


def test_render_snapshot_line_includes_time():
    line = render.render_snapshot_line(
        100, 100, graph_only=False, bar_style=render.BAR_STYLE_GREEK_CROSS
    )
    assert line.startswith(f"{render.format_remaining(100)} ")


def test_bar_color_for_ratio_thresholds():
    ansi = render._ansi_table(True)
    assert render._bar_color_for_ratio(0.5, ansi=ansi) == render.ANSI_RED
    assert render._bar_color_for_ratio(0.2, ansi=ansi) == render.ANSI_YELLOW
    assert render._bar_color_for_ratio(0.1, ansi=ansi) == render.ANSI_GREEN
    assert render._bar_color_for_ratio(0.01, ansi=ansi) == render.ANSI_BLUE
