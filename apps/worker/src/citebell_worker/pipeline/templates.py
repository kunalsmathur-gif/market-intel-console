"""Report templates: the fixed section structure for each report type (PRD §7 report
schedule table).

A template only says *what a section is allowed to draw on* — it never invents content.
Whether a section actually renders depends entirely on which claims survived the gate step
(fail-closed): a field with no connector yet, or a quiet news day, means an honestly withheld
section with a reason, not a placeholder value made up by a model.

Several fields the PRD's report schedule names aren't collected yet (GIFT Nifty, live global
index/commodity futures, PCR/max pain/OI buildup, the economic calendar) — those need a paid
feed or a new connector the PRD defers to V1 (§8.4, §8.11). Their sections are declared here so
they start rendering automatically once that data exists, rather than being left out of the
template altogether.
"""

from dataclasses import dataclass

from citebell_schemas import ReportType


@dataclass(frozen=True)
class SectionTemplate:
    key: str
    title: str
    # citebell_worker.pipeline.collect.FIELD_UNITS keys this section may show, in display
    # order. A field with no published claim this run is silently skipped, not withheld.
    market_fields: tuple[str, ...] = ()
    # Whether this section may also draw on published NEWS_EVENT claims not already claimed
    # by an earlier section in the same report (first come, first served within one run).
    include_news: bool = False


@dataclass(frozen=True)
class ReportTemplate:
    report_type: ReportType
    sections: tuple[SectionTemplate, ...]


REPORT_TEMPLATES: dict[ReportType, ReportTemplate] = {
    ReportType.MORNING: ReportTemplate(
        ReportType.MORNING,
        (
            SectionTemplate(
                "global_opening_check",
                "Global Opening Check",
                # GIFT Nifty and S&P/Nasdaq futures need a paid feed or a news-reported
                # claim (PRD §8.4); US 10Y and crypto are the only global feeds V0 has.
                market_fields=("us10y.yield", "bitcoin.price_usd", "btc.dominance_pct"),
                include_news=True,
            ),
            SectionTemplate(
                "india_setup_and_flows",
                "India Setup & Flows",
                market_fields=(
                    "nifty50.close",
                    "banknifty.close",
                    "india_vix.ltp",
                    "fii.net_cash_cr",
                    "dii.net_cash_cr",
                ),
            ),
            # PCR, put base/call wall, max pain, long/short buildup, F&O ban: no
            # connector computes these yet (PRD §8.11 derivatives panel is V1+).
            SectionTemplate("data_outlook", "Data Outlook"),
        ),
    ),
    ReportType.MIDDAY: ReportTemplate(
        ReportType.MIDDAY,
        (
            SectionTemplate(
                "midday_markets",
                "Mid-day Markets",
                market_fields=("nifty50.ltp", "banknifty.ltp", "india_vix.ltp"),
                include_news=True,
            ),
        ),
    ),
    ReportType.EOD: ReportTemplate(
        ReportType.EOD,
        (
            SectionTemplate(
                "eod_insights",
                "End-of-day Insights",
                market_fields=(
                    "nifty50.close",
                    "sensex.close",
                    "banknifty.close",
                    "india_vix.ltp",
                ),
                include_news=True,
            ),
        ),
    ),
    ReportType.FLOWS: ReportTemplate(
        ReportType.FLOWS,
        (
            SectionTemplate(
                "institutional_flows",
                "Institutional Flows",
                market_fields=("fii.net_cash_cr", "dii.net_cash_cr"),
            ),
        ),
    ),
}
