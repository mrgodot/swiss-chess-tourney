# Swiss Chess Tourney

Object classes to run a Swiss-system chess tournament on [lichess.org](https://lichess.org). The tournament is intended
to be run from a Jupyter notebook (or Google Colab). A Google Sheet acts as the database and historical record,
allowing players to track and update the tournament state.

## Modules

| Module | Description |
|---|---|
| `tournament.tournament` | Main entry point for managing rounds, pairings, and game sheets |
| `tournament.player` | Player representation — Elo, score, and game history |
| `tournament.game` | Single lichess game with round, players, outcome, and opening |
| `tournament.optimization` | Optimal Swiss pairings via mixed-integer linear programming (GLPK) |
| `tournament.lichess` | Lichess API helpers — challenges, PGN export, game results |
| `tournament.utils` | Shared enums, Elo odds, and timestamp utilities |

## Pairing Optimization

Round pairings are determined by minimizing a cost function over all possible player matchups using
[CVXPY](https://www.cvxpy.org/) with the GLPK mixed-integer solver. The cost function penalizes score differences,
rematches, intra-federation pairings, and Elo gaps (decaying by round so score delta dominates later).

## Setup

Install runtime dependencies:

```shell
pip install -r requirements.txt
```

## Development

Install pre-commit hooks (one-time setup per clone):

```shell
pip install pre-commit
pre-commit install
```

Pre-commit runs the following hooks on every commit:

- **black** — code formatting (line length 120)
- **isort** — import sorting (black-compatible profile)
- **flake8** — linting (line length 120, reads config from `pyproject.toml` via `flake8-pyproject`)

Tool configuration is centralized in `pyproject.toml`. Run hooks manually with:

```shell
pre-commit run --all-files
```
