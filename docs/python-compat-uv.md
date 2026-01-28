# Python Compatibility Checks (uv / CPython 3.10-3.13)

This document summarizes commands to verify CPython 3.10 / 3.11 / 3.12 / 3.13 using uv, based on `requires-python = ">=3.10"` in `pyproject.toml`.

## Prerequisites

- uv is installed
- run from the repository root
- dependencies are listed in `pyproject.toml` (dev: pytest / ruff / pyright)

## Common Steps (run per version; no activate required)

Repeat the steps below for **3.10 / 3.11 / 3.12 / 3.13**. Using `.venv/bin/python` means no `activate` is needed.

```bash
# Example: 3.12
uv venv --python 3.12
uv pip install -p .venv/bin/python -e ".[dev]"
uv run -p .venv/bin/python pytest
uv run -p .venv/bin/python ruff check
uv run -p .venv/bin/python pyright
```

## Per-Version Commands

### CPython 3.10

```bash
uv venv --clear --python 3.10
uv pip install -p .venv/bin/python -e ".[dev]"
uv run -p .venv/bin/python pytest
uv run -p .venv/bin/python ruff check
uv run -p .venv/bin/python pyright
```

### CPython 3.11

```bash
uv venv --clear --python 3.11
uv pip install -p .venv/bin/python -e ".[dev]"
uv run -p .venv/bin/python pytest
uv run -p .venv/bin/python ruff check
uv run -p .venv/bin/python pyright
```

### CPython 3.12

```bash
uv venv --clear --python 3.12
uv pip install -p .venv/bin/python -e ".[dev]"
uv run -p .venv/bin/python pytest
uv run -p .venv/bin/python ruff check
uv run -p .venv/bin/python pyright
```

### CPython 3.13

```bash
uv venv --clear --python 3.13
uv pip install -p .venv/bin/python -e ".[dev]"
uv run -p .venv/bin/python pytest
uv run -p .venv/bin/python ruff check
uv run -p .venv/bin/python pyright
```

## Notes

- For compatibility checks, prefer `uv run -p .venv/bin/python pytest`.
