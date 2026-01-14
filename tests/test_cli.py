import pytest

from decafe_timer.cli import normalize_cli_request, parse_cli_args
from decafe_timer.duration import parse_duration


def _request_from(argv):
    args = parse_cli_args(argv)
    return normalize_cli_request(args)


def test_run_clear_conflict():
    request, error = _request_from(["run", "clear"])
    assert error is not None
    assert "Cannot combine run and clear." in error
    assert request.run is True
    assert request.clear is True


def test_run_clear_flags_conflict():
    request, error = _request_from(["--run", "--clear"])
    assert error is not None
    assert "Cannot combine run and clear." in error
    assert request.run is True
    assert request.clear is True


def test_run_with_clear_argument_conflict():
    request, error = _request_from(["--run", "clear"])
    assert error is not None
    assert "Cannot combine run and clear." in error
    assert request.run is True
    assert request.clear is True


def test_run_with_clear_flag_conflict():
    request, error = _request_from(["run", "--clear"])
    assert error is not None
    assert "Cannot combine run and clear." in error
    assert request.run is True
    assert request.clear is True


def test_run_alias_with_duration():
    request, error = _request_from(["run", "10m"])
    assert error is None
    assert request.run is True
    assert request.clear is False
    assert request.duration == "10m"


def test_run_flag_with_duration():
    request, error = _request_from(["--run", "10m"])
    assert error is None
    assert request.run is True
    assert request.clear is False
    assert request.duration == "10m"


def test_clear_alias():
    request, error = _request_from(["clear"])
    assert error is None
    assert request.run is False
    assert request.clear is True
    assert request.duration is None


def test_clear_zero_alias():
    request, error = _request_from(["0"])
    assert error is None
    assert request.run is False
    assert request.clear is True
    assert request.duration is None


def test_clear_with_duration_rejected():
    request, error = _request_from(["clear", "10m"])
    assert error is not None
    assert "clear does not accept a duration." in error
    assert request.run is False
    assert request.clear is True


def test_parse_single_duration():
    remaining, total = parse_duration("1h30m")
    assert remaining == 5400
    assert total == 5400


def test_parse_colon_format():
    remaining, total = parse_duration("0:01:00")
    assert remaining == 60
    assert total == 60


def test_parse_remaining_total():
    remaining, total = parse_duration("3h/5h")
    assert remaining == 10800
    assert total == 18000


def test_parse_invalid_zero():
    with pytest.raises(ValueError):
        parse_duration("0")
