from datetime import datetime
from random import shuffle

from attrs import define, field
import pandas as pd

from tournament.lichess import create_lichess_challenge
from tournament.player import Player
from tournament.utils import Outcome, expires_at_timestamp, timestamp_to_datetime


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

    @classmethod
    def create(cls, round_num: str, players: tuple[Player], lichess_api_token: str,
               testing: bool = False, days_until_expired: int = 7,
               **kwargs):

        player_pair = [players[0], players[1]]

        # randomize side if not bye
        if not players[1].is_bye:
            shuffle(player_pair)

        expires_at = expires_at_timestamp(days_until_expired)
        expires_at_datetime = timestamp_to_datetime(expires_at)

        if testing:
            game_link = 'https://lichess.org/'
        else:
            game_link = create_lichess_challenge(
                round_num=round_num,
                white_player=player_pair[0],
                black_player=player_pair[1],
                api_token=lichess_api_token,
                **kwargs)

        return cls(
            round_num=int(round_num),
            white=player_pair[0].name,
            black=player_pair[1].name,
            score_delta=player_pair[0].score - player_pair[1].score,
            games_played=players[0].match_count(players[1].name),
            match_link=game_link,
            expires=expires_at_datetime,
            outcome=Outcome.white if players[1].is_bye else None)

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
