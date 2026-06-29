# Four-Player Modern Chess Bot

A fast, deterministic four-player chess engine and self-play bot for the chess.com Modern setup. The project models Red, Blue, Yellow, and Green players, applies chess.com-style scoring bonuses, and emits a four-player PGN with moves separated by `..`.

## Quick start

```bash
python -m four_player_chess --seed 7 --time 60 --increment 7 --html game.html
```

Run tests:

```bash
python -m pytest
```

## Features

- Modern 14x14 four-player board geometry with Red, Blue, Yellow, Green turn order.
- Side-specific pawn promotion targets:
  - Red promotes on rank 8.
  - Blue promotes on file `h`.
  - Yellow promotes on rank 7.
  - Green promotes on file `g`.
- Forced denoted-queen promotions (`D`) worth one point when captured.
- Capture, checkmate, stalemate, multi-check, threefold, insufficient-material, and 50-full-turn scoring rules.
- Four self-play bots that use iterative deepening, tactical move ordering, and a fast heuristic evaluation to maximize finishing placement.
- Standalone HTML reports showing the moves played, final scores, and full PGN for sharing game results.
