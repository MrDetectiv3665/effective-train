from pathlib import Path


def test_root_launcher_opens_report_in_new_tab():
    page = Path("index.html").read_text(encoding="utf-8")
    assert "window.open('four_player_chess_report.html', '_blank'" in page
    assert "Fallback link" in page


def test_static_report_shows_clock_moves_and_pgn():
    page = Path("four_player_chess_report.html").read_text(encoding="utf-8")
    assert "1 minute + 7 second increment" in page
    assert "Real queens: Red g1, Blue a8, Yellow h14, Green n7" in page
    assert "Play full game live" in page
    assert "Moves played" in page
    assert "PGN of this game" in page
    assert page.count(" .. ") > 40
