"""Data connectors: real fetches only, no invented numbers (PRD §8.4).

Each connector reads its source's id and tier from the private registry (a
citebell_schemas.Source), so classifying a source stays a config change, not a code
change. Connectors raise DataSourceError on anything unusable; the caller decides
whether that withholds one field or the whole run.
"""

from .base import DataSourceError, Observation, get_with_retries
from .coingecko import btc_dominance, simple_prices
from .fred import latest_observation as fred_latest_observation
from .rss import FeedItem, fetch_feed

__all__ = [
    "DataSourceError",
    "Observation",
    "get_with_retries",
    "btc_dominance",
    "simple_prices",
    "fred_latest_observation",
    "FeedItem",
    "fetch_feed",
]
