import pandas as pd
from attrs import define, field

from tournament.game import Game
from tournament.utils import BYE_PLAYER, BYE_PLAYER_ELO, Outcome, PlayerSheetHeader


@define
class Player:
    name: str
    handle: str
    elo_init: float  # elo at start of tournament
    elo: float
    federation: str | None = None
    withdrawn: bool = field(default=False)
    games: list[Game] = field(factory=list, init=False)

    @classmethod
    def from_series(cls, series: pd.Series):
        elo_init = float(series[PlayerSheetHeader.ELO_INIT.value])
        return cls(
            name=str(series.name),
            handle=series[PlayerSheetHeader.HANDLE.value],
            elo_init=elo_init,
            elo=elo_init,
            withdrawn=series.get(PlayerSheetHeader.WITHDRAWN.value, "FALSE") == "TRUE",
            federation=series.get(PlayerSheetHeader.FEDERATION.value),
        )

    @classmethod
    def bye_player(cls):
        return cls(
            name=BYE_PLAYER,
            handle=BYE_PLAYER,
            federation=BYE_PLAYER,
            elo=BYE_PLAYER_ELO,
        )

    @property
    def is_bye(self) -> bool:
        return self.name == BYE_PLAYER

    @property
    def byes(self) -> int:
        return len([game for game in self.games if game.bye])

    @property
    def score(self) -> float:
        return sum(game.get_points(self.name) for game in self.games)

    @property
    def rounds_played(self) -> int:
        return len(self.games)

    def to_dict(self) -> dict:
        return {
            PlayerSheetHeader.PLAYER.value: self.name,
            PlayerSheetHeader.HANDLE.value: self.handle,
            PlayerSheetHeader.FEDERATION.value: self.federation,
            PlayerSheetHeader.ELO_INIT.value: self.elo_init,
            PlayerSheetHeader.ELO.value: self.elo,
            PlayerSheetHeader.SCORE.value: self.score,
        }

    def match_count(self, opponent: str) -> int:
        return sum(opponent in {game.white, game.black} for game in self.games)

    def _update_elo(self, opponent_elo: float, points: float, k_factor: int = 100):
        expected_score = 1 / (1 + 10 ** ((opponent_elo - self.elo) / 400))
        self.elo += k_factor * (points - expected_score)

    def update(self, game: Game, opponent_elo: float, **kwargs):
        """add game to player list and update player elo based on `game.outcome`. pass k_factor to _update_elo."""
        self.games.append(game)
        if game.outcome != Outcome.EXPIRED and not game.bye:
            self._update_elo(opponent_elo=opponent_elo, points=game.get_points(self.name), **kwargs)

    def reset(self):
        self.games = []
        self.elo = self.elo_init

    def __repr__(self) -> str:
        return (
            f"Player(name='{self.name}', handle='{self.handle}', "
            f"federation='{self.federation}', elo={self.elo}, "
            f"score={self.score}, rounds_played={self.rounds_played}, withdrawn={self.withdrawn})"
        )
