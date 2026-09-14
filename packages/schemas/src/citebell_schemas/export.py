"""Write every model as one JSON Schema bundle; the web app turns it into TypeScript types.

Usage: python -m citebell_schemas.export packages/schemas/citebell.schema.json
"""

import json
import sys
from pathlib import Path
from typing import Any

from pydantic.json_schema import models_json_schema

from .models import Claim, Evidence, GateDecision, RunKey, Source


def build_schema() -> dict[str, Any]:
    _, schema = models_json_schema(
        [(model, "serialization") for model in (Source, Evidence, Claim, GateDecision, RunKey)],
        title="Citebell",
    )
    for definition in schema.get("$defs", {}).values():
        for prop in definition.get("properties", {}).values():
            _drop_titles(prop)
    return schema


def _drop_titles(node: Any) -> None:
    """Field titles make the TypeScript generator emit an alias per field; models keep theirs."""
    if isinstance(node, dict):
        node.pop("title", None)
        for child in node.values():
            _drop_titles(child)
    elif isinstance(node, list):
        for child in node:
            _drop_titles(child)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m citebell_schemas.export <output.json>")
    out = Path(sys.argv[1])
    out.write_text(json.dumps(build_schema(), indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
