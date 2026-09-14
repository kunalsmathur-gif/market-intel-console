# Example private config

A fake stand-in for the private config repo, used by tests and local dry runs. **The real prompts, source registry and eval goldens live in a separate private repo**; point `PRIVATE_CONFIG_DIR` at your checkout of it.

- `sources.toml`: the source registry. Each `[[source]]` matches `citebell_schemas.Source`.
- `nse_holidays.txt`: NSE trading holidays, one ISO date per line. Copy them from NSE's official holiday circular. The example is empty on purpose, so the worker treats every weekday as a trading day and warns you.
- `prompts/<step>.md`: one system prompt per pipeline step (`classify`, `extract`, `verify`, `write`, `qa`).
