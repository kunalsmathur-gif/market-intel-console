"""The report timetable in IST (PRD §7 report schedule, §8.11 timings).

Morning Insights is fully specified: collect 07:30, cutoff 08:15, publish target 08:38,
hard deadline 08:45. The other reports keep the same shape: collection starts 45 minutes
before cutoff and the publish target sits 7 minutes before the deadline.
Institutional Flows has no fixed cutoff; it starts when NSE's file is uploaded.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from citebell_schemas import ReportType

IST = ZoneInfo("Asia/Kolkata")
COLLECT_LEAD = timedelta(minutes=45)
PUBLISH_BUFFER = timedelta(minutes=7)


@dataclass(frozen=True)
class ReportSlot:
    report_type: ReportType
    title: str
    deadline: time
    cutoff: time | None  # None: triggered by an upload rather than the clock

    @property
    def publish_target(self) -> time:
        return _shift(self.deadline, -PUBLISH_BUFFER)

    @property
    def collect_start(self) -> time | None:
        return None if self.cutoff is None else _shift(self.cutoff, -COLLECT_LEAD)

    def deadline_at(self, trading_date: date) -> datetime:
        return datetime.combine(trading_date, self.deadline, tzinfo=IST)


SCHEDULE: dict[ReportType, ReportSlot] = {
    ReportType.MORNING: ReportSlot(ReportType.MORNING, "Morning Insights", time(8, 45), time(8, 15)),
    ReportType.MIDDAY: ReportSlot(ReportType.MIDDAY, "Mid-day Markets", time(12, 15), time(11, 50)),
    ReportType.EOD: ReportSlot(ReportType.EOD, "End-of-day Insights", time(16, 0), time(15, 35)),
    ReportType.FLOWS: ReportSlot(ReportType.FLOWS, "Institutional Flows", time(20, 0), None),
}


def _shift(t: time, delta: timedelta) -> time:
    return (datetime.combine(date(2000, 1, 3), t) + delta).time()


def load_holidays(path: Path) -> frozenset[date]:
    """Read NSE trading holidays: one ISO date per line, '#' starts a comment."""
    days: set[date] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            days.add(date.fromisoformat(line))
    return frozenset(days)


def is_trading_day(day: date, holidays: frozenset[date]) -> bool:
    return day.weekday() < 5 and day not in holidays


def now_ist() -> datetime:
    return datetime.now(IST)
