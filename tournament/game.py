from datetime import datetime

from attrs import define, field
import pandas as pd

from tournament.utils import Outcome, GamesSheetHeader, BYE_PLAYER


@define
class Game:
    round_num: int = field(converter=int)
    white: str = field()  # player name
    black: str  # player name
    score_delta: float
    games_played: int
    match_link: str  # lichess url
    outcome: Outcome
    expires: datetime
    opening: str

    @white.validator
    def not_bye(self, attribute, value):
        if value == 'bye':
            raise ValueError('Bye player must be black')

    @classmethod
    def from_series(cls, series: pd.Series):
        """convert series of strings into Game object"""
        return cls(
            round_num=series[GamesSheetHeader.ROUND.value],
            white=series[GamesSheetHeader.WHITE.value],
            black=series[GamesSheetHeader.BLACK.value],
            score_delta=series[GamesSheetHeader.SCORE_DELTA.value],
            games_played=series[GamesSheetHeader.GAMES_PLAYED.value],
            match_link=series[GamesSheetHeader.MATCH_LINK.value],
            outcome=Outcome(series[GamesSheetHeader.OUTCOME.value]),
            expires=pd.to_datetime(series[GamesSheetHeader.EXPIRES.value]),
            opening=series[GameSheetHeader.OPENING.value],
        )

    @property
    def bye(self):
        return self.black == BYE_PLAYER

    @property
    def in_progress(self) -> bool:
        """True when game outcome is blank"""
        return self.outcome == Outcome.PENDING

    def to_dict(self) -> dict:
        return {
            GamesSheetHeader.ROUND.value: self.round_num,
            GamesSheetHeader.WHITE.value: self.white,
            GamesSheetHeader.BLACK.value: self.black,
            GamesSheetHeader.SCORE_DELTA.value: self.score_delta,
            GamesSheetHeader.GAMES_PLAYED.value: self.games_played,
            GamesSheetHeader.MATCH_LINK.value: self.match_link,
            GamesSheetHeader.OUTCOME.value: self.outcome.value,
            GamesSheetHeader.EXPIRES.value: self.expires,
            GamesSheetHeader.OPENING.value: self.opening,
        }

    def get_points(self, player: str) -> float:
        if self.outcome == Outcome.DRAW:
            return 0.5

        elif ((player == self.white and self.outcome == Outcome.WHITE)
              or (player == self.black and self.outcome == Outcome.BLACK)):
            return 1.0

        else:
            # losses and games that expire
            return 0.
