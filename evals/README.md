# Evals

The eval harness and bake-off runner will live here (PRD §8.10, §8.12). **Test data doesn't:** golden claim sets, trap cases, labelled stories and recorded trading days go in the private config repo, next to the prompts, so that the traps can't leak into public training data.

Planned layout:

| Path | Suite |
|---|---|
| `pipeline/` | Extraction recall and precision, wrongly accepted claims, quote support, no model-written numbers |
| `bakeoff/` | Runs every candidate model on the same sets three times and records accuracy, latency and cost |
| `replay/` | Replays the last 20 trading days from saved inputs, plus failure drills |

The publish-gate rules already have unit tests in `apps/worker/tests/test_gate.py`, covering syndicated copies, stale stories, TX sources, broken links and number tolerances.
