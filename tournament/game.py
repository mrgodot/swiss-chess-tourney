from datetime import datetime

from attrs import define, field
import pandas as pd

from tournament.utils import Outcome


@define
class Game:
    round_num: int = field(converter=int)
    white: str
    black: str
    score_delta: float = field(default=None)
    games_played: int = field(default=None)
    match_link: str = field(default=None)  # lichess url
    expires: datetime = field(default=None)
    outcome: Outcome = field(default=None)

    @classmethod
    def from_series(cls, series: pd.Series):
        return cls(
            round_num=int(series.name),
            white=series['White'],
            black=series['Black'],
            outcome=Outcome(series['Outcome']) if series['Outcome'] != '' else None)

    @property
    def bye(self):
        return self.black == 'bye'

    def to_dict(self) -> dict:
        return {
            'Round': self.round_num,
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
