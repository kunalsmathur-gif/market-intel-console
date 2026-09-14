"""Vocabulary shared by the worker, the database and the web app (PRD §7, §8.8)."""

from enum import StrEnum


class ReportType(StrEnum):
    MORNING = "morning"  # Morning Insights, ready 08:45 IST
    MIDDAY = "midday"  # Mid-day Markets, ready 12:15 IST
    EOD = "eod"  # End-of-day Insights, ready 16:00 IST
    FLOWS = "flows"  # Institutional Flows, ready 20:00 IST


class SourceTier(StrEnum):
    T1 = "T1"  # primary: exchange, regulator, central bank, statistics office, company filing
    T2 = "T2"  # established press and wires
    T3 = "T3"  # context only, never enough to publish
    TX = "TX"  # never publishable: social media, Telegram, unnamed


class SourceKind(StrEnum):
    RSS = "rss"
    API = "api"
    SEARCH = "search"
    MANUAL = "manual"  # files the owner uploads, e.g. NSE FII/DII


class EvidenceKind(StrEnum):
    FEED = "feed"  # a number from a data API or an official file
    ARTICLE = "article"  # a web page that states the claim


class ClaimType(StrEnum):
    MARKET_NUMBER = "market_number"
    NEWS_EVENT = "news_event"
    FORECAST = "forecast"
    OPINION = "opinion"


class Badge(StrEnum):
    PRIMARY_DATA = "primary_data"
    NEWS_REPORTED = "news_reported"
    VERIFIED = "verified"
    ATTRIBUTED_VIEW = "attributed_view"
    SINGLE_SOURCE = "single_source"
    WITHHELD = "withheld"


class Verdict(StrEnum):
    PUBLISH = "publish"
    WITHHOLD = "withhold"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PUBLISHED = "published"
    PARTIAL = "partial"  # some sections withheld
    WITHHELD = "withheld"
    FAILED = "failed"
