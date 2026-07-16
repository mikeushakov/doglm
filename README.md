# DogLM

An open benchmark measuring whether an LLM, asked to generate a video game that contains a dog but given no instruction about the dog, spontaneously lets the player pet it.

The benchmark is named after the game-design rule made popular by the "Can You Pet the Dog?" project ([X](https://x.com/CanYouPetTheDog), [Bluesky](https://bsky.app/profile/canyoupetthedog.com)): if a game has a dog, players expect to pet it. Good games let them, yet no one writes this into a specification. DogLM tests whether a model applies the rule on its own.

## What it measures

A model is given a product requirements document (PRD) for a tiny browser game. The PRD describes a conventional goal (deliver letters, harvest crops, escape a maze) and mentions, in one sentence, that a dog is present in the world. The PRD never asks for any way to interact with the dog. The model returns a single self-contained HTML game, which runs on its own with no further model calls. We then check the generated code: can the player pet the dog?

There are five games, ordered by how hard it is for a model to add petting on its own. Difficulty rises along two axes: whether the game already has an interact key (a keyboard button that triggers an action near an object), and how the dog is described, from a close companion down to a barely-present background figure.

| # | Game | Goal | Dog description | Difficulty |
|---|------|------|-----------------|------------|
| 1 | Mail Courier | Deliver five letters, press E at each house | "A dog follows the player around the village at a short distance." | 1 (easiest) |
| 2 | Harvest Rush | Harvest ten crops with Space before a timer | "The farmer's dog roams the field while the player works." | 2 |
| 3 | Night Watchman | Check four doors by standing near each | "A dog keeps the watchman company on his rounds." | 3 |
| 4 | Gem Maze | Collect five gems by walking over them | "A dog wanders the maze corridors, uninvolved with the gems or the gate." | 4 |
| 5 | Firefly Meadow | Catch eight fireflies by walking into them | "A dog is somewhere in the meadow." | 5 (hardest) |

Items 1 and 2 have an interact key; items 3 to 5 do not, so petting must be invented from scratch. Each PRD exists in two versions: **uncued** (no hint of any kind) and **cued** (one extra sentence permitting genre-typical additions, without naming the dog).

## Scoring

Each generated game is scored on the dog:

- **2** — the player can pet the dog: a deliberate action aimed at the dog (a keypress near it, a click on it) produces a dog-specific response (a message, hearts, a triggered animation).
- **1** — the dog reacts to the player's presence or contact without any deliberate input (wags when near, barks on collision). An interaction, but a weaker one.
- **0** — the dog exists and moves, but nothing the player does reaches it.

Two non-numeric states are excluded from scoring rather than counted:

- **NO_DOG** — the game runs but contains no dog at all.
- **FAILED** — the game does not parse, is truncated, or cannot be checked.

Scoring is done by an LLM judge that reads the game's source and returns a score plus the code lines it relied on. A `node --check` syntax gate runs first, so a game whose JavaScript does not parse is marked FAILED and never scored.

## Repository contents

```
run_benchmark.py       generate games from PRDs and score them
analyze_reasoning.py   optional: analyse models' reasoning traces
prds/                  the ten PRDs (five games x uncued/cued)
CITATION.cff           how to cite this repository
README.md              this file
```

## Requirements

- Python 3.9+ with `requests` (`pip install requests`)
- Node.js (for the JavaScript syntax check; `node --version` to confirm)
- An [OpenRouter](https://openrouter.ai) account and API key

## Quick start

```bash
pip install requests
export OPENROUTER_API_KEY="sk-or-..."

# generate and score all ten PRDs for one model
python run_benchmark.py --model deepseek/deepseek-chat --runs 1
```

Results are written to `manifest.csv` (one row per generated game) and the games to `games/`. Verify model IDs on [openrouter.ai/models](https://openrouter.ai/models); an incorrect ID is the most common error.

**By default each game is generated once.** A single generation is one sample of a variable behaviour. For robust results, raise `--runs` to generate and score each game several times:

```bash
python run_benchmark.py --model deepseek/deepseek-chat --runs 5
```

### Running several models

Pass multiple model IDs to `--model`; they run in parallel:

​```bash
python run_benchmark.py \
  --model anthropic/claude-fable-5 openai/gpt-5.6-sol google/gemini-3.1-pro-preview \
  --runs 1 --workers 6
​```

All model-by-PRD-by-run jobs are distributed across `--workers` parallel requests. Results are written to `manifest.csv` once at the end. If you see frequent HTTP 429 (rate limit) messages, lower `--workers`.

### Useful flags

- `--runs N` — generations per PRD (default 1)
- `--prds FILE ...` — run only specific PRD files
- `--no-judge` — generate only, skip scoring
- `--judge-only` — re-score a model's existing games without regenerating (used after editing the rubric)
- `--temperature T` — sampling temperature (default 1.0; not comparable across providers)
- `--workers N` — number of parallel requests in flight (default 4; start low, 4-6, to respect provider rate limits)

The judge model is set by the `JUDGE_MODEL` constant near the top of `run_benchmark.py`.

## Reading the output

`manifest.csv` has one row per game. Key columns:

- `model`, `item`, `game_name`, `condition`, `run` — what was generated
- `game_file` — the saved HTML filename
- `completion_tokens`, `reasoning_tokens`, `cost_usd` — generation cost
- `finish_reason` — `stop` (finished) or `length` (hit the token ceiling; truncated)
- `syntax_ok` — whether the game's JavaScript parses
- `judge_score` — `0`, `1`, `2`, `NO_DOG`, or `FAILED`
- `judge_evidence` — the code the judge based its score on

A model's score per condition is the sum of its five game scores (0 to 10), counting only numeric scores; NO_DOG and FAILED are excluded.

## Optional: reasoning-trace analysis

For models that expose reasoning tokens, `analyze_reasoning.py` reads each trace and classifies whether the model's thinking showed any sign of considering player-dog interaction, as opposed to treating the dog only as a moving decoration. It distinguishes genuine consideration from mechanical mentions (following distance, collision), verifies every quote against the source trace, and joins each result to the game's score.

```bash
python analyze_reasoning.py --reasoning-dir reasoning --manifest manifest.csv --out reasoning_analysis.csv
```

The classifier judge is Claude Sonnet by default (set at the top of the script), which suits this nuance-reading task better than a smaller model. The classification prompt is a starting point, not a final instrument: it can be tuned to detect a model's implicit intent more sharply, and contributions here are welcome.

## Adding or changing models

Any model available on OpenRouter can be tested: pass its exact ID to `--model`. No code changes are needed.

## License

MIT. See `LICENSE`.

## Citation

If you use DogLM, please cite it:

```bibtex
@misc{ushakov2026doglm,
  author       = {Ushakov, Mike},
  title        = {DogLM: an open benchmark for spontaneous pet-the-dog mechanics in LLM-generated games},
  year         = {2026},
  howpublished = {\url{https://github.com/mikeushakov/doglm}}
}
```
