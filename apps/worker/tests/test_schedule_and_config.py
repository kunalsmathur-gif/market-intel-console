from datetime import date, time
from pathlib import Path

import pytest

from citebell_schemas import ReportType, SourceTier
from citebell_worker.config import EXAMPLE_PRIVATE_CONFIG
from citebell_worker.private_config import PrivateConfigError, load_private_config
from citebell_worker.schedule import IST, SCHEDULE, is_trading_day, load_holidays


def test_morning_timings_match_the_prd() -> None:
    morning = SCHEDULE[ReportType.MORNING]
    assert morning.collect_start == time(7, 30)
    assert morning.cutoff == time(8, 15)
    assert morning.publish_target == time(8, 38)
    assert morning.deadline_at(date(2026, 9, 15)).tzinfo is IST


def test_flows_waits_for_the_upload() -> None:
    assert SCHEDULE[ReportType.FLOWS].collect_start is None


def test_weekends_and_holidays_are_not_trading_days(tmp_path: Path) -> None:
    holidays_file = tmp_path / "h.txt"
    holidays_file.write_text("# comment\n2026-10-02  # example date\n\n", encoding="utf-8")
    holidays = load_holidays(holidays_file)
    assert holidays == {date(2026, 10, 2)}
    assert not is_trading_day(date(2026, 10, 2), holidays)
    assert not is_trading_day(date(2026, 9, 19), holidays)  # Saturday
    assert is_trading_day(date(2026, 9, 18), holidays)


def test_example_private_config_loads() -> None:
    config = load_private_config(EXAMPLE_PRIVATE_CONFIG)
    assert {s.id for s in config.sources} >= {"example-exchange", "example-wire"}
    assert "blog.example" not in config.allowed_domains(SourceTier.T3)  # inactive
    assert "wire.example" in config.allowed_domains()
    assert "Never write a number" in config.prompt("extract")
    with pytest.raises(PrivateConfigError):
        config.prompt("no-such-step")


def test_duplicate_source_ids_are_rejected(tmp_path: Path) -> None:
    entry = '[[source]]\nid = "dup"\nname = "A"\ndomain = "a.example"\ntier = "T2"\nkind = "rss"\n'
    (tmp_path / "sources.toml").write_text(entry * 2, encoding="utf-8")
    with pytest.raises(PrivateConfigError, match="duplicate"):
        load_private_config(tmp_path)
