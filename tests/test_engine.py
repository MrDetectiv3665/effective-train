from four_player_chess.engine import Game, Piece, Player, run_self_play


def test_modern_setup_has_four_sides_and_moves():
    game = Game.modern(seed=1)
    assert {piece.owner for piece in game.board.values()} == set(Player)
    assert game.current_player == Player.RED
    assert game.legal_moves(Player.RED)


def test_forced_denoted_queen_promotion_is_one_point_capture():
    game = Game(board={(4, 7): Piece(Player.RED, "P"), (5, 9): Piece(Player.BLUE, "K"), (10, 10): Piece(Player.RED, "K")})
    move = next(move for move in game.legal_moves(Player.RED) if move.end == (4, 8))
    game.apply_move(move)
    assert game.board[(4, 8)].kind == "D"
    game.board[(4, 9)] = Piece(Player.BLUE, "R")
    game.board[(4, 8)] = Piece(Player.RED, "D")
    capture = next(move for move in game.legal_moves(Player.BLUE) if move.end == (4, 8))
    game.apply_move(capture)
    assert game.scores[Player.BLUE] == 1


def test_self_play_emits_four_player_pgn():
    game = run_self_play(seed=3, seconds_per_side=0.01, max_rounds=2)
    assert game.pgn
    assert game.pgn[0].startswith("1. ")
    assert " .. " in game.pgn[0]


def test_modern_real_queen_squares_are_correct():
    game = Game.modern(seed=2)
    assert game.board[(7, 1)] == Piece(Player.RED, "Q")
    assert game.board[(1, 8)] == Piece(Player.BLUE, "Q")
    assert game.board[(8, 14)] == Piece(Player.YELLOW, "Q")
    assert game.board[(14, 7)] == Piece(Player.GREEN, "Q")


def test_promotion_notation_keeps_pawn_prefix():
    game = Game(board={(4, 7): Piece(Player.RED, "P"), (10, 10): Piece(Player.RED, "K"), (5, 9): Piece(Player.BLUE, "K")})
    move = next(move for move in game.legal_moves(Player.RED) if move.end == (4, 8))
    assert game.apply_move(move).startswith("d7-d8=D")
