"""HTML reporting for four-player self-play games."""

from __future__ import annotations

import html
from pathlib import Path

from .engine import Game, TURN_ORDER


def write_html_report(game: Game, path: str | Path, seconds_per_side: float = 60.0, increment_seconds: float = 7.0) -> Path:
    """Write a standalone HTML report showing moves, scores, and PGN."""
    output = Path(path)
    output.write_text(render_html_report(game, seconds_per_side, increment_seconds), encoding="utf-8")
    return output


def render_html_report(game: Game, seconds_per_side: float = 60.0, increment_seconds: float = 7.0) -> str:
    rows = []
    for line in game.pgn:
        turn, moves = line.split(". ", 1)
        cells = [html.escape(turn)] + [html.escape(move) for move in moves.split(" .. ")]
        cells.extend([""] * (5 - len(cells)))
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    score_items = "".join(
        f"<li><strong>{player.value}</strong>: {game.scores[player]} points</li>" for player in TURN_ORDER
    )
    pgn = html.escape("\n".join(game.pgn))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Four-Player Modern Chess Self-Play</title>
  <style>
    :root {{ color-scheme: dark; --bg: #111827; --panel: #1f2937; --text: #f9fafb; --muted: #9ca3af; --accent: #38bdf8; }}
    body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: var(--bg); color: var(--text); }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px; }}
    .hero, .card {{ background: var(--panel); border: 1px solid #374151; border-radius: 18px; padding: 24px; box-shadow: 0 16px 50px #0006; }}
    h1 {{ margin: 0 0 8px; }}
    .meta {{ color: var(--muted); margin: 0; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 12px; }}
    th, td {{ border-bottom: 1px solid #374151; padding: 10px 12px; text-align: left; font-variant-numeric: tabular-nums; }}
    th {{ color: var(--accent); background: #0f172a; position: sticky; top: 0; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #030712; border-radius: 12px; padding: 16px; max-height: 520px; overflow: auto; }}
    ul {{ line-height: 1.9; }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Four-Player Modern Chess Self-Play</h1>
      <p class="meta">Clock: {seconds_per_side:g}+{increment_seconds:g}. Turn order: Red, Blue, Yellow, Green.</p>
    </section>
    <section class="grid">
      <article class="card">
        <h2>Scores</h2>
        <ul>{score_items}</ul>
      </article>
      <article class="card">
        <h2>Game PGN</h2>
        <pre>{pgn}</pre>
      </article>
    </section>
    <section class="card" style="margin-top: 18px;">
      <h2>Moves Played</h2>
      <table>
        <thead><tr><th>#</th><th>Red</th><th>Blue</th><th>Yellow</th><th>Green</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""
