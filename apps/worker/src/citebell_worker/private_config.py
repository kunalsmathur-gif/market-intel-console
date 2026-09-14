"""Load prompts, the source registry and NSE holidays from the private config repo.

The public repo holds only the loader and a clearly fake example. Layout of the private repo:

    sources.toml        [[source]] tables matching citebell_schemas.Source
    nse_holidays.txt    one ISO date per line
    prompts/<step>.md   one system prompt per pipeline step
"""

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from citebell_schemas import Source, SourceTier

from .schedule import load_holidays


class PrivateConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrivateConfig:
    root: Path
    sources: tuple[Source, ...]
    holidays: frozenset[date]

    def prompt(self, step: str) -> str:
        path = self.root / "prompts" / f"{step}.md"
        if not path.is_file():
            raise PrivateConfigError(f"missing prompt for step {step!r}: {path}")
        return path.read_text(encoding="utf-8")

    def allowed_domains(self, *tiers: SourceTier) -> frozenset[str]:
        """Domains that search results may come from; everything else is dropped in code."""
        wanted = set(tiers) or {SourceTier.T1, SourceTier.T2}
        return frozenset(s.domain for s in self.sources if s.active and s.tier in wanted)


def load_private_config(root: Path) -> PrivateConfig:
    if not root.is_dir():
        raise PrivateConfigError(f"private config directory not found: {root}")

    sources_path = root / "sources.toml"
    try:
        raw = tomllib.loads(sources_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PrivateConfigError(f"cannot read {sources_path}: {exc}") from exc
    sources = tuple(Source.model_validate(entry) for entry in raw.get("source", []))
    ids = [s.id for s in sources]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise PrivateConfigError(f"duplicate source ids in {sources_path}: {duplicates}")

    holidays_path = root / "nse_holidays.txt"
    holidays = load_holidays(holidays_path) if holidays_path.is_file() else frozenset()
    return PrivateConfig(root=root, sources=sources, holidays=holidays)
