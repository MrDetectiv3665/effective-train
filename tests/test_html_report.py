from four_player_chess.engine import run_self_play
from four_player_chess.html_report import render_html_report


def test_html_report_contains_clock_moves_scores_and_pgn():
    game = run_self_play(seed=4, seconds_per_side=0.01, increment_seconds=0, max_rounds=1)
    page = render_html_report(game, seconds_per_side=60, increment_seconds=7)
    assert "Clock: 60+7" in page
    assert "Moves Played" in page
    assert "Game PGN" in page
    assert game.pgn[0].split(" .. ")[0] in page
