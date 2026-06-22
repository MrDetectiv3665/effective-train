"""Fast four-player chess self-play engine for the Modern chess.com setup.

The implementation favors speed and deterministic tactical play over exhaustive rule UI
integration. It is intentionally standalone so it can be embedded in a chess.com bridge
or run locally to produce four-player PGN transcripts.
"""

from __future__ import annotations

import argparse
import copy
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

FILES = "abcdefghijklmn"
BOARD_SIZE = 14
CAPTURE_POINTS = {"P": 1, "D": 1, "N": 3, "B": 5, "R": 5, "Q": 9, "K": 20}
MAJOR_PIECES = {"K", "Q", "R", "B", "N"}


class Player(str, Enum):
    RED = "Red"
    BLUE = "Blue"
    YELLOW = "Yellow"
    GREEN = "Green"


TURN_ORDER = [Player.RED, Player.BLUE, Player.YELLOW, Player.GREEN]
PROMOTION_TARGETS = {
    Player.RED: lambda sq: sq[1] == 8,
    Player.BLUE: lambda sq: sq[0] == 8,  # h-file
    Player.YELLOW: lambda sq: sq[1] == 7,
    Player.GREEN: lambda sq: sq[0] == 7,  # g-file
}
PAWN_DIRS = {
    Player.RED: (0, 1),
    Player.BLUE: (1, 0),
    Player.YELLOW: (0, -1),
    Player.GREEN: (-1, 0),
}
PAWN_CAPTURES = {
    Player.RED: [(-1, 1), (1, 1)],
    Player.BLUE: [(1, -1), (1, 1)],
    Player.YELLOW: [(-1, -1), (1, -1)],
    Player.GREEN: [(-1, -1), (-1, 1)],
}
KNIGHT_DELTAS = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
KING_DELTAS = [(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if x or y]
BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


@dataclass(frozen=True)
class Piece:
    owner: Player
    kind: str
    dead: bool = False

    @property
    def value(self) -> int:
        return 0 if self.dead else CAPTURE_POINTS[self.kind]


@dataclass(frozen=True)
class Move:
    start: tuple[int, int]
    end: tuple[int, int]
    promotion: bool = False
    check_count: int = 0


@dataclass
class Game:
    board: dict[tuple[int, int], Piece] = field(default_factory=dict)
    scores: dict[Player, int] = field(default_factory=lambda: {p: 0 for p in TURN_ORDER})
    active: set[Player] = field(default_factory=lambda: set(TURN_ORDER))
    turn_index: int = 0
    pgn: list[str] = field(default_factory=list)
    half_turns_without_progress: int = 0
    positions: dict[str, int] = field(default_factory=dict)
    rng: random.Random = field(default_factory=random.Random)

    @classmethod
    def modern(cls, seed: int | None = None) -> "Game":
        game = cls(rng=random.Random(seed))
        # Compact Modern-like deployment on all four board edges. Coordinates are
        # file/rank pairs where a1 is lower-left from Red's perspective.
        back = "RNBQKBNR"
        for i, kind in enumerate(back, start=4):
            game.board[(i, 1)] = Piece(Player.RED, kind)
            game.board[(i, 14)] = Piece(Player.YELLOW, kind)
            game.board[(1, i)] = Piece(Player.BLUE, kind)
            game.board[(14, i)] = Piece(Player.GREEN, kind)
        for i in range(4, 12):
            game.board[(i, 2)] = Piece(Player.RED, "P")
            game.board[(i, 13)] = Piece(Player.YELLOW, "P")
            game.board[(2, i)] = Piece(Player.BLUE, "P")
            game.board[(13, i)] = Piece(Player.GREEN, "P")
        game.positions[game.position_key()] = 1
        return game

    @property
    def current_player(self) -> Player:
        for _ in range(4):
            player = TURN_ORDER[self.turn_index % 4]
            if player in self.active:
                return player
            self.turn_index += 1
        return TURN_ORDER[0]

    def inside(self, sq: tuple[int, int]) -> bool:
        return 1 <= sq[0] <= BOARD_SIZE and 1 <= sq[1] <= BOARD_SIZE

    def legal_moves(self, player: Player) -> list[Move]:
        if player not in self.active:
            return []
        moves: list[Move] = []
        for sq, piece in list(self.board.items()):
            if piece.owner != player or piece.dead:
                continue
            for end in self.pseudo_targets(sq, piece):
                target = self.board.get(end)
                if target and target.owner == player:
                    continue
                promotion = piece.kind == "P" and PROMOTION_TARGETS[player](end)
                candidate = Move(sq, end, promotion)
                clone = self.clone()
                clone.apply_move(candidate, score=False)
                if not clone.in_check(player):
                    moves.append(candidate)
        return moves

    def pseudo_targets(self, sq: tuple[int, int], piece: Piece) -> Iterable[tuple[int, int]]:
        if piece.kind in {"P", "D"} and piece.kind == "P":
            dx, dy = PAWN_DIRS[piece.owner]
            one = (sq[0] + dx, sq[1] + dy)
            if self.inside(one) and one not in self.board:
                yield one
            for cx, cy in PAWN_CAPTURES[piece.owner]:
                cap = (sq[0] + cx, sq[1] + cy)
                if self.inside(cap) and cap in self.board and self.board[cap].owner != piece.owner:
                    yield cap
            return
        if piece.kind == "N":
            for dx, dy in KNIGHT_DELTAS:
                end = (sq[0] + dx, sq[1] + dy)
                if self.inside(end):
                    yield end
            return
        if piece.kind == "K":
            for dx, dy in KING_DELTAS:
                end = (sq[0] + dx, sq[1] + dy)
                if self.inside(end):
                    yield end
            return
        dirs = BISHOP_DIRS if piece.kind == "B" else ROOK_DIRS if piece.kind == "R" else BISHOP_DIRS + ROOK_DIRS
        for dx, dy in dirs:
            end = (sq[0] + dx, sq[1] + dy)
            while self.inside(end):
                yield end
                if end in self.board:
                    break
                end = (end[0] + dx, end[1] + dy)

    def in_check(self, player: Player) -> bool:
        kings = [sq for sq, pc in self.board.items() if pc.owner == player and pc.kind == "K" and not pc.dead]
        if not kings:
            return True
        king = kings[0]
        for sq, piece in self.board.items():
            if piece.owner != player and piece.owner in self.active and not piece.dead:
                if king in set(self.pseudo_targets(sq, piece)):
                    return True
        return False

    def checked_opponents(self, player: Player) -> list[Player]:
        return [p for p in self.active if p != player and self.in_check(p)]

    def apply_move(self, move: Move, score: bool = True) -> str:
        piece = self.board.pop(move.start)
        captured = self.board.pop(move.end, None)
        progressed = piece.kind == "P" or captured is not None
        if score and captured and captured.owner != piece.owner:
            self.scores[piece.owner] += captured.value
        if move.promotion:
            piece = Piece(piece.owner, "D")
        self.board[move.end] = piece
        if score:
            checked = self.checked_opponents(piece.owner)
            if len(checked) == 2:
                self.scores[piece.owner] += 1 if piece.kind in {"Q", "D"} else 5
            elif len(checked) >= 3:
                self.scores[piece.owner] += 5 if piece.kind in {"Q", "D"} else 20
            for victim in checked:
                if not self.legal_moves(victim):
                    self.scores[piece.owner] += 20
                    self.kill_side(victim)
            self.half_turns_without_progress = 0 if progressed else self.half_turns_without_progress + 1
            key = self.position_key()
            self.positions[key] = self.positions.get(key, 0) + 1
        return self.format_move(move, piece, captured)

    def kill_side(self, player: Player) -> None:
        self.active.discard(player)
        for sq, piece in list(self.board.items()):
            if piece.owner == player:
                self.board[sq] = Piece(piece.owner, piece.kind, dead=True)

    def position_key(self) -> str:
        parts = [f"{x},{y}:{p.owner.value[0]}{p.kind}{int(p.dead)}" for (x, y), p in sorted(self.board.items())]
        return "|".join(parts) + f"/{self.turn_index % 4}"

    def terminal_reason(self) -> str | None:
        if len(self.active) <= 1:
            return "only one active player remains"
        if any(count >= 3 for count in self.positions.values()):
            for p in self.active:
                self.scores[p] += 10
            return "threefold repetition"
        if self.half_turns_without_progress >= 200:
            for p in self.active:
                self.scores[p] += 10
            return "50 full turns without capture or pawn move"
        live_material = [pc.kind for pc in self.board.values() if not pc.dead and pc.owner in self.active and pc.kind != "K"]
        if not any(k in MAJOR_PIECES or k == "P" for k in live_material):
            for p in self.active:
                self.scores[p] += 10
            return "insufficient material"
        return None

    def clone(self) -> "Game":
        return copy.deepcopy(self)

    def format_move(self, move: Move, moved: Piece, captured: Piece | None) -> str:
        prefix = "" if moved.kind == "P" else moved.kind
        capture = "x" + ((captured.kind if captured and captured.kind != "P" else "") if captured else "") if captured else "-"
        suffix = "=D" if move.promotion else ""
        checks = len(self.checked_opponents(moved.owner))
        suffix += "+" * min(checks, 2)
        return f"{prefix}{square_name(move.start)}{capture}{square_name(move.end)}{suffix}"


def square_name(sq: tuple[int, int]) -> str:
    return f"{FILES[sq[0] - 1]}{sq[1]}"


class Bot:
    def choose(self, game: Game, player: Player, deadline: float) -> Move | None:
        moves = game.legal_moves(player)
        if not moves:
            return None
        ordered = sorted(moves, key=lambda m: self.static_score(game, m, player), reverse=True)
        best = ordered[0]
        depth = 1
        while time.monotonic() < deadline and depth <= 2:
            best = max(ordered[:24], key=lambda m: self.search_score(game, m, player, depth, deadline))
            depth += 1
        return best

    def static_score(self, game: Game, move: Move, player: Player) -> float:
        target = game.board.get(move.end)
        score = (target.value if target else 0) * 20
        score += 9 if move.promotion else 0
        score += center_bonus(move.end)
        return score + game.rng.random() * 0.01

    def search_score(self, game: Game, move: Move, player: Player, depth: int, deadline: float) -> float:
        clone = game.clone()
        clone.apply_move(move)
        if depth == 0 or time.monotonic() >= deadline or clone.terminal_reason():
            return evaluate(clone, player)
        clone.turn_index += 1
        opponent = clone.current_player
        replies = clone.legal_moves(opponent)[:12]
        if not replies:
            return evaluate(clone, player)
        return min(self.search_score(clone, reply, player, depth - 1, deadline) for reply in replies)


def center_bonus(sq: tuple[int, int]) -> float:
    return 7 - (abs(sq[0] - 7.5) + abs(sq[1] - 7.5)) / 2


def evaluate(game: Game, player: Player) -> float:
    material = sum(pc.value for pc in game.board.values() if pc.owner == player and not pc.dead)
    enemy_material = sum(pc.value for pc in game.board.values() if pc.owner != player and not pc.dead) / 3
    placement = sorted(game.scores.values(), reverse=True).index(game.scores[player])
    return game.scores[player] * 100 + material * 2 - enemy_material - placement * 15


def run_self_play(seed: int | None = None, seconds_per_side: float = 30.0, max_rounds: int = 250) -> Game:
    game = Game.modern(seed)
    bots = {p: Bot() for p in TURN_ORDER}
    clocks = {p: seconds_per_side for p in TURN_ORDER}
    ply_moves: list[str] = []
    full_turn = 1
    while full_turn <= max_rounds:
        reason = game.terminal_reason()
        if reason:
            break
        player = game.current_player
        start = time.monotonic()
        move = bots[player].choose(game, player, start + min(0.05, max(0.001, clocks[player] / 40)))
        clocks[player] -= time.monotonic() - start
        if move is None:
            game.scores[player] += 20
            game.active.discard(player)
            text = "S"
        else:
            text = game.apply_move(move)
        ply_moves.append(text)
        game.turn_index += 1
        if len(ply_moves) == 4 or game.current_player == Player.RED:
            game.pgn.append(f"{full_turn}. " + " .. ".join(ply_moves))
            ply_moves = []
            full_turn += 1
    if ply_moves:
        game.pgn.append(f"{full_turn}. " + " .. ".join(ply_moves))
    return game


def main() -> None:
    parser = argparse.ArgumentParser(description="Run four-player Modern chess self-play.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--time", type=float, default=30.0, help="seconds per side")
    parser.add_argument("--max-rounds", type=int, default=250, help="maximum full turns")
    args = parser.parse_args()
    game = run_self_play(args.seed, args.time, args.max_rounds)
    print("Scores:", {p.value: game.scores[p] for p in TURN_ORDER})
    print("\n".join(game.pgn))


if __name__ == "__main__":
    main()
