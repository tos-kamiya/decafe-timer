from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

from .__about__ import __version__


@dataclass(frozen=True)
class CliRequest:
    run: bool
    clear: bool
    intake: bool
    mem: bool
    config: bool
    duration: Optional[str]
    mem_duration: Optional[str]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Caffeine clearance timer")
    parser.add_argument(
        "args",
        nargs="*",
        metavar="ARG",
        help=(
            "Intake caffeine (e.g. intake 2h, +5h) or set memory (mem 3h). "
            "Use 'config' to show memory and bar style. "
            "Use 'clear' or 0 to remove the current timer."
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
        default=None,
        help="Use the single-line ASCII format (time + bar).",
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        default=None,
        help="Show only the ASCII bar (no time).",
    )
    parser.add_argument(
        "--layout",
        choices=("default", "one-line", "graph-only"),
        default=None,
        help="Pick the layout (default, one-line, graph-only).",
    )
    parser.add_argument(
        "--bar-style",
        choices=(
            "greek-cross",
            "counting-rod",
            "blocks",
        ),
        default=None,
        help="Pick the ASCII bar style (default: stored setting or greek-cross).",
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
    tokens = list(getattr(args, "args", []) or [])
    tokens_lower = [token.strip().lower() for token in tokens]
    requested_run = False
    requested_clear = False
    requested_intake = False
    requested_mem = False
    requested_config = False

    def pop_token():
        nonlocal tokens, tokens_lower
        tokens = tokens[1:]
        tokens_lower = tokens_lower[1:]

    while tokens_lower:
        first = tokens_lower[0]
        if first == "run":
            requested_run = True
            pop_token()
            continue
        if first == "clear":
            requested_clear = True
            pop_token()
            continue
        if first == "intake":
            requested_intake = True
            pop_token()
            continue
        if first == "mem":
            requested_mem = True
            pop_token()
            continue
        if first == "config":
            requested_config = True
            pop_token()
            continue
        if first.startswith("+"):
            if first == "+":
                return CliRequest(requested_run, False, False, False, False, None, None), (
                    "intake requires a duration."
                )
            if requested_mem:
                return CliRequest(requested_run, False, False, False, False, None, None), (
                    "Cannot combine mem and +duration."
                )
            if requested_intake:
                return CliRequest(requested_run, False, False, False, False, None, None), (
                    "Cannot combine intake and +duration."
                )
            if requested_config:
                return CliRequest(requested_run, False, False, False, False, None, None), (
                    "Cannot combine config and +duration."
                )
            requested_intake = True
            tokens[0] = tokens[0][1:]
            tokens_lower[0] = tokens_lower[0][1:]
        break

    if sum([requested_run, requested_clear, requested_intake, requested_mem, requested_config]) > 1:
        return CliRequest(requested_run, False, False, False, False, None, None), (
            "Cannot combine run, intake, mem, config, and clear."
        )

    if requested_run and tokens:
        return CliRequest(requested_run, False, False, False, False, None, None), (
            "run does not accept a duration."
        )

    if requested_clear and tokens:
        return CliRequest(requested_run, requested_clear, False, False, False, None, None), (
            "clear does not accept a duration."
        )

    if requested_mem and any(token.startswith("+") for token in tokens_lower):
        return CliRequest(requested_run, False, False, False, False, None, None), (
            "Cannot combine mem and +duration."
        )

    if requested_config and tokens:
        return CliRequest(requested_run, False, False, False, False, None, None), (
            "config does not accept a duration."
        )

    if requested_mem:
        mem_duration = " ".join(tokens) if tokens else None
        return (
            CliRequest(
                requested_run,
                requested_clear,
                requested_intake,
                requested_mem,
                requested_config,
                None,
                mem_duration,
            ),
            None,
        )

    if requested_config:
        return (
            CliRequest(
                requested_run,
                requested_clear,
                requested_intake,
                requested_mem,
                requested_config,
                None,
                None,
            ),
            None,
        )

    duration = " ".join(tokens) if tokens else None
    if duration is not None and not requested_intake:
        return CliRequest(requested_run, False, False, False, False, None, None), (
            "Duration requires an intake command (use intake 3h or +3h)."
        )
    return (
        CliRequest(
            requested_run,
            requested_clear,
            requested_intake,
            requested_mem,
            requested_config,
            duration,
            None,
        ),
        None,
    )
