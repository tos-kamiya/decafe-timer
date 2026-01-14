from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

from .__about__ import __version__


@dataclass(frozen=True)
class CliRequest:
    run: bool
    clear: bool
    duration: Optional[str]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coffee cooldown timer")
    parser.add_argument(
        "duration",
        nargs="*",
        metavar="ARG",
        help=(
            "Set a new timer (e.g. 2h, 15m30s, 0:25:00, or remaining/total like 3h/5h). "
            "Omit to resume. Use 'run' to keep updating continuously, and use "
            "'clear', --clear, or 0 to remove the current timer."
        ),
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Alias for the clear command.",
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
        help="Alias for the run command (keep updating continuously).",
    )
    parser.add_argument(
        "--bar-style",
        choices=(
            "greek-cross",
            "counting-rod",
            "blocks",
        ),
        default="greek-cross",
        help="Pick the ASCII bar style (default: greek-cross).",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="Control ANSI colors (auto, always, never).",
    )
    return parser


def parse_cli_args(argv=None) -> argparse.Namespace:
    return build_arg_parser().parse_args(argv)


def normalize_cli_request(args: argparse.Namespace) -> tuple[CliRequest, Optional[str]]:
    tokens = list(getattr(args, "duration", []) or [])
    tokens_lower = [token.strip().lower() for token in tokens]
    requested_run = bool(getattr(args, "run", False))
    requested_clear = bool(getattr(args, "clear", False))

    if tokens_lower:
        first = tokens_lower[0]
        if first == "run":
            requested_run = True
            tokens = tokens[1:]
            tokens_lower = tokens_lower[1:]
        elif first in {"clear", "0"}:
            requested_clear = True
            tokens = tokens[1:]
            tokens_lower = tokens_lower[1:]

    if requested_run and requested_clear:
        return CliRequest(requested_run, requested_clear, None), (
            "Cannot combine run and clear."
        )

    if requested_run and any(token in {"clear", "0"} for token in tokens_lower):
        return CliRequest(requested_run, True, None), (
            "Cannot combine run and clear."
        )

    if requested_clear and "run" in tokens_lower:
        return CliRequest(True, requested_clear, None), (
            "Cannot combine run and clear."
        )

    if requested_clear and tokens:
        return CliRequest(requested_run, requested_clear, None), (
            "clear does not accept a duration."
        )

    duration = " ".join(tokens) if tokens else None
    return CliRequest(requested_run, requested_clear, duration), None
