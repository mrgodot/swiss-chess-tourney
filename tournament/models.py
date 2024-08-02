from datetime import datetime
from enum import Enum

from attrs import define, field
import pandas as pd
import numpy as np


class Outcome(Enum):
    white='White'
    black='Black'
    draw='Draw'
    expired='Expired'


@define
class Game:
    round: int = field(converter=int)
    white: str
    black: str
    score_delta: float = field(default=None)
    games_played: int = field(default=None)
    match_link: str = field(default=None)
    expires: datetime = field(default=None)
    outcome: Outcome = field(default=None)

    @classmethod
    def from_series(cls, series: pd.Series):
        return cls(
            round=series.name,
            white=series['White'],
            black=series['Black'],
            outcome=Outcome(series['Outcome']) if series['Outcome'] != '' else None)

    @property
    def bye(self):
        return self.black == 'bye'

    def to_dict(self) -> dict:
        return {
            'Round': self.round,
            'White': self.white,
            'Black': self.black,
            'Score Delta': self.score_delta,
            'Rematch': self.games_played,
            'Match Link': self.match_link,
            'Expires': self.expires,
            'Outcome': '' if self.outcome is None else self.outcome.value}

    def get_points(self, player: str) -> float:
        if self.outcome == Outcome.draw:
            return 0.5

        elif (player == self.white and self.outcome == Outcome.white) or \
                (player == self.black and self.outcome == Outcome.black):
             return 1.0

        else:
            # losses and games that expire
            return 0.


@define
class Player:
    name: str
    handle: str
    federation: str
    elo: float = field(default=1500)
    games: list[Game] = field(factory=list, init=False)

    @classmethod
    def from_series(cls, series: pd.Series):
        return cls(
            name=series.name,
            handle=series['Lichess'],
            federation=series['Federation'])

    @classmethod
    def bye_player(cls):
        return cls(
            name='bye',
            handle=None,
            federation=None,
            elo=-np.inf)

    @property
    def is_bye(self) -> bool:
        return self.name == 'bye'

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
            'Player': self.name,
            'Lichess': self.handle,
            'Federation': self.federation,
            'Elo': self.elo,
            'Score': self.score}

    def match_count(self, opponent: str) -> int:
        return sum(opponent in {game.white, game.black} for game in self.games)

    def _update_elo(self, opponent_elo: float, points: float,
                    k_factor: int = 100):
        expected_score = 1 / (1 + 10 ** ((opponent_elo - self.elo) / 400))
        self.elo += k_factor * (points - expected_score)

    def update(self, game: Game, opponent_elo: float):
        self.games.append(game)
        if game.outcome != Outcome.expired and not game.bye:
            self._update_elo(
                opponent_elo=opponent_elo,
                points=game.get_points(self.name))

    def __repr__(self) -> str:
        return f"Player(name='{self.name}', handle={self.handle}, federation={self.federation}, elo={self.elo})"
    