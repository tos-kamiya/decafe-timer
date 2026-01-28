import pytest

from decafe_timer.cli import normalize_cli_request, parse_cli_args
from decafe_timer.duration import parse_duration


def _request_from(argv):
    args = parse_cli_args(argv)
    return normalize_cli_request(args)


def test_run_clear_conflict():
    request, error = _request_from(["run", "clear"])
    assert error is not None
    assert "Cannot combine run, intake, mem, config, and clear." in error
    assert request.run is True
    assert request.clear is False
    assert request.config is False


def test_run_with_duration_rejected():
    request, error = _request_from(["run", "10m"])
    assert error is not None
    assert "run does not accept a duration." in error
    assert request.run is True
    assert request.clear is False


def test_clear_alias():
    request, error = _request_from(["clear"])
    assert error is None
    assert request.run is False
    assert request.clear is True
    assert request.config is False
    assert request.duration is None


def test_clear_zero_alias():
    request, error = _request_from(["0"])
    assert error is None
    assert request.run is False
    assert request.clear is True
    assert request.config is False
    assert request.duration is None


def test_clear_with_duration_rejected():
    request, error = _request_from(["clear", "10m"])
    assert error is not None
    assert "clear does not accept a duration." in error
    assert request.run is False
    assert request.clear is True
    assert request.config is False


def test_intake_alias_with_duration():
    request, error = _request_from(["intake", "10m"])
    assert error is None
    assert request.intake is True
    assert request.config is False
    assert request.duration == "10m"


def test_intake_plus_duration():
    request, error = _request_from(["+10m"])
    assert error is None
    assert request.intake is True
    assert request.config is False
    assert request.duration == "10m"


def test_intake_without_duration():
    request, error = _request_from(["intake"])
    assert error is None
    assert request.intake is True
    assert request.config is False
    assert request.duration is None


def test_mem_show():
    request, error = _request_from(["mem"])
    assert error is None
    assert request.mem is True
    assert request.config is False
    assert request.mem_duration is None


def test_mem_set():
    request, error = _request_from(["mem", "3h"])
    assert error is None
    assert request.mem is True
    assert request.config is False
    assert request.mem_duration == "3h"


def test_mem_run_conflict():
    request, error = _request_from(["run", "mem"])
    assert error is not None
    assert "Cannot combine run, intake, mem, config, and clear." in error
    assert request.run is True
    assert request.config is False


def test_intake_mem_conflict():
    request, error = _request_from(["intake", "mem"])
    assert error is not None
    assert "Cannot combine run, intake, mem, config, and clear." in error


def test_config_show():
    request, error = _request_from(["config"])
    assert error is None
    assert request.config is True
    assert request.mem is False
    assert request.intake is False


def test_config_with_duration_rejected():
    request, error = _request_from(["config", "3h"])
    assert error is not None
    assert "config does not accept a duration." in error


def test_config_run_conflict():
    request, error = _request_from(["run", "config"])
    assert error is not None
    assert "Cannot combine run, intake, mem, config, and clear." in error


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
